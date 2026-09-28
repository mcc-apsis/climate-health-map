from pathlib import Path
from typing import Annotated

import typer


def match_grid(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target file for the doc-to-grid matches')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Match study places to a grid and attach population and attribution categories."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(match_grid)
