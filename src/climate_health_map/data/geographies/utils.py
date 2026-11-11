import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from climate_health_map.data import LABELS

if TYPE_CHECKING:
    from geopandas import GeoDataFrame

EXCLUDED_SEARCH_NAMES = {
    'B.V.',
    'MMT',
    'Yellow',
    'Hadley',
    'Western North',
    'colonies',
    'TN',
    'NH',
    'Mn',
    'Tx',
    'TX',
    'Tn',
    'FL',
    'Spartina',
    'Tamarix',
    'Eurasia',
    'Phillyrea',
    'N-15',
    'LT50',
    'POSEIDON',
    'LC50',
    'El Nio',
    'La Nia',
    'Red',
    'Gulf Stream',
    'NH 1',
    'Quercus',
    'ZJP',
    'MSW',
    'CCS',
    'Tier-3',
    'N2O',
    'VKT',
    'OECD',
    'States',
    'North to South',
    'Stabilising',
    'Mass Railway',
    'City',
    'the Urban Heat Island',
    'Munich Re',
    'HKH',
    'WC-RC',
}
EXCLUDED_NAMES = {
    'Pacific County',
}


def get_naming_mask(place_df: pd.DataFrame) -> pd.Series:
    """Create mask to remove places that are, based on anecdotal evidence, not actually clean place names."""
    return (
        # ~place_df['name'].str.lower().str.strip().isin({name.lower().strip() for name in EXCLUDED_NAMES})
        # & ~place_df['search_name'].str.lower().str.strip().isin({name.lower().strip() for name in EXCLUDED_SEARCH_NAMES})
        (place_df['search_name'].str.len() > 2)
        & ~place_df['name'].str.strip().isin({name.strip() for name in EXCLUDED_NAMES})
        & ~place_df['search_name'].str.strip().isin({name.strip() for name in EXCLUDED_SEARCH_NAMES})
    )


def get_publisher_mask(merged_df: pd.DataFrame) -> pd.Series:
    """Remove texts associated with certain publishers; input is df_base.merge(df_places) or similar"""
    pubs = [('S. Karger AG, Basel', ['Basel', 'Switzerland']), ('Licensee MDPI, Basel', ['Basel', 'Switzerland'])]
    mask = merged_df['item_id'].notna()
    for snippet, place in pubs:
        mask &= ~(merged_df['text'].str.contains(snippet) & merged_df['name'].isin(place))
    return mask


