"""Drift-corrected grid-cell trends and resampled attribution distributions.

Port of `resample_trends.py` and the observation cells of `explore.ipynb` in mcc-apsis/climate-trend-attribution,
vectorised over grid cells and runs. Arrays are (…, lat, lon) with lat ascending.
"""

import re
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import numpy as np
import typer

from climate_health_map.shared import get_logger, load_settings

if TYPE_CHECKING:
    import xarray as xr


def linear_trend(y: np.ndarray, axis: int = 0) -> np.ndarray:
    """OLS slope along `axis` per 100 steps (change per century for annual data); NaN anywhere gives NaN."""
    y = np.moveaxis(y, axis, 0)
    x = np.arange(y.shape[0]) - (y.shape[0] - 1) / 2
    return np.asarray(100 * np.tensordot(x, y, axes=1) / (x @ x))


def drift_corrected(pi: np.ndarray) -> np.ndarray:
    """Subtract each run's per-cell linear fit from piControl (run, time, …) and average over runs."""
    x = np.arange(pi.shape[1]) - (pi.shape[1] - 1) / 2
    slope = np.tensordot(x, pi, axes=([0], [1])) / (x @ x)
    fit = pi.mean(axis=1, keepdims=True) + x[None, :, None, None] * slope[:, None]
    return np.asarray(np.nanmean(pi - fit, axis=0))


def smooth7(y: np.ndarray) -> np.ndarray:
    """Trailing 7-step running mean along axis 1, dropping the first 6 and last 6 means (legacy trimming)."""
    c = np.concatenate([np.zeros_like(y[:, :1]), np.cumsum(y, axis=1)], axis=1)
    means = (c[:, 7:] - c[:, :-7]) / 7
    return np.asarray(means[:, :-6])


def smoothed_std(y: np.ndarray) -> np.ndarray:
    """Std over time of the smoothed series of each run (run, time, …), averaged over runs."""
    return np.asarray(np.nanmean(smooth7(y).std(axis=1), axis=0))


def obs_variability(obs: np.ndarray, af_mean: np.ndarray) -> np.ndarray:
    """Smoothed std of annual observations (time, …) after removing the multi-model all-forcing mean."""
    return np.asarray(smooth7((obs - af_mean)[None])[0].std(axis=0))


def legacy_seeds(n_samples: int = 50, seed: int = 2023) -> np.ndarray:
    """Per-sample seeds as drawn by the legacy code (`np.random.seed(2023)`, `randint(0, 10000, 50)`)."""
    return np.random.RandomState(seed).randint(0, 10000, size=n_samples)


def resample_trends(dc: np.ndarray, window: int, seeds: Sequence[int] | np.ndarray) -> np.ndarray:
    """Trends of random `window`-length segments of drift-corrected piControl (time, …), one per seed."""
    starts = [np.random.RandomState(s).randint(0, dc.shape[0] - window) for s in seeds]
    return np.stack([linear_trend(dc[s : s + window]) for s in starts])


