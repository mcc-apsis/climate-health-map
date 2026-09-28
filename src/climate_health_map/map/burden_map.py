from pathlib import Path
from typing import Annotated

import typer


def burden_map(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target figure file')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Render the studies-per-1000-climate-deaths map."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(burden_map)