def fix_geographies(place_df: pd.DataFrame) -> pd.DataFrame:
    geocolumns = ['feature_code', 'lat', 'lon', 'name', 'feature_class', 'geonameid', 'country_code3']

    place_df.loc[place_df['search_name'] == 'Pakistan', geocolumns] = ['PCLI', 30, 70, 'Islamic Republic of Pakistan', 'A', 1168579, 'PAK']
    place_df.loc[place_df['search_name'] == 'Colombia', geocolumns] = ['PCLI', 4, -73.25, 'Colombia', 'A', 3686110, 'COL']
    place_df.loc[place_df['search_name'] == 'Argentina', geocolumns] = ['PCLI', -34, -64, 'Argentine Republic', 'A', 3865483, 'ARG']
    place_df.loc[place_df['search_name'] == 'East China', geocolumns] = ['PCLI', 35, 105, 'China', 'A', 1814991, 'CHN']
    place_df.loc[place_df['search_name'] == 'South China', geocolumns] = ['PCLI', 35, 105, 'China', 'A', 1814991, 'CHN']
    place_df.loc[place_df['search_name'] == 'Ireland', geocolumns] = ['PCLI', 53, -8, 'Ireland', 'A', 2963597, 'IRL']
    place_df.loc[place_df['search_name'] == 'United States', geocolumns] = ['PCLI', 39.76, -98.5, 'United States', 'A', 6252001, 'USA']
    place_df.loc[place_df['search_name'] == 'Czech Republic', geocolumns] = ['PCLI', 49.75, 15, 'Czechia', 'A', 3077311, 'CZE']
    place_df.loc[place_df['search_name'] == 'Czechia', geocolumns] = ['PCLI', 49.75, 15, 'Czechia', 'A', 3077311, 'CZE']
    place_df.loc[place_df['search_name'] == 'China', geocolumns] = ['PCLI', 35, 105, 'China', 'A', 1814991, 'CHN']
    place_df.loc[place_df['search_name'] == 'United Arab Emirates', geocolumns] = ['PCLI', 23.75, 54.5, 'United Arab Emirates', 'A', 290557, 'ARE']

    place_df.loc[place_df['search_name'] == 'Sahara', geocolumns] = ['DSRT', 26, 13, 'Sahara', 'T', 2212709, None]

    place_df.loc[place_df['search_name'] == 'Alps', geocolumns] = ['MTS', 46.41667, 10, 'Alps', 'T', 2661786, None]
    place_df.loc[place_df['search_name'] == 'Himalayan', geocolumns] = ['MTS', 28, 84, 'Himalayas', 'T', 1252558, None]
    place_df.loc[place_df['search_name'] == 'Himalayas', geocolumns] = ['MTS', 28, 84, 'Himalayas', 'T', 1252558, None]

    place_df.loc[place_df['search_name'] == 'Mediterranean Sea', geocolumns] = ['SEA', 35, 20, 'Mediterranean Sea', 'T', 2661786, None]
    place_df.loc[place_df['search_name'] == 'MEDITERRANEAN', geocolumns] = ['SEA', 35, 20, 'Mediterranean Sea', 'T', 2661786, None]
    place_df.loc[place_df['search_name'] == 'Red Sea', geocolumns] = ['SEA', 20.26735, 38.53455, 'Red Sea', 'H', 350155, None]
    place_df.loc[place_df['search_name'] == 'North Sea', geocolumns] = ['SEA', 55, 3, 'North Sea', 'P', 2960848, None]
    place_df.loc[place_df['search_name'] == 'Philippine Sea', geocolumns] = ['SEA', 20, 135, 'Philippine Sea', 'P', 1818190, None]
    place_df.loc[place_df['search_name'] == 'Black Sea', geocolumns] = ['SEA', 43, 34, 'Black Sea', 'H', 630673, None]
    place_df.loc[place_df['search_name'] == 'Coral Sea', geocolumns] = ['SEA', -20, 155, 'Coral Sea', 'H', 2194166, None]
    place_df.loc[place_df['search_name'] == 'Timor Sea', geocolumns] = ['SEA', -11, 127, 'Timor Sea', 'H', 2078065, None]
    place_df.loc[place_df['search_name'] == 'Bering Sea', geocolumns] = ['SEA', 60, -175, 'Bering Sea', 'H', 4031788, None]
    place_df.loc[place_df['search_name'] == 'Okhotsk Sea', geocolumns] = ['SEA', 55, 150, 'Sea of Okhotsk', 'H', 2127380, None]
    place_df.loc[place_df['search_name'] == 'Ionian Sea', geocolumns] = ['SEA', 39, 19, 'Ionian Sea', 'H', 2463713, None]

    place_df.loc[place_df['search_name'] == 'South Pacific', geocolumns] = ['OCN', -45, -130, 'South Pacific Ocean', 'H', 4030483, None]
    place_df.loc[place_df['search_name'] == 'Atlantic Ocean', geocolumns] = ['OCN', 10, -25, 'Atlantic Ocean', 'H', 3373405, None]
    place_df.loc[place_df['search_name'] == 'North Pacific', geocolumns] = ['OCN', 30, -170, 'North Pacific Ocean', 'H', 4030875, None]
    place_df.loc[place_df['search_name'] == 'Indian Ocean', geocolumns] = ['OCN', -10, 70, 'Indian Ocean', 'P', 1545739, None]

    place_df.loc[place_df['search_name'] == 'Great Lakes', geocolumns] = ['LK', 45.68751, -84.43753, 'Great Lakes', 'H', 4994594, 'USA']

    place_df.loc[place_df['search_name'] == 'Catalonia', geocolumns] = ['ADM1', 41.82046, 1.86768, 'Catalunya', 'A', 3336901, 'ESP']
    place_df.loc[place_df['search_name'] == 'California (USA', geocolumns] = ['ADM1', 37.25022, -119.75126, 'California', 'A', 5332921, 'USA']
    place_df.loc[place_df['search_name'] == 'California, USA', geocolumns] = ['ADM1', 37.25022, -119.75126, 'California', 'A', 5332921, 'USA']
    place_df.loc[place_df['name'] == 'Central Upper Nile', geocolumns] = ['ADM1', 10, 32.7, 'Upper Nile', 'A', 381229, 'SSD']

    place_df.loc[place_df['search_name'] == 'Gulf Coast', geocolumns] = ['AREA', 29.36901, -95.00565, 'Gulf Coast', 'L', 7287689, 'USA']
    place_df.loc[place_df['search_name'] == 'Gulf coast', geocolumns] = ['AREA', 29.36901, -95.00565, 'Gulf Coast', 'L', 7287689, 'USA']

    place_df.loc[place_df['search_name'] == 'Hainan Island', geocolumns] = ['ISL', 19.2, 109.7, 'Hainan Dao', 'T', 1809055, 'CHN']

    place_df.loc[place_df['search_name'] == "North America's", geocolumns] = ['CONT', 46.07323, -100.54688, 'North America', 'L', 6255149, None]

    place_df.loc[place_df['search_name'] == 'Scandinavia', geocolumns] = ['RGN', 63, 12, 'Scandinavia', 'L', 2614165, None]

    place_df.loc[place_df['search_name'] == 'Huai', geocolumns] = ['STM', 33.133333, 118.5, 'Huai He', 'H', 1807690, 'CHN']
    place_df.loc[place_df['search_name'] == 'Washington, DC', geocolumns] = ['PPLC', 38.89511, -77.03637, 'Washington', 'P', 4140963, 'USA']
    place_df.loc[place_df['search_name'] == 'Messinian', geocolumns] = ['ADM2', 37.25, -21.83333, 'Nomos Messinias', 'A', 257149, 'GRC']

    place_df.loc[place_df['search_name'] == 'NYC', geocolumns] = ['PPL', 40.71427, -74.00597, 'New York City', 'P', 5128581, 'USA']

    place_df.loc[place_df['search_name'] == 'Hudson Bay', geocolumns] = ['BAY', 60, -85, 'Hudson Bay', 'H', 5978134, 'CAN']

    # Additional examples for potential fixes
    # > item_id  	name 	search_name 	feature_code 	country_code3 	lat 	lon 	start_char 	end_char 	geonameid
    # > | Republic of Zambia | Northern Egypt.(Table | PCLI | ZMB | \-14.33333 | 28.5 | 493 | 523 | 895949 |
    # > | Syrian Arab Republic | the Northern Delta Region | PCLI | SYR | 35.0 | 38.0 | 220 | 264 | 163843 |
    # > | 06521812-a904-403d-8ecd-501e2b9fdfe2 | Sunway | Sunway City | HTL | CHN | 22.64952 | 113.82104 | 1599 | 1617 | 9952455 |
    # > | b687e55e-8eb0-4e96-b20b-d5b3d489c791 | West Coast | the U.S. East Coast | ADM1 | NZL | \-42.45658 | 171.22081 | 52 | 85 | 6612113 |
    # > | b687e55e-8eb0-4e96-b20b-d5b3d489c791 | United States | the United States | PCLI | USA | 39.76 | \-98.5 | 146 | 174 | 6252001 |
    # > | b687e55e-8eb0-4e96-b20b-d5b3d489c791 | West Coast | the U.S. East Coast | ADM1 | NZL | \-42.45658 | 171.22081 | 1035 | 1068 | 6612113 |
    # > de5874e7-0389-4336-a9fb-a34b1a64bb39 	West Asia Hotel Shanghai 	West Asia 	HTL 	CHN 	31.1166 	121.3666 	375 	389 	6522100
    # > 5b6c8ffb-896a-4293-bbd5-271c552c83e4 	Bosnia and Herzegovina 	the Black Sea Region of 	PCLI 	BIH 	44.25 	17.83333 	606 	650 	3277605
    # > ee1d28bf-7e32-427a-9a41-5b9b29aea400 	Colorado 	East 23rd to 34th Streets 	ADM1 	USA 	39.00027 	-105.50083 	822 	865 	5417618
    # > ee1d28bf-7e32-427a-9a41-5b9b29aea400 	New York City 	NYC 	PPL 	USA 	40.71427 	-74.00597 	605 	608 	5128581
    # > 13ecac4d-d0c0-48e7-8398-7a30d74fcea8 	Republic of Namibia 	South and East Africa 	PCLI 	NAM 	-22.0 	17.0 	2124 	2145 	3355338
    # > f7ef8ef4-256d-4af2-8580-b2c86957cce4 	Sabah 	Sub-Sahara Africa 	ADM1 	MYS 	5.5 	117.0 	312 	340 	1733039
    # > 2d797363-894f-4267-bc75-c5e0b56502ab 	Tropics Hotel 	tropics 	HTL 	BGR 	42.71021 	27.75489 	997 	1004 	10120934
    # > 297d77a4-b264-4962-8a9c-fbb3bee2eb36 	Shatskiy Rise 	Northwest Pacific 	RISU 	NA 	35.0 	160.0 	150 	167 	2113215
    # > 5c1d7d12-a988-490e-8b5c-bfd954445bef 	Guangzhou 	Kiang Wu Hospital 	PPLA 	CHN 	23.11667 	113.25 	595 	621 	1809858
    # > bd3ad050-6e03-47b7-991f-286d6f91efa5 	Greater New Orleans Church 	Greater New Orleans 	CH 	USA 	29.97321 	-90.10179 	2062 	2093 	7533772
    # > bd3ad050-6e03-47b7-991f-286d6f91efa5 	Rapides Parish 	the Rapid Triage Area 	ADM2 	USA 	31.19862 	-92.5332 	1525 	1563 	4338356
    # > bd3ad050-6e03-47b7-991f-286d6f91efa5 	New Orleans 	East Jeff 	PPLA2 	USA 	29.95465 	-90.07507 	1768 	1782 	4335045
    # > b8dea545-191a-4521-9103-5f8429b99571 	Porto 	Porto 	ADM2 	PRT 	41.15556 	-8.62672 	1310 	1315 	6458924
    # > b8dea545-191a-4521-9103-5f8429b99571 	North America 	North 	CONT 	NA 	46.07323 	-100.54688 	1317 	1322 	6255149
    # > 1da02a15-c3e2-4503-8251-92e576149b87 	Republic of Cabo Verde 	Cape Hedo 	PCLI 	CPV 	16.0 	-24.0 	900 	914 	3374766
    # > aa9ae2e1-7499-4ab9-bbb8-d1c190508167 	Port of Spain 	Port of Spain 	PPLC 	TTO 	10.66668 	-61.51889 	1105 	1126 	3573890
    # > c6331fbf-641c-4b56-b77f-e0b32089853e 	Ehime 	MEA 	ADM1 	JPN 	33.61667 	132.85 	607 	610 	1864226
    # > 2c7f3ccb-8fc0-4899-a4be-de0b1e1a897e 	United States Virgin Islands 	THE UNITED STATES 	PCLD 	VIR 	18.34829 	-64.98348 	57 	85 	4796775
    # > 04fd36b2-b45e-4b64-bd25-41ef44f16bb0 	Southern District 	Southern Hemisphere 	ADM1 	ISR 	30.66667 	34.83333 	994 	1022 	294952
    # > 04fd36b2-b45e-4b64-bd25-41ef44f16bb0 	Pohjois-Pohjanmaa 	Northern Hemisphere 	ADM1 	FIN 	65.0 	26.41667 	1110 	1138 	830667
    # > b1b534a8-0de6-4656-b66b-bddd4f00fb98 	Bairin Youqi 	Guanzhong Plain 	ADM3 	CHN 	43.55045 	118.95073 	101 	116 	2038538
    # > b1b534a8-0de6-4656-b66b-bddd4f00fb98 	Great Dividing Range 	The Guanzhong Plain 	MTS 	AUS 	-25.0 	147.0 	146 	165 	2164625
    # > b1b534a8-0de6-4656-b66b-bddd4f00fb98 	Bairin Zuoqi 	the Guanzhong Plain 	ADM3 	CHN 	44.18835 	119.24984 	564 	583 	2038537
    # > b1b534a8-0de6-4656-b66b-bddd4f00fb98 	Chang’an Qu 	the Chang'an District 	ADM3 	CHN 	34.03702 	108.93366 	594 	615 	1815800
    # > b1b534a8-0de6-4656-b66b-bddd4f00fb98 	Dihok 	Hu County 	ADM1 	IRQ 	37.06667 	43.13333 	620 	629 	97270
    # >
    return place_df


