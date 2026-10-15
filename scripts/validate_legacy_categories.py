"""Compare the ported attribution categories with the legacy categories in data/attribution/legacy.

Checks the branch logic against a copy of `attr_categorize` from explore.ipynb on random cells, including
percentiles near the thresholds. Then compares the categories from the legacy trend files with attribution.pickle,
first with the ported observed trends and then with the legacy observed_trends.pickle.

    uv run --extra analysis python scripts/validate_legacy_categories.py
"""

import pickle
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import norm

from climate_health_map.attribution.categorize import categorize_all, categorize_trends, read_arrays

LEGACY = Path('data/attribution/legacy')
TRENDS = Path('data/attribution/trends/tas_g5_legacy')
LEGACY_MODELS = ['MIROC6', 'IPSL-CM6A-LR', 'CanESM5', 'GFDL-ESM4', 'ACCESS-ESM1-5', 'BCC-CSM2-MR', 'NorESM2-LM']
END_YEARS = range(1990, 2024)


def legacy_category(af_quantiles: np.ndarray, hn_quantiles: np.ndarray, obs_trend: float) -> float:  # noqa: C901
    """Copy of attr_categorize in explore.ipynb; NaN where the notebook returns None."""
    sign = np.sign(obs_trend)
    loc_af, scale_af = norm.fit(af_quantiles)
    loc_hn, scale_hn = norm.fit(hn_quantiles)
    percentile_af = norm.cdf(obs_trend, loc_af, scale_af) * 100
    percentile_hn = norm.cdf(obs_trend, loc_hn, scale_hn) * 100

    if sign == 1:
        if percentile_af > 5 and percentile_af < 95:
            if percentile_hn <= 96:
                return 0
            else:
                return 2
        elif percentile_hn < 95 and percentile_hn > 5:
            return 0
        elif percentile_af <= 5 and percentile_hn >= 95:
            return 1
        elif percentile_af >= 95:
            return 3
        elif percentile_hn <= 5:
            return 0
    elif sign == -1:
        if percentile_af < 95 and percentile_af > 5:
            if percentile_hn >= 4:
                return 0
            else:
                return -2
        elif percentile_hn > 5 and percentile_hn < 95:
            return 0
        elif percentile_hn <= 5 and percentile_af >= 95:
            return -1
        elif percentile_af <= 5:
            return -3
        if percentile_hn >= 95:
            return 0
    return np.nan


def unit_check(n_cells: int = 3000) -> None:
    rng = np.random.default_rng(0)
    af_loc, af_scale = rng.normal(0.2, 0.2, n_cells), rng.uniform(0.05, 0.4, n_cells)
    hn_loc, hn_scale = rng.normal(0.0, 0.2, n_cells), rng.uniform(0.05, 0.4, n_cells)
    af = rng.normal(af_loc, af_scale, size=(350, n_cells))
    hn = rng.normal(hn_loc, hn_scale, size=(350, n_cells))

    boundary = np.array([0.04, 0.0499, 0.05, 0.0501, 0.9499, 0.95, 0.9501, 0.96])
    u = np.where(rng.uniform(size=n_cells) < 0.5, rng.choice(boundary, n_cells), rng.uniform(size=n_cells))
    obs = af.mean(axis=0) + af.std(axis=0) * norm.ppf(u)

    legacy = np.array([legacy_category(af[:, c], hn[:, c], obs[c]) for c in range(n_cells)])
    new = categorize_trends(obs[None], af[:, None, :], hn[:, None, :])[0]
    np.testing.assert_array_equal(new, legacy)
    values, counts = np.unique(legacy[~np.isnan(legacy)], return_counts=True)
    print(f'unit: {n_cells} cells match the notebook function; counts {dict(zip(values.tolist(), counts.tolist(), strict=True))}')


def pickle_check(obs_trend: np.ndarray, label: str) -> None:
    with open(LEGACY / 'data/attribution.pickle', 'rb') as f:
        legacy = pickle.load(f)
    cats = categorize_all(obs_trend, [TRENDS / f'{m}.nc' for m in LEGACY_MODELS])

    mismatched, total = 0, 0
    pairs: Counter[tuple[float, float]] = Counter()
    for i, year in enumerate(END_YEARS):
        old = np.flip(np.asarray(legacy[year]), axis=0)
        bad = ~(cats[i] == old)
        mismatched += int(bad.sum())
        total += bad.size
        pairs.update(zip(old[bad].tolist(), cats[i][bad].tolist(), strict=True))
        if bad.any():
            print(f'  {year}: {int(bad.sum())} cells differ')
    print(f'{label}: {mismatched}/{total} cells differ')
    for (old, new), k in pairs.most_common(10):
        print(f'  legacy {old:+.0f} -> new {new:+.0f}: {k}')


def legacy_observed_trends() -> np.ndarray:
    with open(LEGACY / 'observed_trends.pickle', 'rb') as f:
        old = pickle.load(f)
    return np.flip(np.stack([np.asarray(old[y].values) for y in END_YEARS]), axis=1)


def main() -> None:
    unit_check()
    pickle_check(read_arrays(TRENDS / 'obs.nc', ['trend'])['trend'], 'ported observed trends')
    pickle_check(legacy_observed_trends(), 'legacy observed trends')


if __name__ == '__main__':
    main()
