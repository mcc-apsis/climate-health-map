from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from scipy.stats import norm

from climate_health_map.shared import get_logger, load_settings


def read_arrays(path: Path, names: Sequence[str]) -> dict[str, np.ndarray]:
    """Read variables or coordinates of a netCDF file as float arrays, with fill values as NaN."""
    import netCDF4

    with netCDF4.Dataset(path) as ds:
        return {name: np.ma.filled(ds[name][:].astype(float), np.nan) for name in names}


def categorize_trends(
    obs: np.ndarray,
    af: np.ndarray,
    hn: np.ndarray,
    tail: float = 5.0,
    pos_hn_cut: float = 96.0,
    neg_hn_cut: float = 4.0,
) -> np.ndarray:
    """Attribution category per cell from the observed trend (lat, lon) and the all-forcing and natural-only trend samples (sample, lat, lon).

    Each sample set is fitted with a normal distribution, and the observed trend is placed on it as a percentile.
    The result is NaN where the observed trend is zero or an input is missing.
    """
    pa = norm.cdf(obs, af.mean(axis=0), af.std(axis=0)) * 100
    ph = norm.cdf(obs, hn.mean(axis=0), hn.std(axis=0)) * 100
    upper = 100 - tail
    in_af = (pa > tail) & (pa < upper)
    in_hn = (ph > tail) & (ph < upper)
    pos, neg = obs > 0, obs < 0
    conditions = [
        pos & in_af & (ph <= pos_hn_cut),
        pos & in_af,
        pos & in_hn,
        pos & (pa <= tail) & (ph >= upper),
        pos & (pa >= upper),
        pos & (ph <= tail),
        neg & in_af & (ph >= neg_hn_cut),
        neg & in_af,
        neg & in_hn,
        neg & (ph <= tail) & (pa >= upper),
        neg & (pa <= tail),
        neg & (ph >= upper),
    ]
    values = [0.0, 2.0, 0.0, 1.0, 3.0, 0.0, 0.0, -2.0, 0.0, -1.0, -3.0, 0.0]
    cats = np.select(conditions, values, default=np.nan)
    return np.where(np.isfinite(obs) & np.isfinite(pa) & np.isfinite(ph), cats, np.nan)


def categorize_all(obs_trend: np.ndarray, model_files: Sequence[Path]) -> np.ndarray:
    """Categories (end_year, lat, lon) from observed trends (end_year, lat, lon) and the resampled samples of each model file."""
    runs = [read_arrays(p, ['resampled_af', 'resampled_hn']) for p in model_files]
    af = np.concatenate([r['resampled_af'] for r in runs], axis=1)
    hn = np.concatenate([r['resampled_hn'] for r in runs], axis=1)
    return np.stack([categorize_trends(obs_trend[i], af[i], hn[i]) for i in range(len(obs_trend))])


def categorize(
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    variable: Annotated[str, typer.Option(help='Climate variable to categorize (tas only until precipitation has a suitable test)')] = 'tas',
    trends_dir: Annotated[
        Path | None, typer.Option(help='Trend files as obs.nc and <model>.nc (default: <DATA_ROOT>/attribution/trends/<variable>_<grid>)')
    ] = None,
    target: Annotated[Path | None, typer.Option(help='Output netCDF (default: <DATA_ROOT>/attribution/categories/<variable>_<grid>.nc)')] = None,
    grid: Annotated[str, typer.Option(help='Grid suffix of the trend directory (g5 or g025)')] = 'g5',
    models: Annotated[list[str] | None, typer.Option(help='Models to use (default: every <model>.nc in the trends directory)')] = None,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Assign per-cell attribution categories from resampled trend distributions."""
    import xarray as xr

    logger = get_logger('attribution.categorize', loglevel=loglevel)
    if variable != 'tas':
        raise typer.BadParameter('Only tas is categorized: precipitation trends are not normally distributed, so they need a different test')
    settings = load_settings(config)
    trends_dir = trends_dir or settings.DATA_ROOT / 'attribution' / 'trends' / f'{variable}_{grid}'
    target = target or settings.DATA_ROOT / 'attribution' / 'categories' / f'{variable}_{grid}.nc'
    model_files = [trends_dir / f'{m}.nc' for m in models] if models else sorted(p for p in trends_dir.glob('*.nc') if p.name != 'obs.nc')
    if not model_files:
        raise typer.BadParameter(f'No model trend files in {trends_dir}')

    obs = read_arrays(trends_dir / 'obs.nc', ['trend', 'end_year', 'lat', 'lon'])
    logger.info('Categorizing %d end years from %d models', len(obs['end_year']), len(model_files))
    cats = categorize_all(obs['trend'], model_files)

    target.parent.mkdir(parents=True, exist_ok=True)
    xr.Dataset(
        {'category': (('end_year', 'lat', 'lon'), cats)},
        coords={'end_year': obs['end_year'].astype(int), 'lat': obs['lat'], 'lon': obs['lon']},
        attrs={'models': ' '.join(p.stem for p in model_files), 'source': str(trends_dir)},
    ).to_netcdf(target)
    logger.info('Wrote categories to %s', target)


if __name__ == '__main__':
    typer.run(categorize)
