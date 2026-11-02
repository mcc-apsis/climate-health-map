"""Per-cell geometry and population for the study grid."""

import json
from pathlib import Path
from typing import Annotated

import numpy as np
import pandas as pd
import typer

from climate_health_map.shared import Settings, get_logger, load_settings

RESOLUTION = 2.5
EARTH_RADIUS_KM = 6371.0
PRODUCT = 'WorldPop 2026 1km, R2025A (global_pop_2026_CN_1km_R2025A_UA_v1.tif)'


def population_tif(settings: Settings) -> Path:
    """WorldPop population raster in the synced shapes tree."""
    return Path(settings.DATA_ROOT) / 'shapes_2026/shapes_2026/global_pop_2026_CN_1km_R2025A_UA_v1.tif'


def cells_csv(settings: Settings) -> Path:
    """Derived per-cell attributes, written by `derive-cells` and read by `load_grid_data`."""
    return Path(settings.DATA_ROOT) / 'geographies/cells.csv'


def cell_areas(lat: np.ndarray) -> np.ndarray:
    """Spherical areas in km² of `RESOLUTION`-degree cells centred at the given latitudes."""
    f0, f1 = np.radians(lat - RESOLUTION / 2), np.radians(lat + RESOLUTION / 2)
    return EARTH_RADIUS_KM**2 * np.radians(RESOLUTION) * (np.sin(f1) - np.sin(f0))


def zonal_cells(raster, resolution: float = RESOLUTION, chunk_rows: int = 1200) -> tuple[np.ndarray, np.ndarray]:
    """Sum population and count land pixels per cell of an open population raster, read in row chunks.

    Returns (n_lat, n_lon) arrays. Raster rows map to cells whole (the raster may cover fewer latitudes than the
    globe); columns tile exactly. The 746M-pixel WorldPop grid does not fit in memory as any useful dtype.
    """
    import rasterio.windows

    transform, width, height = raster.transform, raster.width, raster.height
    if transform.b or transform.d:
        raise typer.BadParameter('rotated rasters are not supported')
    n_lon = int(360 / resolution)
    n_lat = int(180 / resolution)
    lat_idx = np.floor(((transform.f + (np.arange(height) + 0.5) * transform.e) + 90) / resolution).astype(int)
    lon_idx = np.floor(((transform.c + (np.arange(width) + 0.5) * transform.a) + 180) / resolution).astype(int)
    if lon_idx.min() < 0 or lon_idx.max() >= n_lon or lat_idx.min() < 0 or lat_idx.max() >= n_lat:
        raise typer.BadParameter(f'raster {transform} reaches outside the {resolution}-degree grid')
    pop_sum, land_px = np.zeros((n_lat, n_lon)), np.zeros((n_lat, n_lon))
    for r0 in range(0, height, chunk_rows):
        pop = raster.read(1, window=rasterio.windows.Window(0, r0, width, min(chunk_rows, height - r0)))
        land = np.isfinite(pop) & (pop != raster.nodata)
        pop *= land
        rows = lat_idx[r0 : r0 + pop.shape[0]]
        for i in np.unique(rows):
            idx = np.flatnonzero(rows == i)
            x = np.tile(lon_idx, len(idx))
            pop_sum[i] += np.bincount(x, weights=pop[idx].ravel(), minlength=n_lon)
            land_px[i] += np.bincount(x, weights=land[idx].ravel(), minlength=n_lon)
    return pop_sum, land_px


def derive_cells(
    source: Annotated[Path | None, typer.Option(help='WorldPop population GeoTIFF (default: the WorldPop 2026 raster under the data root)')] = None,
    target: Annotated[Path | None, typer.Option(help='Target CSV file (default: geographies/cells.csv under the data root)')] = None,
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Derive per-cell area, land mask and population on the study grid from a population raster."""
    import rasterio

    logger = get_logger('geographies.grid', loglevel=loglevel)
    settings = load_settings(config)
    source = source or population_tif(settings)
    target = target or cells_csv(settings)
    with rasterio.open(source) as raster:
        if raster.crs is not None and not raster.crs.equals('EPSG:4326'):
            raise typer.BadParameter(f'{source} is not in EPSG:4326')
        logger.info('Reading %s with %s in row chunks', source, raster.transform)
        pop_sum, land_px = zonal_cells(raster)

    lat = np.arange(-90 + RESOLUTION / 2, 90, RESOLUTION)
    lon = np.arange(-180 + RESOLUTION / 2, 180, RESOLUTION)
    df = pd.DataFrame(
        {
            'LAT': np.repeat(lat, len(lon)),
            'LON': np.tile(lon, len(lat)),
            'area': np.repeat(cell_areas(lat), len(lon)),
            'is_land': (land_px > 0).ravel(),
            'population': pop_sum.ravel(),
        }
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False)
    target.with_suffix('.provenance.json').write_text(json.dumps({'source': str(source), 'product': PRODUCT, 'grid': f'{RESOLUTION}°'}, indent=2) + '\n')
    logger.info('Wrote %d cells (%d land, %s population) to %s', len(df), int(df['is_land'].sum()), f"{df['population'].sum():,.0f}", target)


if __name__ == '__main__':
    typer.run(derive_cells)
