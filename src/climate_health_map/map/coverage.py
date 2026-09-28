from pathlib import Path
from typing import Annotated

import typer


def coverage(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target directory for the coverage figures')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Render the country/region and HDI coverage figures."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(coverage)
