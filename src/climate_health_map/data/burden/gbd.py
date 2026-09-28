from pathlib import Path
from typing import Annotated

import typer


def load_gbd(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target file for the tidied GBD mortality table')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Load and tidy GBD mortality with its cause and location hierarchy."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(load_gbd)
