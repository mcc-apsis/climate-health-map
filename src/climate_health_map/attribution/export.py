from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from climate_health_map.attribution.categorize import read_arrays
from climate_health_map.attribution.provenance import (
    StaleOutputError,
    categories_path,
    check_provenance,
    clear_provenance,
    grid_csv,
    used_settings,
    write_provenance,
)
from climate_health_map.shared import get_logger, load_settings

VARIABLES = {'tas': 'temp_cat', 'pr': 'precip_cat'}


def long_frame(cats, end_year, lat, lon, column: str) -> pd.DataFrame:
    """Melt a (end_year, lat, lon) category array to a flat frame with the category in `column`."""
    index = pd.MultiIndex.from_product([end_year.astype(int), lat, lon], names=['end_year', 'LAT', 'LON'])
    return pd.Series(cats.ravel(), index=index, name=column).astype('Int8').reset_index()


def export_grid(
    target: Annotated[Path | None, typer.Option(help='Target CSV file (default: attribution/grid.csv under the data root)')] = None,
    config: Annotated[Path | None, typer.Option(help='Path to config file (default: $CH_CONFIG or config/default.env)')] = None,
    loglevel: Annotated[str, typer.Option(help='Loglevel')] = 'INFO',
) -> None:
    """Export the per-(grid-cell, year) attribution grid as a flat CSV."""
    logger = get_logger('attribution.export', loglevel=loglevel)
    settings = load_settings(config)
    target = target or grid_csv(settings)
    grid = settings.ATTRIBUTION.grid
    used = used_settings(settings)

    frames = {}
    upstream = {}
    for variable, column in VARIABLES.items():
        source = categories_path(settings, variable)
        try:
            upstream[variable] = check_provenance(source, used, f'healthmap attribution categorize --variable {variable}')
        except StaleOutputError as e:
            raise typer.BadParameter(str(e)) from e
        arrays = read_arrays(source, ['category', 'end_year', 'lat', 'lon'])
        arrays['lon'] = (arrays['lon'] + 180) % 360 - 180  # the category files carry 0-360 longitudes, the studies -180-180
        if frames:
            same = all((arrays[k] == frames['coords'][k]).all() for k in ('end_year', 'lat', 'lon'))
            if not same:
                raise typer.BadParameter(f'{source} has a different grid or end years than the other variable')
        else:
            frames['coords'] = arrays
        frames[column] = long_frame(arrays['category'], arrays['end_year'], arrays['lat'], arrays['lon'], column)
        logger.info('Read %d cell-years of %s categories from %s', len(frames[column]), variable, source)

    df = frames['temp_cat'].merge(frames['precip_cat'], on=['end_year', 'LAT', 'LON'], how='outer')
    df = df.sort_values(['LAT', 'LON', 'end_year'])

    clear_provenance(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(target, index=False)
    write_provenance(target, '+'.join(VARIABLES), grid, used, upstream)
    logger.info('Wrote %d rows to %s', len(df), target)


if __name__ == '__main__':
    typer.run(export_grid)
