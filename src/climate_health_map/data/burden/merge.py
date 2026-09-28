from pathlib import Path
from typing import Annotated

import typer


def merge(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target feather file for the merged studies database')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Assemble the spatially-resolved health-impact literature database."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(merge)