def cell_bounds(centres: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Lower and upper bounds of the cells of a regular axis."""
    half = abs(centres[1] - centres[0]) / 2
    return centres - half, centres + half


def overlap_weights(dst_lo: np.ndarray, dst_hi: np.ndarray, src_lo: np.ndarray, src_hi: np.ndarray, period: float | None = None) -> np.ndarray:
    """Overlap length of each destination interval with each source interval, optionally periodic."""
    w = np.zeros((len(dst_lo), len(src_lo)))
    for shift in (-period, 0.0, period) if period else (0.0,):
        hi = np.minimum(dst_hi[:, None], src_hi[None, :] + shift)
        lo = np.maximum(dst_lo[:, None], src_lo[None, :] + shift)
        w += np.clip(hi - lo, 0, None)
    return w


def conservative_regrid(values: np.ndarray, src_lat: np.ndarray, src_lon: np.ndarray, dst_lat: np.ndarray, dst_lon: np.ndarray) -> np.ndarray:
    """Area-conservative regrid over the last two axes between regular lat-lon grids with cells bounded by parallels and meridians."""
    sin_bounds = [np.sin(np.deg2rad(np.clip(b, -90, 90))) for b in (*cell_bounds(dst_lat), *cell_bounds(src_lat))]
    w_lat = overlap_weights(*sin_bounds)
    w_lon = overlap_weights(*cell_bounds(dst_lon), *cell_bounds(src_lon), period=360.0)
    return np.asarray((w_lat @ (values @ w_lon.T)) / np.outer(w_lat.sum(axis=1), w_lon.sum(axis=1)))


def member_of(path: Path) -> str:
    """Variant label (e.g. r1i1p1f1) from a CMIP6-ng file name."""
    return path.stem.split('_')[-2]


def legacy_files(source: Path, variable: str, model: str, experiment: str, grid: str = 'g5') -> list[Path]:
    """Files matched by the legacy glob `r*1p1f1`, in the legacy (lexical) order."""
    return sorted((source / variable / model / grid).glob(f'{variable}_ann_{model}_{experiment}_r*1p1f1_{grid}.nc'))


def experiment_files(source: Path, variable: str, model: str, experiment: str, grid: str) -> dict[str, Path]:
    """All files of one experiment keyed by variant label."""
    paths = (source / variable / model / grid).glob(f'{variable}_ann_{model}_{experiment}_*_{grid}.nc')
    return {member_of(p): p for p in paths if re.fullmatch(r'r\d+i\d+p\d+f\d+', member_of(p))}


def family_of(label: str) -> str:
    """Initialisation, physics and forcing indices of a variant label (r3i1p1f2 -> i1p1f2)."""
    return label[label.index('i') :]


def parent_label(path: Path) -> str:
    """piControl variant label a run branched from (`parent_variant_label`)."""
    import netCDF4

    with netCDF4.Dataset(path) as ds:
        return str(ds.getncattr('parent_variant_label'))


def select_runs(source: Path, variable: str, model: str, scenario: str, grid: str, legacy: bool) -> tuple[dict[str, list[list[Path]]], dict[str, list[str]]]:
    """File lists and variant labels per run for all-forcing (historical + scenario), historical, hist-nat and piControl.

    The default pairs historical and scenario runs by variant label and keeps the family (i, p, f indices) with most pairs,
    ties going to the lexically first. Historical and hist-nat runs are restricted to that family, and piControl runs are
    the parents of its historical runs. Labels also list unpaired historical and scenario runs and parents with no file.
    legacy reproduces the old selection: glob `r*1p1f1` and historical i paired with scenario i modulo the scenario count.
    """
    if legacy:
        hist, ssp, hn, pi = (legacy_files(source, variable, model, e, grid) for e in ('historical', scenario, 'hist-nat', 'piControl'))
        af = [[h, ssp[i % len(ssp)]] for i, h in enumerate(hist)] if ssp else []
        return (
            {'af': af, 'hn': [[p] for p in hn], 'pi': [[p] for p in pi]},
            {'af': [f'{member_of(h)}+{member_of(s)}' for h, s in af], 'hn': [member_of(p) for p in hn], 'pi': [member_of(p) for p in pi]},
        )
    hist_m, ssp_m, hn_m, pi_m = (experiment_files(source, variable, model, e, grid) for e in ('historical', scenario, 'hist-nat', 'piControl'))
    paired = sorted(hist_m.keys() & ssp_m.keys())
    labels: dict[str, list[str]] = {k: [] for k in ('af', 'hist', 'hn', 'pi', 'missing_pi')}
    labels['unpaired'] = sorted(hist_m.keys() ^ ssp_m.keys())
    if paired:
        counts = Counter(family_of(m) for m in paired)
        family = max(sorted(counts), key=counts.__getitem__)
        labels['af'] = [m for m in paired if family_of(m) == family]
        labels['hist'] = sorted(m for m in hist_m if family_of(m) == family)
        labels['hn'] = sorted(m for m in hn_m if family_of(m) == family)
        parents = {parent_label(hist_m[m]) for m in labels['hist']}
        labels['pi'] = sorted(parents & pi_m.keys())
        labels['missing_pi'] = sorted(parents - pi_m.keys())
    files = {
        'af': [[hist_m[m], ssp_m[m]] for m in labels['af']],
        'hist': [[hist_m[m]] for m in labels['hist']],
        'hn': [[hn_m[m]] for m in labels['hn']],
        'pi': [[pi_m[m]] for m in labels['pi']],
    }
    return files, labels


def read_annual(path: Path, variable: str) -> 'xr.DataArray':
    """Read one annual-mean file into (year, lat, lon) with fill values as NaN.

    Reads with netCDF4 directly: loading these files through xarray's netCDF4 backend segfaults
    under Python 3.14 / numpy 2.4 (in xarray's fill-value masking).
    """
    import netCDF4
    import xarray as xr

    with netCDF4.Dataset(path) as ds:
        t = ds['time']
        years = [d.year for d in cast(np.ndarray, netCDF4.num2date(t[:], t.units, getattr(t, 'calendar', 'standard')))]
        values = np.ma.filled(ds[variable][:].astype(float), np.nan)
        lat, lon = np.asarray(ds['lat'][:]), np.asarray(ds['lon'][:])
    return xr.DataArray(values, coords={'year': years, 'lat': lat, 'lon': lon}, dims=('year', 'lat', 'lon'))


def era5_annual_means(path: Path, variable: str, month_weighted: bool = True) -> 'xr.DataArray':
    """Annual means (year, lat, lon) of a monthly ERA5 netCDF file on its native grid.

    Handles the legacy (`time`) and current (`valid_time`) CDS layouts; month_weighted weights months by their length,
    as `cdo yearmonmean` does for the CMIP6 inputs (the legacy observations used an unweighted mean).
    """
    import calendar

    import netCDF4
    import xarray as xr

    with netCDF4.Dataset(path) as ds:
        t = ds['valid_time' if 'valid_time' in ds.variables else 'time']
        dates = cast(np.ndarray, netCDF4.num2date(t[:], t.units, getattr(t, 'calendar', 'standard')))
        years = np.array([d.year for d in dates])
        days = np.array([calendar.monthrange(d.year, d.month)[1] for d in dates], dtype=np.float64)
        lat, lon = np.asarray(ds['latitude'][:]), np.asarray(ds['longitude'][:])
        means = []
        for year in np.unique(years):
            idx = np.flatnonzero(years == year)
            block = np.ma.filled(ds[variable][idx[0] : idx[-1] + 1].astype(float), np.nan)
            w = days[idx] if month_weighted else np.ones(len(idx))
            means.append(np.tensordot(w / w.sum(), block, axes=1))
    return xr.DataArray(np.stack(means), coords={'year': np.unique(years), 'lat': lat, 'lon': lon}, dims=('year', 'lat', 'lon'))


def load_annual(paths: Sequence[Sequence[Path]], variable: str, first_year: int, last_year: int) -> 'xr.DataArray':
    """Load runs into (run, year, lat, lon); each run is a sequence of files concatenated in time (e.g. historical + SSP)."""
    import xarray as xr

    runs = []
    for files in paths:
        da = xr.concat([read_annual(p, variable) for p in files], dim='year')
        runs.append(da.sel(year=slice(first_year, last_year)).sortby('lat'))
    return xr.concat(runs, dim='run', join='outer')


def model_trends(runs: 'xr.DataArray', start_year: int, end_year: int) -> np.ndarray:
    """Per-run trends over start_year..end_year averaged over runs; runs with missing years in the window are skipped."""
    sel = runs.sel(year=slice(start_year, end_year)).values
    return np.asarray(np.nanmean(linear_trend(sel, axis=1), axis=0))


def spliced_mean(hist: 'xr.DataArray', af: 'xr.DataArray', baseline: tuple[int, int]) -> 'xr.DataArray':
    """All-forcing ensemble mean as one run (run, year, …): the mean of all historical runs up to their last year,
    then the mean of the paired historical + scenario runs plus the difference of the two means over the baseline years."""
    import xarray as xr

    h, a = hist.mean('run'), af.mean('run')
    offset = (h - a).sel(year=slice(*baseline)).mean('year')
    last = int(h['year'].max())
    return xr.concat([h.sel(year=slice(None, last)), (a + offset).sel(year=slice(last + 1, None))], dim='year').expand_dims(run=1)


ERA5_NAMES = {'tas': 't2m', 'pr': 'tp'}
# ERA5 monthly-mean tp is in m/day; CMIP6 pr is in kg m-2 s-1.
ERA5_FACTORS = {'tas': 1.0, 'pr': 1000 / 86400}


def trends(
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    variable: Annotated[str, typer.Option(help='Climate variable to attribute (tas or pr)')] = 'tas',
    models_dir: Annotated[
        Path | None, typer.Option(help='CMIP6 annual files as <variable>/<model>/<grid>/*.nc (default: <DATA_ROOT>/attribution/legacy/models)')
    ] = None,
    obs: Annotated[Path | None, typer.Option(help='Monthly ERA5 netCDF (default: <DATA_ROOT>/attribution/era5/<variable>.nc)')] = None,
    target: Annotated[Path | None, typer.Option(help='Output directory (default: <DATA_ROOT>/attribution/trends/<variable>_<grid>)')] = None,
    grid: Annotated[str | None, typer.Option(help='Grid subdirectory and file suffix of the CMIP6 files (default: grid in config/attribution.yaml)')] = None,
    models: Annotated[list[str] | None, typer.Option(help='Models to use (default: models in config/attribution.yaml)')] = None,
    scenario: Annotated[str | None, typer.Option(help='Scenario extending the historical runs (default: scenario in config/attribution.yaml)')] = None,
    start_year: Annotated[int, typer.Option(help='First year of model trend windows')] = 1951,
    obs_start_year: Annotated[
        int | None, typer.Option(help='First year of observed trend windows and of the variability estimate (default: value in config/attribution.yaml)')
    ] = None,
    first_end_year: Annotated[int, typer.Option(help='First trend end year')] = 1990,
    latest_year: Annotated[int, typer.Option(help='Last trend end year')] = 2023,
    min_hist_nat: Annotated[int, typer.Option(help='Minimum number of hist-nat runs for a model to be used')] = 3,
    n_samples: Annotated[int, typer.Option(help='Number of resampled piControl segments')] = 50,
    splice_baseline_start: Annotated[int, typer.Option(help='First year of the baseline aligning paired scenario runs with all historical runs')] = 1995,
    splice_baseline_end: Annotated[int, typer.Option(help='Last year of the splice baseline')] = 2014,
    legacy: Annotated[bool, typer.Option(help='Reproduce the legacy run selection, piControl window length and unweighted observed annual means')] = False,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Compute drift-corrected trends and resampled attribution distributions, one netCDF per model plus obs.nc."""
    import xarray as xr

    logger = get_logger('attribution.trends', loglevel=loglevel)
    settings = load_settings(config)
    grid = grid or settings.ATTRIBUTION.grid
    scenario = scenario or settings.ATTRIBUTION.scenario
    obs_start_year = obs_start_year or settings.ATTRIBUTION.obs_start_year
    models = models or settings.ATTRIBUTION.models
    models_dir = models_dir or settings.DATA_ROOT / 'attribution' / 'legacy' / 'models'
    obs = obs or settings.DATA_ROOT / 'attribution' / 'era5' / f'{variable}.nc'
    target = target or settings.DATA_ROOT / 'attribution' / 'trends' / f'{variable}_{grid}'
    target.mkdir(parents=True, exist_ok=True)
    end_years = np.arange(first_end_year, latest_year + 1)

    runs = {}
    members = {}
    for model in models:
        files, labels = select_runs(models_dir, variable, model, scenario, grid, legacy)
        n = {k: len(v) for k, v in files.items()}
        if labels.get('unpaired'):
            logger.info('%s: %d historical or %s runs without a counterpart: %s', model, len(labels['unpaired']), scenario, ' '.join(labels['unpaired']))
        if labels.get('missing_pi'):
            logger.warning('%s: piControl parents without a file: %s', model, ' '.join(labels['missing_pi']))
        if n['af'] < 1 or n['hn'] < min_hist_nat or n['pi'] < 1:
            logger.warning('Skipping %s: %s', model, n)
            continue
        logger.info('Loading %s: %s', model, n)
        af = load_annual(files['af'], variable, obs_start_year, latest_year)
        runs[model] = {
            'af': af,
            'af_mean': af
            if legacy
            else spliced_mean(load_annual(files['hist'], variable, obs_start_year, latest_year), af, (splice_baseline_start, splice_baseline_end)),
            'hn': load_annual(files['hn'], variable, obs_start_year, latest_year),
            'pi': load_annual(files['pi'], variable, -(10**6), 10**6),
        }
        members[model] = labels
    if not runs:
        raise typer.BadParameter(f'No usable models under {models_dir}')
    lat, lon = next(iter(runs.values()))['af']['lat'].values, next(iter(runs.values()))['af']['lon'].values

    logger.info('Reading observations from %s', obs)
    native = era5_annual_means(obs, ERA5_NAMES[variable], month_weighted=not legacy) * ERA5_FACTORS[variable]
    annual = conservative_regrid(native.values, native['lat'].values, native['lon'].values, lat, lon)
    obs_years = native['year'].values
    in_obs = (obs_years >= obs_start_year) & (obs_years <= latest_year)
    af_mean = np.concatenate([r['af'].sel(year=obs_years[in_obs]).values for r in runs.values()]).mean(axis=0)
    obs_std = obs_variability(annual[in_obs], af_mean)
    obs_trends = np.stack([linear_trend(annual[(obs_years >= obs_start_year) & (obs_years <= y)]) for y in end_years])
    coords = {'end_year': end_years, 'lat': lat, 'lon': lon}
    xr.Dataset(
        {'trend': (('end_year', 'lat', 'lon'), obs_trends), 'std': (('lat', 'lon'), obs_std)},
        coords=coords,
        attrs={
            'source': str(obs),
            'start_year': obs_start_year,
            'legacy': int(legacy),
            'grid': grid,
            'attribution': settings.ATTRIBUTION.model_dump_json(),
        },
    ).to_netcdf(target / 'obs.nc')

    seeds = legacy_seeds(n_samples)
    for model, r in runs.items():
        logger.info('Trends and resampling for %s', model)
        dc = drift_corrected(r['pi'].values)
        std_corr = obs_std / smoothed_std(r['pi'].values)
        out: dict[str, list[np.ndarray]] = {'trend_af': [], 'trend_hn': [], 'resampled_af': [], 'resampled_hn': []}
        for year in end_years.tolist():
            window = year - start_year + (0 if legacy else 1)
            samples = resample_trends(dc, window, seeds) * std_corr
            t_af, t_hn = model_trends(r['af_mean'], start_year, year), model_trends(r['hn'], start_year, year)
            for key, arr in (('trend_af', t_af), ('trend_hn', t_hn), ('resampled_af', samples + t_af), ('resampled_hn', samples + t_hn)):
                out[key].append(arr)
        hn_last = int(r['hn']['year'].max())
        if hn_last < latest_year:
            logger.warning('%s hist-nat ends in %d; natural-only trends for later end years stop at %d', model, hn_last, hn_last)
        xr.Dataset(
            {
                'trend_af': (('end_year', 'lat', 'lon'), np.stack(out['trend_af'])),
                'trend_hn': (('end_year', 'lat', 'lon'), np.stack(out['trend_hn'])),
                'resampled_af': (('end_year', 'sample', 'lat', 'lon'), np.stack(out['resampled_af'])),
                'resampled_hn': (('end_year', 'sample', 'lat', 'lon'), np.stack(out['resampled_hn'])),
                'std_corr': (('lat', 'lon'), std_corr),
            },
            coords=coords | {'sample': np.arange(n_samples)},
            attrs={
                'model': model,
                'scenario': scenario,
                'start_year': start_year,
                'legacy': int(legacy),
                'runs_af': len(r['af']['run']),
                'runs_hn': len(r['hn']['run']),
                'runs_pi': len(r['pi']['run']),
                'runs_hist': len(members[model].get('hist', [])),
                'members_af': ' '.join(members[model]['af']),
                'members_hist': ' '.join(members[model].get('hist', [])),
                'members_hn': ' '.join(members[model]['hn']),
                'members_pi': ' '.join(members[model]['pi']),
                'splice_baseline': '' if legacy else f'{splice_baseline_start}-{splice_baseline_end}',
                'hist_nat_last_year': hn_last,
            },
        ).to_netcdf(target / f'{model}.nc')
    logger.info('Wrote %d model files and obs.nc to %s', len(runs), target)


if __name__ == '__main__':
    typer.run(trends)
