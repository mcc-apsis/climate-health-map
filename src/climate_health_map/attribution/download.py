from pathlib import Path
from typing import Annotated

import typer


def download_climate_data(
    config: Annotated[Path, typer.Option(help='Path to config file')],
    variable: Annotated[str, typer.Option(help='Climate variable to retrieve (tas or pr)')] = 'tas',
    latest_year: Annotated[int, typer.Option(help='Last year of ERA5 observations to retrieve')] = 2023,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Download ERA5 reanalysis and CMIP6 model output for the given variable."""
    raise NotImplementedError


if __name__ == '__main__':
    typer.run(download_climate_data)
