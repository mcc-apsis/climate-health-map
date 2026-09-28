from pathlib import Path
from typing import Annotated

import typer


def climate_mortality(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    target: Annotated[Path, typer.Option(help='Target file for the climate-mortality / coverage table')],
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Combine GBD mortality with Corvetto et al. attributable fractions."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(climate_mortality)
