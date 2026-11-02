"""Area geometries for abstracted place names, fetched from Natural Earth.

Physical (deserts, mountain ranges, plateaus, plains, basins), marine (seas, gulfs, bays, channels,
oceans) and admin-1 places resolve to a polygon whose grid cells the study is scored over; countries
resolve through the admin-0 shapes the pipeline already uses. Anything unmatched falls back to the
cell containing the place's point.
"""

import hashlib
import json
import logging
import urllib.request
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import pandas as pd
import typer

from climate_health_map.shared import Settings, get_logger, load_settings

if TYPE_CHECKING:
    from geopandas import GeoDataFrame

# Natural Earth 10m layers from the official CDN; the zips have not changed since 2022 (NE v5.1.x)
LAYERS = {
    'adm1': (
        'ne_10m_admin_1_states_provinces',
        'https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip',
        'efc59726337323058f9446210adc96673179cd344e053666ee3d28cb58ba2b05',
    ),
    'regions': (
        'ne_10m_geography_regions_polys',
        'https://naciscdn.org/naturalearth/10m/physical/ne_10m_geography_regions_polys.zip',
        'cb7b9db200284ed1551f20eacc7f3333e9b5f311c19f7cb2670694529f688682',
    ),
    'marine': (
        'ne_10m_geography_marine_polys',
        'https://naciscdn.org/naturalearth/10m/physical/ne_10m_geography_marine_polys.zip',
        'a2d3395904c41e718e02c3ec5bc988712164c524c236fad32d95d282ca303b2a',
    ),
}

# GeoNames feature codes whose places name an area: code -> (layer, featurecla values to search, match by geonameid).
POLYGON_CODES: dict[str, tuple[str, tuple[str, ...] | None, bool]] = {
    'ADM1': ('adm1', None, True),
    'ADM1H': ('adm1', None, True),
    'MTS': ('regions', ('Range/mtn',), False),
    'PLAT': ('regions', ('Plateau',), False),
    'PLN': ('regions', ('Plain',), False),
    'DSRT': ('regions', ('Desert',), False),
    'BSNU': ('regions', ('Basin',), False),
    'OCN': ('marine', ('ocean',), False),
    'SEA': ('marine', ('sea', 'bay'), False),
    'GULF': ('marine', ('gulf', 'bay'), False),
    'BAY': ('marine', ('gulf', 'bay'), False),
    'CHN': ('marine', ('channel',), False),
}

# Coarseness of a place name for ancestor pruning: a polygon place is dropped when a place with a
# strictly larger rank of the same paper lies inside it ("São Paulo, Brazil" keeps São Paulo).
# Physical and marine areas sit between admin-1 and admin-2; everything point-like is largest.
PLACE_RANK = {
    'PCLI': 0,
    'PCLD': 0,
    'PCLF': 0,
    'PCLS': 0,
    'PCL': 0,
    'TERR': 0,
    'ADMD': 0,
    'ADM1': 1,
    'ADM1H': 1,
    'SEA': 2,
    'MTS': 2,
    'PLN': 2,
    'OCN': 2,
    'DSRT': 2,
    'GULF': 2,
    'PLAT': 2,
    'CHN': 2,
    'BSNU': 2,
    'BAY': 2,
}
DEFAULT_RANK = 3

