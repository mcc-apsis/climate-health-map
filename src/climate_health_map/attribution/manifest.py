"""Build the CMIP6 input manifest from the provenance attributes of CMIP6-ng files.

Depends only on netCDF4 and the standard library, so it also runs standalone on machines without this package:
    uv run --with netCDF4 --with typer python manifest.py --source <models dir> --target manifest.csv
"""

import csv
import logging
from pathlib import Path
from typing import Annotated

import typer

FIELDS = [
    'variable',
    'model',
    'experiment',
    'member',
    'ng_file',
    'esgf_file',
    'sha256',
    'esgf_path',
    'tracking_id',
    'file_qf',
    'fixes',
    'unfixed_issues',
    'ng_git',
]


def parse_cmip6ng(attr: str) -> dict[str, str]:
    """Parse the newline-separated `key = value` pairs of the `cmip6-ng` global attribute."""
    out = {}
    for line in attr.splitlines():
        key, sep, value = line.partition(' = ')
        if sep:
            out[key.strip()] = value.strip()
    return out


def scan_file(path: Path) -> list[dict[str, str]]:
    """Return one manifest row per original ESGF file a CMIP6-ng file was built from."""
    import netCDF4

    # CMIP6-ng name pattern: <variable>_<tres>_<model>_<experiment>_<member>_<grid>.nc
    variable, _, model, experiment, member, _ = path.stem.split('_')
    with netCDF4.Dataset(path) as ds:
        attrs = {k: str(ds.getncattr(k)) for k in ds.ncattrs()}
        file_qf = str(int(ds.variables['file_qf'][...])) if 'file_qf' in ds.variables else ''
    ng = parse_cmip6ng(attrs.get('cmip6-ng', ''))
    names = [n.strip() for n in attrs.get('original_file_names', '').split(',') if n.strip()]
    hashes = [h.strip() for h in attrs.get('original_file_hash_codes', '').split(',') if h.strip()]
    base = {
        'variable': variable,
        'model': model,
        'experiment': experiment,
        'member': member,
        'ng_file': path.name,
        'tracking_id': attrs.get('tracking_id', ''),
        'file_qf': file_qf,
        'fixes': ng.get('fixes', ''),
        'unfixed_issues': ng.get('unfixed_issues', ''),
        'ng_git': ng.get('git', ''),
    }
    if not names:
        return [base | {'esgf_file': '', 'sha256': '', 'esgf_path': ''}]
    return [base | {'esgf_file': Path(name).name, 'sha256': sha, 'esgf_path': name} for name, sha in zip(names, hashes, strict=True)]


def manifest(
    source: Annotated[Path, typer.Option(help='Directory containing <variable>/<model>/g025/*.nc CMIP6-ng files')],
    target: Annotated[Path, typer.Option(help='Target manifest CSV')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Write one row per original ESGF file (name, SHA256, CMIP6-ng fixes) behind each CMIP6-ng file."""
    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', level=loglevel)
    logger = logging.getLogger('attribution.manifest')

    files = sorted(source.glob('*/*/g025/*.nc'))
    logger.info('Scanning %d CMIP6-ng files under %s', len(files), source)
    rows = []
    for path in files:
        file_rows = scan_file(path)
        if not file_rows[0]['sha256']:
            logger.warning('No provenance attributes in %s', path)
        rows.extend(file_rows)

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info('Wrote %d rows to %s', len(rows), target)


if __name__ == '__main__':
    typer.run(manifest)
