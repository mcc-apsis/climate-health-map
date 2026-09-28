from pathlib import Path
from typing import Annotated

import typer


def export_grid(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target CSV file')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Export the per-(grid-cell, year) attribution grid as a flat CSV."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(export_grid)
