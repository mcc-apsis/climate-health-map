from pathlib import Path
from typing import Annotated

import typer


def export_grid(
    target: Annotated[Path, typer.Option(help='Target CSV file')],
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Export the per-(grid-cell, year) attribution grid as a flat CSV."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(export_grid)
