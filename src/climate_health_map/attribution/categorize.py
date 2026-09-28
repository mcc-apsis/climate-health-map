from pathlib import Path
from typing import Annotated

import typer


def categorize(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    variable: Annotated[str, typer.Option(help='Climate variable to categorize (tas or pr)')] = 'tas',
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Assign per-cell attribution categories from resampled trend distributions."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(categorize)
