from pathlib import Path
from typing import Annotated

import typer


def headline(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target xlsx file for the headline tables')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Compute the headline statistics and tables."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(headline)
