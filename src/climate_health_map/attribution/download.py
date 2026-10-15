from pathlib import Path
from typing import Annotated

import typer

from climate_health_map.shared import get_logger, load_settings

# ERA5 CDS variable names keyed by the short variable code used across the attribution pipeline.
ERA5_VARIABLES: dict[str, str] = {
    'tas': '2m_temperature',
    'pr': 'total_precipitation',
}


def download_climate_data(
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    variable: Annotated[str, typer.Option(help='Climate variable to retrieve (tas or pr)')] = 'tas',
    start_year: Annotated[int, typer.Option(help='First year of ERA5 observations to retrieve')] = 1940,
    latest_year: Annotated[int, typer.Option(help='Last year of ERA5 observations to retrieve')] = 2023,
    target: Annotated[Path | None, typer.Option(help='Target netCDF file (default: <DATA_ROOT>/attribution/era5/<variable>.nc)')] = None,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Download ERA5 monthly-mean reanalysis for the given variable from the Copernicus CDS.

    Requires CDS API credentials in ~/.cdsapirc (see https://cds.climate.copernicus.eu/api-how-to).
    """
    import cdsapi

    logger = get_logger('attribution.download', loglevel=loglevel)
    settings = load_settings(config)

    if variable not in ERA5_VARIABLES:
        raise typer.BadParameter(f'variable must be one of {sorted(ERA5_VARIABLES)}')

    if target is None:
        target = settings.DATA_ROOT / 'attribution' / 'era5' / f'{variable}.nc'
    target.parent.mkdir(parents=True, exist_ok=True)

    logger.info('Downloading ERA5 %s (%s) %d-%d to %s', variable, ERA5_VARIABLES[variable], start_year, latest_year, target)
    client = cdsapi.Client()
    client.retrieve(
        'reanalysis-era5-single-levels-monthly-means',
        {
            'format': 'netcdf',
            'product_type': 'monthly_averaged_reanalysis',
            'variable': ERA5_VARIABLES[variable],
            'year': [str(y) for y in range(start_year, latest_year + 1)],
            'month': [f'{m:02d}' for m in range(1, 13)],
            'time': '00:00',
        },
        str(target),
    )
    logger.info('Finished ERA5 download: %s', target)


if __name__ == '__main__':
    typer.run(download_climate_data)
