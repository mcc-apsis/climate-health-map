"""Provenance sidecars of attribution outputs: the settings an output was generated with, checked when it is read.

Variable and grid are part of the output path. The other settings that shape an output (models, scenario, observation start year)
are written to a JSON sidecar next to it, and readers compare them with the current settings.
"""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from climate_health_map.shared.config import Settings

PROVENANCE_FILE = 'provenance.json'


class StaleOutputError(RuntimeError):
    """An attribution output is missing its provenance or was generated with settings that differ from the current ones."""


def era5_path(settings: Settings, variable: str) -> Path:
    """Monthly ERA5 file of a variable."""
    return Path(settings.DATA_ROOT) / 'attribution' / 'era5' / f'{variable}.nc'


def trends_dir(settings: Settings, variable: str) -> Path:
    """Directory of the trend files of a variable on the grid of the settings."""
    return Path(settings.DATA_ROOT) / 'attribution' / 'trends' / f'{variable}_{settings.ATTRIBUTION.grid}'


def categories_path(settings: Settings, variable: str) -> Path:
    """Category file of a variable on the grid of the settings."""
    return Path(settings.DATA_ROOT) / 'attribution' / 'categories' / f'{variable}_{settings.ATTRIBUTION.grid}.nc'


def grid_csv(settings: Settings) -> Path:
    """Flat CSV of the categories of all variables and years, written by `export-grid` and read by the geographies loaders."""
    return Path(settings.DATA_ROOT) / 'attribution' / 'grid.csv'


def sidecar(path: Path) -> Path:
    """Provenance file of an output: `provenance.json` inside a directory, `<name>.provenance.json` next to a file."""
    return path / PROVENANCE_FILE if path.is_dir() or not path.suffix else path.with_suffix('.provenance.json')


def used_settings(settings: Settings, models: Sequence[str] | None = None) -> dict[str, Any]:
    """Attribution settings that shape the outputs, except the grid (in the path); `models` are those actually used where a run skipped some."""
    used: dict[str, Any] = settings.ATTRIBUTION.model_dump(exclude={'grid'})
    if models:
        used['models'] = list(models)
    return used


def clear_provenance(path: Path) -> None:
    """Remove the provenance of an output that is about to be regenerated, so that an interrupted run leaves none."""
    sidecar(path).unlink(missing_ok=True)


def write_provenance(path: Path, variable: str, grid: str, used: Mapping[str, Any], upstream: Mapping[str, Any] | None = None) -> None:
    """Write the provenance of an output: variable, grid, settings used and the provenance of the inputs."""
    record = {'variable': variable, 'grid': grid, 'settings': dict(used), 'upstream': dict(upstream) if upstream else None}
    sidecar(path).write_text(json.dumps(record, indent=2, default=str) + '\n')


def differences(recorded: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    """Descriptions of the expected settings that the recorded settings do not match.

    The models are compared as sets, because the observed variability that scales every model's resampled trends
    is computed from the mean over all models. All other settings must be equal.
    """
    out = []
    used, wanted = set(recorded.get('models', [])), set(expected['models'])
    if used != wanted:
        parts = [f'{label}: {", ".join(sorted(names))}' for label, names in (('missing', wanted - used), ('extra', used - wanted)) if names]
        out.append(f'models differ ({"; ".join(parts)})')
    out.extend(f'{key} is {recorded.get(key)!r}, expected {value!r}' for key, value in expected.items() if key != 'models' and recorded.get(key) != value)
    return out


def check_provenance(path: Path, expected: Mapping[str, Any], rerun: str) -> dict[str, Any]:
    """Return the provenance of an output after checking it against the expected settings; `rerun` is the command that regenerates it."""
    file = sidecar(path)
    if not path.exists():
        raise StaleOutputError(f'{path} does not exist; generate it with: {rerun}')
    if not file.is_file():
        raise StaleOutputError(f'{path} has no provenance file {file.name}; regenerate it with: {rerun}')
    record: dict[str, Any] = json.loads(file.read_text())
    diffs = differences(record['settings'], expected)
    if diffs:
        raise StaleOutputError(f'{path} was generated with different settings ({"; ".join(diffs)}); regenerate it with: {rerun}')
    return record