def flatten_country_groups(df: pd.DataFrame, prefix: str) -> tuple[pd.DataFrame, dict[str, list[tuple[str, str, str]]]]:
    cols = [
        'Group (Lancet 2026)',
        'Group (WHO 2026)',
        'Group (HDI 2026)',
        'Region (IPCC AR6, 6)',
        'Region (IPCC AR6, 10)',
        'Region (WorldBank 2026)',
        'Income group (WorldBank 2026)',
        'Lending category (WorldBank 2026)',
        'Continent (Name)',
    ]

    if 'item_id' not in df.columns:
        df.reset_index(inplace=True)

    # "Melt" the dataframe so columns become a single categorical variable
    df_melted = df.melt(id_vars=['item_id'], value_vars=cols, var_name='column', value_name='grouping')
    # Drop NaNs once globally
    df_melted = df_melted.dropna(subset=['grouping'])
    # Perform a single GroupBy + Size (Vectorized value_counts)
    counts = df_melted.groupby(['item_id', 'column', 'grouping']).size()
    # Reshape to get specific naming convention /  Unstack 'column' and 'grouping' into the header
    result = counts.unstack(level=[1, 2]).fillna(0).astype(int)

    # Fix column names to match '{prefix}_{column}|{grouping}' format and build lookup
    groups: dict[str, list[tuple[str, str, str]]] = {}
    renamed_columns = {f'{prefix}_{col}|{label.name}': label.column for col in cols for label in LABELS[f'{prefix}_{col}'].labels}
    for col, grp in result.columns:
        column = f'{prefix}_{col}|{grp}'
        groups.setdefault(col, []).append((grp, column, renamed_columns[column]))
    result.columns = [f'{prefix}_{col}|{grp}' for col, grp in result.columns]
    result.index.name = 'item_id'
    return result.rename(columns=renamed_columns), groups


