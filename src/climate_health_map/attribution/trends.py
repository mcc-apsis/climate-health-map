from pathlib import Path
from typing import Annotated

import typer


def trends(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    variable: Annotated[str, typer.Option(help='Climate variable to attribute (tas or pr)')] = 'tas',
    latest_year: Annotated[int, typer.Option(help='Last year to compute trends up to')] = 2023,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Compute drift-corrected trends and resampled attribution distributions."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(trends)
