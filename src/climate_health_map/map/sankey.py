from pathlib import Path
from typing import Annotated

import typer


def sankey(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target figure file')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Render the climate-driver to health-impact sankey."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(sankey)