# Renames so a Natural Earth polygon carries the GeoNames place name; (layer, featurecla substring,
# name substring, new name, new featurecla or None). A featurecla reassignment moves the polygon
# into the search pool of the renamed-to feature code, where studies class it differently.
RENAMES = [
    ('regions', 'Range/mtn', 'altay', 'Altay', None),
    ('regions', 'Range/mtn', 'appalach', 'Appalachian Mountains', None),
    ('regions', 'Range/mtn', 'cant', 'Cordillera Cantábrica', None),
    ('regions', 'Range/mtn', 'dabie', 'Dabie Shan', None),
    ('regions', 'Range/mtn', 'eastern ghats', 'Eastern Ghāts', None),
    ('regions', 'Range/mtn', 'western ghats', 'Western Ghāts', None),
    ('regions', 'Range/mtn', 'kunlun', 'Kalakunlun Shan', None),
    ('regions', 'Range/mtn', 'len mountain', 'Kölen', None),
    ('regions', 'Range/mtn', 'taihang mts.', 'Taihang Shan', None),
    ('regions', 'Range/mtn', 'tatra mts.', 'Tatry', None),
    ('regions', 'Range/mtn', 'tian shan', 'Tien Shan', None),
    ('regions', 'Range/mtn', 'andes', 'Andes Mountains', None),
    ('regions', 'Range/mtn', 'hindu kush', 'Hindū Kush', None),
    ('regions', 'Range/mtn', 'marrah mts', 'Jabal Marrah', None),
    ('regions', 'Range/mtn', 'lebanon', 'Mount Lebanon', None),
    ('regions', 'Range/mtn', 'karakoram ra', 'Karakorum Shan', None),
    ('regions', 'Desert', 'negev', 'Negev', None),
    ('regions', 'Desert', 'atacama', 'Atacama Desert', None),
    ('regions', 'Desert', 'chihuahuan desert', 'Chihuahua Desert', None),
    ('regions', 'Desert', 'lut desert', 'God-e Lut', None),
    ('regions', 'Desert', 'taklimakan desert', 'Takla Makan Desert', None),
    ('regions', 'Plateau', 'cumberland', 'Cumberland Plateau', 'Plain'),
    ('regions', 'Plateau', 'colorado', 'San Francisco Plateau', 'Plain'),
    ('regions', 'Plain', 'gange', 'Gangetic Plain', None),
    ('regions', 'Plain', 'north china', 'Huanghuai Pingyuan', None),
    ('regions', 'Plateau', 'mongol', 'Nei Mongol Gaoyuan', None),
    ('regions', 'Plateau', 'deccan', 'Deccan', None),
    ('regions', 'Plateau', 'chota', 'Chota Nāgpur Plateau', None),
    ('regions', 'Plateau', 'loess', 'Huangtu Gaoyuan', None),
    ('regions', 'Plateau', 'khorat', 'Khorat Plateau', None),
    ('regions', 'Plateau', 'tibet', 'Qing Zang Gaoyuan', None),
    ('regions', 'Plateau', 'polar', 'South Polar Plateau', None),
    ('regions', 'Plateau', 'yungui', 'Yungui Gaoyuan', None),
]


def place_shapes_dir(settings: Settings) -> Path:
    """Natural Earth tree under the data root, written by `fetch-place-shapes`."""
    return Path(settings.DATA_ROOT) / 'shapes_2026/natural_earth'


