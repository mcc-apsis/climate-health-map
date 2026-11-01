from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from scipy.stats import norm

from climate_health_map.attribution.provenance import (
    StaleOutputError,
    categories_path,
    check_provenance,
    clear_provenance,
    trends_dir as trends_path,
    used_settings,
    write_provenance,
)
from climate_health_map.shared import get_logger, load_settings


def read_arrays(path: Path, names: Sequence[str]) -> dict[str, np.ndarray]:
    """Read variables or coordinates of a netCDF file as float arrays, with fill values as NaN."""
    import netCDF4

    with netCDF4.Dataset(path) as ds:
        return {name: np.ma.filled(ds[name][:].astype(float), np.nan) for name in names}


def assign_categories(
    obs: np.ndarray,
    pa: np.ndarray,
    ph: np.ndarray,
    af_mean: np.ndarray,
    hn_mean: np.ndarray,
    tail: float = 5.0,
) -> np.ndarray:
    """Attribution category per cell from the observed trend, its percentiles on the all-forcing (pa) and natural-only (ph) distributions
    and the means of the two distributions.

    A trend beyond the natural-only range in its own direction is detectable. If it has the sign of the all-forcing mean,
    it is categorised ±3, ±2 or ±1 as stronger than, within or weaker than the all-forcing range, with the sign of the trend.
    If it has the opposite sign, it is ±4. Trends within or against the natural-only range are 0.
    A trend stronger than the all-forcing range must also be closer to the all-forcing than to the natural-only mean,
    otherwise it is ±1 (Knutson and Zeng, 2018).
    The result is NaN where the observed trend or the all-forcing mean is zero or an input is missing.
    """
    upper = 100 - tail
    sign = np.sign(af_mean)
    detectable = ((obs > 0) & (ph >= upper)) | ((obs < 0) & (ph <= tail))
    stronger = ((sign > 0) & (pa >= upper)) | ((sign < 0) & (pa <= tail))
    weaker = ((sign > 0) & (pa <= tail)) | ((sign < 0) & (pa >= upper))
    magnitude = np.select([stronger, weaker], [3.0, 1.0], default=2.0)
    magnitude = np.where((magnitude == 3) & ~(np.abs(obs - af_mean) < np.abs(obs - hn_mean)), 1.0, magnitude)
    cats = np.where(detectable, np.where(np.sign(obs) == sign, sign * magnitude, 4 * np.sign(obs)), 0.0)
    valid = np.isfinite(obs) & np.isfinite(pa) & np.isfinite(ph) & np.isfinite(af_mean) & np.isfinite(hn_mean) & (obs != 0) & (sign != 0)
    return np.where(valid, cats, np.nan)


def categorize_trends(obs: np.ndarray, af: np.ndarray, hn: np.ndarray) -> np.ndarray:
    """Attribution category per cell from the observed trend (lat, lon) and the all-forcing and natural-only trend samples (sample, lat, lon).

    Each sample set is fitted with a normal distribution, and the observed trend is placed on it as a percentile.
    """
    pa = norm.cdf(obs, af.mean(axis=0), af.std(axis=0)) * 100
    ph = norm.cdf(obs, hn.mean(axis=0), hn.std(axis=0)) * 100
    return assign_categories(obs, pa, ph, af.mean(axis=0), hn.mean(axis=0))


LEVELS = np.arange(101.0)


def percentile_of(obs: np.ndarray, quantiles: np.ndarray) -> np.ndarray:
    """Percentile (0-100) of the observed trend (lat, lon) on a distribution given by its quantiles at LEVELS (level, lat, lon).

    Interpolates linearly between levels; trends outside the quantile range give 0 or 100.
    """
    below = (quantiles <= obs[None]).sum(axis=0)
    lo = np.clip(below - 1, 0, len(LEVELS) - 2)[None]
    q_lo, q_hi = (np.take_along_axis(quantiles, i, axis=0)[0] for i in (lo, lo + 1))
    with np.errstate(divide='ignore', invalid='ignore'):
        frac = np.where(q_hi > q_lo, (obs - q_lo) / (q_hi - q_lo), 0.0)
    p = LEVELS[lo[0]] + np.clip(frac, 0, 1) * (LEVELS[1] - LEVELS[0])
    p = np.where(below == 0, 0.0, np.where(below == len(LEVELS), 100.0, p))
    return np.where(np.isfinite(obs) & np.isfinite(quantiles).all(axis=0), p, np.nan)


