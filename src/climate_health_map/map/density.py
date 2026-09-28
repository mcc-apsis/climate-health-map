from pathlib import Path
from typing import Annotated

import typer


def density(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target figure file')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Render the study-density maps."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(density)
