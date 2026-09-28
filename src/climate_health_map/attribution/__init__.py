import typer

from .download import download_climate_data
from .trends import trends
from .categorize import categorize
from .export import export_grid

app = typer.Typer()
app.command('download', help='Download ERA5 + CMIP6 inputs (temperature/precipitation)')(download_climate_data)
app.command('trends', help='Compute drift-corrected trends and resampled attribution distributions')(trends)
app.command('categorize', help='Assign attribution categories from resampled trend distributions')(categorize)
app.command('export-grid', help='Export the per-(cell, year) attribution grid CSV')(export_grid)

__all__ = [
    'app',
    'download_climate_data',
    'trends',
    'categorize',
    'export_grid',
]