def categorize_all(obs_trend: np.ndarray, model_files: Sequence[Path], average: bool = False) -> np.ndarray:
    """Categories (end_year, lat, lon) from observed trends (end_year, lat, lon) and the resampled samples of each model file.

    By default the samples of all models are pooled and fitted with a normal distribution.
    With average, each model's distribution is summarised by its percentiles, and the percentiles are averaged over models,
    giving a distribution with the average characteristics of the models and no assumption of normality.
    """
    if not average:
        runs = [read_arrays(p, ['resampled_af', 'resampled_hn']) for p in model_files]
        af = np.concatenate([r['resampled_af'] for r in runs], axis=1)
        hn = np.concatenate([r['resampled_hn'] for r in runs], axis=1)
        return np.stack([categorize_trends(obs_trend[i], af[i], hn[i]) for i in range(len(obs_trend))])
    shape = (len(obs_trend), len(LEVELS), *obs_trend.shape[1:])
    quantiles = {k: np.zeros(shape) for k in ('resampled_af', 'resampled_hn')}
    means = {k: np.zeros(obs_trend.shape) for k in ('resampled_af', 'resampled_hn')}
    for path in model_files:
        for key, arr in read_arrays(path, ['resampled_af', 'resampled_hn']).items():
            quantiles[key] += np.percentile(arr, LEVELS, axis=1).swapaxes(0, 1)
            means[key] += arr.mean(axis=1)
    n = len(model_files)
    cats = []
    for i in range(len(obs_trend)):
        pa, ph = (percentile_of(obs_trend[i], quantiles[k][i] / n) for k in ('resampled_af', 'resampled_hn'))
        cats.append(assign_categories(obs_trend[i], pa, ph, means['resampled_af'][i] / n, means['resampled_hn'][i] / n))
    return np.stack(cats)


def categorize(
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    variable: Annotated[str, typer.Option(help='Climate variable to categorize (tas: pooled normal distribution, pr: average of model percentiles)')] = 'tas',
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Assign per-cell attribution categories from resampled trend distributions."""
    import xarray as xr

    logger = get_logger('attribution.categorize', loglevel=loglevel)
    if variable not in ('tas', 'pr'):
        raise typer.BadParameter('variable must be tas or pr')
    settings = load_settings(config)
    grid = settings.ATTRIBUTION.grid
    models = settings.ATTRIBUTION.models
    trends_dir = trends_path(settings, variable)
    target = categories_path(settings, variable)
    model_files = [trends_dir / f'{m}.nc' for m in models]
    missing = [p.name for p in model_files if not p.is_file()]
    if missing:
        raise typer.BadParameter(f'Missing trend files in {trends_dir}: {", ".join(missing)}')

    try:
        upstream = check_provenance(trends_dir, used_settings(settings), f'healthmap attribution trends --variable {variable}')
    except StaleOutputError as e:
        raise typer.BadParameter(str(e)) from e
    clear_provenance(target)

    obs = read_arrays(trends_dir / 'obs.nc', ['trend', 'end_year', 'lat', 'lon'])
    logger.info('Categorizing %d end years from %d models', len(obs['end_year']), len(model_files))
    cats = categorize_all(obs['trend'], model_files, average=variable == 'pr')

    target.parent.mkdir(parents=True, exist_ok=True)
    xr.Dataset(
        {'category': (('end_year', 'lat', 'lon'), cats)},
        coords={'end_year': obs['end_year'].astype(int), 'lat': obs['lat'], 'lon': obs['lon']},
        attrs={
            'models': ' '.join(p.stem for p in model_files),
            'distribution': 'average of model percentiles' if variable == 'pr' else 'pooled normal',
            'grid': grid,
            'source': str(trends_dir),
            'attribution': settings.ATTRIBUTION.model_dump_json(),
        },
    ).to_netcdf(target)
    write_provenance(target, variable, grid, used_settings(settings), upstream)
    logger.info('Wrote categories to %s', target)


if __name__ == '__main__':
    typer.run(categorize)
