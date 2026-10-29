"""Compare the ported attribution trends with the legacy 5° outputs in data/attribution/legacy.

Reproduces the legacy file selection (glob `r*1p1f1`, historical paired with ssp370 by list position)
and quirks (piControl window `end_year - start_year`, observed trends from 1940, model trends from 1951).

    uv run --extra analysis python scripts/validate_legacy_trends.py --model MIROC6
    uv run --extra analysis python scripts/validate_legacy_trends.py --obs
"""

import pickle
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
import xarray as xr

from climate_health_map.attribution.trends import (
    conservative_regrid,
    drift_corrected,
    era5_annual_means,
    legacy_files,
    legacy_seeds,
    linear_trend,
    load_annual,
    model_trends,
    obs_variability,
    resample_trends,
    smoothed_std,
)

LEGACY = Path('data/attribution/legacy')
# Models with legacy trend files; includes MRI-ESM2-0, which the legacy analysis dropped
LEGACY_FILES = ['MIROC6', 'IPSL-CM6A-LR', 'CanESM5', 'GFDL-ESM4', 'ACCESS-ESM1-5', 'BCC-CSM2-MR', 'MRI-ESM2-0', 'NorESM2-LM']
START_YEAR = 1951
OBS_START_YEAR = 1940
END_YEARS = range(1990, 2024)
LATEST_YEAR = 2023
GRID_5 = (np.arange(-87.5, 90, 5.0), np.arange(-177.5, 180, 5.0))


def diff(label: str, new: np.ndarray, old: np.ndarray) -> float:
    """Print and return the max abs difference; legacy arrays are lat-descending."""
    old = np.flip(np.asarray(old), axis=-2)
    d = float(np.nanmax(np.abs(new - old)))
    r = np.corrcoef(new.ravel(), old.ravel())[0, 1]
    print(f'  {label:<28} max|diff|={d:.3g}  r={r:.6f}  nan(new/old)={np.isnan(new).sum()}/{np.isnan(old).sum()}')
    return d


def load_model(model: str) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray] | None:
    src = LEGACY / 'models'
    hist, ssp, hn, pi = (legacy_files(src, 'tas', model, e) for e in ('historical', 'ssp370', 'hist-nat', 'piControl'))
    if not hist or not ssp or len(hn) < 3:
        print(f'{model}: not usable in legacy selection (historical={len(hist)}, ssp370={len(ssp)}, hist-nat={len(hn)})')
        return None
    af = load_annual([[h, ssp[i % len(ssp)]] for i, h in enumerate(hist)], 'tas', OBS_START_YEAR, LATEST_YEAR)
    nat = load_annual([[p] for p in hn], 'tas', OBS_START_YEAR, LATEST_YEAR)
    ctl = load_annual([[p] for p in pi], 'tas', -(10**6), 10**6)
    print(f'{model}: af {dict(af.sizes)}, hn {dict(nat.sizes)}, pi {dict(ctl.sizes)}')
    return af, nat, ctl


def check_model(model: str, obs_std: np.ndarray, years: range) -> None:
    loaded = load_model(model)
    if loaded is None:
        return
    af, nat, ctl = loaded
    dc = drift_corrected(ctl.values)
    std_corr = obs_std / smoothed_std(ctl.values)
    seeds = legacy_seeds()
    worst = {'trend_af': 0.0, 'trend_hn': 0.0, 'resampled_trend_af': 0.0, 'resampled_trend_hn': 0.0}
    for year in years:
        print(f' {year}')
        t_af, t_hn = model_trends(af, START_YEAR, year), model_trends(nat, START_YEAR, year)
        samples = resample_trends(dc, year - START_YEAR, seeds) * std_corr
        new = {'trend_af': t_af, 'trend_hn': t_hn, 'resampled_trend_af': samples + t_af, 'resampled_trend_hn': samples + t_hn}
        for key, arr in new.items():
            old = np.load(LEGACY / 'models/tas/resampled' / f'{key}_{model}_{year}.npy')
            worst[key] = max(worst[key], diff(key, arr, old))
    print(f'{model} worst: ' + ', '.join(f'{k}={v:.3g}' for k, v in worst.items()))


def era5_annual_5deg() -> xr.DataArray:
    """Legacy observations: unweighted annual means of ERA5 t2m, conservatively regridded to 5°."""
    annual = era5_annual_means(LEGACY / 'data/temp.nc', 't2m', month_weighted=False)
    values = conservative_regrid(annual.values, annual['lat'].values, annual['lon'].values, *GRID_5)
    return xr.DataArray(values, coords={'year': annual['year'].values, 'lat': GRID_5[0], 'lon': GRID_5[1]}, dims=('year', 'lat', 'lon'))


def check_obs(models: list[str]) -> None:
    obs = era5_annual_5deg()
    with open(LEGACY / 'observed_trends.pickle', 'rb') as f:
        old_trends = pickle.load(f)
    worst = 0.0
    for year in END_YEARS:
        new = linear_trend(obs.sel(year=slice(OBS_START_YEAR, year)).values)
        worst = max(worst, diff(f'obs trend {year}', new, old_trends[year].values))
    print(f'obs trend worst: {worst:.3g}')

    af_runs = [m[0].values for m in (load_model(model) for model in models) if m is not None]
    af_mean = np.concatenate(af_runs).mean(axis=0)
    new_std = obs_variability(obs.sel(year=slice(OBS_START_YEAR, LATEST_YEAR)).values, af_mean)
    diff('obs std (temp_obs_var.nc)', new_std, xr.open_dataarray(LEGACY / 'data/temp_obs_var.nc').values)


def main(
    model: Annotated[list[str] | None, typer.Option(help='Model(s) to check (default: all legacy models)')] = None,
    obs: Annotated[bool, typer.Option(help='Check observed trends and observed variability')] = False,
    year: Annotated[list[int] | None, typer.Option(help='End year(s) to check (default: 1990-2023)')] = None,
) -> None:
    models = model or LEGACY_FILES
    if obs:
        check_obs(models)
        return
    obs_std = np.flip(xr.open_dataarray(LEGACY / 'data/temp_obs_var.nc').values, axis=0)
    for m in models:
        check_model(m, obs_std, year or END_YEARS)


if __name__ == '__main__':
    typer.run(main)