def match_grid_years(df_locations: pd.DataFrame, df_grid: pd.DataFrame, publication_year: str = 'Publication year', end_year: str = 'end_year') -> pd.Series:
    """Match each location to a grid end year: the year before publication, or the latest grid year for later publications.

    Locations with no publication year also get the latest grid year; there are none in the exports used here.
    """
    years = df_grid[end_year]
    latest = years.max()
    matched = (df_locations[publication_year].astype('Float64') - 1).fillna(float(latest)).clip(upper=float(latest))
    return matched.where(matched >= years.min()).astype('Int32').rename('grid_year')


def merge_grid_shares(
    df: pd.DataFrame,
    df_locations: pd.DataFrame,
    df_grid: pd.DataFrame,
    shapes: 'GeoDataFrame',
    place_layers: dict[str, 'GeoDataFrame'],
    logger: logging.Logger,
    weight: str = 'population',
    threshold: float = 0.5,
    drivers: dict[str, str] | None = None,
    driver_threshold: float = 0.5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach per-study weighted attribution shares to the papers table.

    `df_grid` holds one row per cell and end year with the cell attributes `area` and `population`.
    Each place becomes its polygon's cells (or the cell containing its point), and ancestors are
    pruned so a paper is scored on its smallest locations. A study is scored only on the variable
    its driver classifier picked: `temp_share` is the share of the paper's deduplicated cell weight
    (the `weight` column of `df_grid`) in a ±2/±3 temperature category at the paper's matched end
    year, `precip_share` likewise. Both are NaN where the classifier did not pick that variable or
    no cell matched the grid. `grid_attributable` marks papers whose larger share reaches `threshold`
    and stays NA where neither variable was scored.
    """
    import geopandas as gpd

    from .place_shapes import prune_ancestor_locations, resolve_place_polygons

    drivers = drivers or {'temp': 'driver|1', 'precip': 'driver|3'}
    location_mask = df_locations['incl_major'] & df_locations['incl_impacts'] & df_locations['incl_location']
    df_locations = df_locations.assign(grid_year=match_grid_years(df_locations, df_grid))
    # location_id collides across merged export sources; renumber the scoring subset
    locations = df_locations[location_mask].copy()
    locations['location_id'] = np.arange(len(locations))
    geometry = resolve_place_polygons(locations, place_layers, adm0=shapes, loglevel=logging.getLevelName(logger.level))
    keep = prune_ancestor_locations(locations, geometry, logger)
    scored = locations.set_index('location_id').loc[keep[keep].index]
    place_geometry = geometry.loc[scored.index]

    # cells: one centroid point per grid cell, with weight columns; polygon places take the cells centred inside them
    cells = df_grid[['LAT', 'LON', 'area', 'population']].drop_duplicates(subset=['LAT', 'LON']).reset_index(drop=True).assign(cell_id=lambda t: t.index)
    cell_points = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells['LON'], cells['LAT']), crs='EPSG:4326')
    polygons = gpd.GeoDataFrame(geometry=place_geometry.where(place_geometry.notna()), crs='EPSG:4326')
    via_polygon = cell_points.sjoin(polygons[polygons.geometry.notna()], predicate='within', how='inner').rename(columns={'index_right': 'location_id'})[
        ['cell_id', 'location_id']
    ]
    # point fallback: LAT/LON already hold the binned cell coords, so an exact coord merge names the cell
    fallback_points = scored.loc[place_geometry[place_geometry.isna()].index, ['LAT', 'LON']]
    via_point = (
        fallback_points.merge(cells[['LAT', 'LON', 'cell_id']], on=['LAT', 'LON'], how='inner')
        .rename_axis('location_id')
        .reset_index()[['cell_id', 'location_id']]
    )
    pairs = (
        pd.concat([via_polygon, via_point])
        .merge(scored[['item_id', 'grid_year']].rename_axis('location_id').reset_index(), on='location_id')
        .merge(cells[['cell_id', 'area', 'population']], on='cell_id')
        .drop_duplicates(subset=['item_id', 'cell_id', 'grid_year'])
    )
    annual = df_grid.merge(cells[['LAT', 'LON', 'cell_id']], on=['LAT', 'LON'])
    matched = pairs.merge(annual[['cell_id', 'end_year', 'temp_cat', 'precip_cat']], left_on=['cell_id', 'grid_year'], right_on=['cell_id', 'end_year'])
    logger.info('%d papers scored on %d (cell, year) matches', matched['item_id'].nunique(), len(matched))

    shares = {}
    for var, column in drivers.items():
        attributed = matched.loc[matched[f'{var}_cat'].abs().isin([2, 3])].groupby('item_id')[weight].sum()
        total = matched.groupby('item_id')[weight].sum()
        share = (attributed.reindex(total.index).fillna(0) / total).astype('Float64')
        driven = (
            (pd.to_numeric(df[column], errors='coerce').reindex(df.index) >= driver_threshold) if column in df.columns else pd.Series(False, index=df.index)
        )
        shares[f'{var}_share'] = share.where(share.index.isin(driven[driven].index)).astype('Float64')
        logger.info(
            '%s: %d of %d driver-classified papers with cells have a share, median %.2f, >0: %d, >=%.2f: %d',
            var,
            int(shares[f'{var}_share'].notna().sum()),
            int(driven.fillna(False).sum()),
            float(shares[f'{var}_share'].median()) if shares[f'{var}_share'].notna().any() else float('nan'),
            int((shares[f'{var}_share'] > 0).sum()),
            threshold,
            int((shares[f'{var}_share'] >= threshold).sum()),
        )
    shares = pd.DataFrame(shares)
    shares['grid_attributable'] = (shares[[f'{var}_share' for var in drivers]].max(axis=1) >= threshold).astype('boolean')
    df = df.join(shares, how='left')
    return df, df_locations