def fetch_place_shapes(
    target: Annotated[Path | None, typer.Option(help='Target directory (default: shapes_2026/natural_earth under the data root)')] = None,
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    force: Annotated[bool, typer.Option('--force', help='Re-download even when the layers are extracted')] = False,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Download and extract the pinned Natural Earth place layers with a provenance record."""
    logger = get_logger('geographies.place_shapes', loglevel=loglevel)
    settings = load_settings(config)
    target = target or place_shapes_dir(settings)
    (target / 'zips').mkdir(parents=True, exist_ok=True)
    provenance = {}
    for key, (name, url, sha256) in LAYERS.items():
        provenance[key] = {'file': f'{name}.shp', 'url': url, 'sha256': sha256}
        if (target / f'{name}.shp').exists() and not force:
            logger.info('Keeping existing %s', target / f'{name}.shp')
            continue
        archive = target / 'zips' / f'{name}.zip'
        if not archive.exists():
            logger.info('Downloading %s', url)
            urllib.request.urlretrieve(url, archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != sha256:
            raise typer.BadParameter(f'{archive} has sha256 {digest}, expected {sha256}')
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target)
        logger.info('Extracted %s from %s', name, archive)
    (target / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


def normalise_place_name(name: str | float) -> str | float:
    """Lower-case and spell out 'mts.' so place and layer names compare equal."""
    if pd.isna(name):
        return name
    return str(name).lower().replace('mts.', 'mountains')


def load_place_layers(settings: Settings | None = None, config: Path | None = None) -> dict[str, 'GeoDataFrame']:
    """Load the Natural Earth layers with lower-cased columns, renames applied and a `place_name` column."""
    import geopandas as gpd

    settings = settings or load_settings(config)
    directory = place_shapes_dir(settings)
    layers = {}
    for key, (name, _, _) in LAYERS.items():
        gdf = gpd.read_file(directory / f'{name}.shp')
        # the regions layer ships its columns upper-cased
        gdf.columns = [str(c).lower() for c in gdf.columns]
        for layer_key, featurecla, needle, new_name, new_featurecla in RENAMES:
            if layer_key != key:
                continue
            mask = gdf['featurecla'].str.contains(featurecla, case=False, na=False, regex=False) & gdf['name'].str.contains(
                needle, case=False, na=False, regex=False
            )
            gdf.loc[mask, 'name'] = new_name
            if new_featurecla is not None:
                gdf.loc[mask, 'featurecla'] = new_featurecla
        gdf['place_name'] = gdf['name'].map(normalise_place_name)
        if 'gn_id' in gdf.columns:
            gdf['gn_id'] = pd.to_numeric(gdf['gn_id'], errors='coerce')
        layers[key] = gdf
    return layers


def _candidate_shapes(pool: 'pd.DataFrame', shape_ids: list[int], point) -> list[int]:
    """Narrow several name matches to the polygons containing the place's point, or to the largest."""
    if len(shape_ids) <= 1:
        return shape_ids
    containing = [i for i in shape_ids if pool.geometry.iloc[i].contains(point)]
    if containing:
        return containing
    areas = {i: pool.geometry.iloc[i].area for i in shape_ids}
    return [max(areas, key=areas.get)]


def resolve_place_polygons(
    df_locations: pd.DataFrame,
    layers: dict[str, 'GeoDataFrame'],
    adm0: 'GeoDataFrame | None' = None,
    loglevel: str = 'INFO',
) -> 'pd.Series':
    """Resolve each location to a place polygon: Natural Earth by geonameid then name, countries and
    unmatched admin-1 places through the admin-0 shapes; unmatched locations get None and are scored
    on the cell containing their point. The returned Series is keyed by `location_id`.

    Where a name matches several polygons, the one containing the location's point wins, else the largest.
    """
    import geopandas as gpd

    logger = get_logger('geographies.place_shapes', loglevel=loglevel)
    if not df_locations['location_id'].is_unique:
        raise ValueError('location_id must be unique: geometries are keyed by it')
    geometry = pd.Series(None, index=pd.Index(df_locations['location_id'], name='location_id'), dtype=object)
    for code, (layer_key, classes, by_geoname) in POLYGON_CODES.items():
        locations = df_locations[df_locations['feature_code'] == code]
        if locations.empty:
            continue
        pool = layers[layer_key].reset_index(drop=True)
        if classes is not None:
            pool = pool[pool['featurecla'].isin(classes)]
        gn_to_pos = {int(g): i for i, g in enumerate(pool['gn_id']) if pd.notna(g)} if by_geoname else {}
        by_name = pool.groupby('place_name', sort=False).indices
        points = gpd.points_from_xy(locations['lon'], locations['lat'])
        matched = 0
        # geonameid decides where both sides carry one; a name match narrows by the point, then by size
        for loc_id, name, gid, point in zip(locations['location_id'], locations['name'], locations['geonameid'].astype('Float64'), points, strict=True):
            shape_ids = [gn_to_pos[int(gid)]] if pd.notna(gid) and int(gid) in gn_to_pos else None
            if shape_ids is None:
                name_ids = by_name.get(normalise_place_name(name))
                shape_ids = [int(i) for i in name_ids] if name_ids is not None else None
            if shape_ids is None:
                continue
            geometry.loc[loc_id] = pool.geometry.iloc[_candidate_shapes(pool, shape_ids, point)[0]]
            matched += 1
        logger.info('%s: %d locations, %d polygons, %d fall back', code, len(locations), matched, len(locations) - matched)

    if adm0 is not None:
        country_codes = {code for code in PLACE_RANK if code not in POLYGON_CODES} | {'ADM1', 'ADM1H'}
        todo = df_locations[df_locations['feature_code'].isin(country_codes) & geometry.loc[df_locations['location_id']].isna().to_numpy()]
        if not todo.empty:
            points = gpd.GeoDataFrame(
                geometry=gpd.points_from_xy(todo['lon'], todo['lat']),
                index=pd.Index(todo['location_id'], name='location_id'),
                crs='EPSG:4326',
            )
            adm0_geoms = adm0[['geometry']] if adm0.crs is not None else adm0.set_crs('EPSG:4326')[['geometry']]
            joined = points.sjoin(adm0_geoms, predicate='within', how='inner')
            joined = joined[~joined.index.duplicated(keep='first')]
            geometry.loc[joined.index] = [adm0_geoms.geometry.iloc[i] for i in joined['index_right']]
            logger.info('Country/admin-0 fallback: %d of %d locations matched a country polygon', len(joined), len(todo))
    return geometry


def prune_ancestor_locations(df_locations: pd.DataFrame, geometry: 'pd.Series', logger: logging.Logger) -> pd.Series:
    """Drop duplicate places and place ancestors within a paper, keeping the smallest locations.

    A polygon place is an ancestor when a place of the same paper with a finer `PLACE_RANK` has its
    point inside the polygon (or its polygon inside the polygon); "São Paulo, Brazil" then keeps São
    Paulo alone. Sub-city nesting needs adm2/adm3 boundaries, which no synced layer carries.
    `df_locations` and `geometry` are keyed the same way; the keep mask inherits that key.
    """
    import geopandas as gpd
    from shapely.geometry.base import BaseGeometry

    loc_ids = pd.Index(df_locations['location_id'] if 'location_id' in df_locations.columns else df_locations.index, name='location_id')
    points = gpd.GeoSeries(gpd.points_from_xy(df_locations['lon'], df_locations['lat']), index=loc_ids)
    geometry = geometry.reindex(loc_ids)
    keep = pd.Series(True, index=loc_ids)
    dupes = df_locations['geonameid'].notna().to_numpy() & df_locations.duplicated(subset=['item_id', 'geonameid'], keep='first').to_numpy()
    keep &= ~dupes
    ranks = df_locations['feature_code'].map(PLACE_RANK).fillna(DEFAULT_RANK)
    ranks = pd.Series(ranks.to_numpy(), index=loc_ids)
    items = pd.Series(df_locations['item_id'].to_numpy(), index=loc_ids)
    pruned = 0
    by_item = items.groupby(items, sort=False).groups
    for loc_id in geometry.index[geometry.notna()]:
        polygon = geometry.loc[loc_id]
        item = items.loc[loc_id]
        siblings = [other for other in by_item[item] if other != loc_id and keep.loc[other] and ranks.loc[other] > ranks.loc[loc_id]]
        ancestor = any(polygon.contains(points.loc[other]) for other in siblings) or any(
            isinstance(geometry.loc[other], BaseGeometry) and geometry.loc[other].within(polygon) for other in siblings
        )
        if ancestor:
            keep.loc[loc_id] = False
            pruned += 1
    logger.info('Pruned %d duplicate and %d ancestor places of %d polygon places', int(dupes.sum()), pruned, int(geometry.notna().sum()))
    return keep
