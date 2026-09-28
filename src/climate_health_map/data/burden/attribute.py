from pathlib import Path
from typing import Annotated

import typer


def attribute(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target feather file for the attributed studies')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Score each study as attributable from the attribution grid it covers."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(attribute)
