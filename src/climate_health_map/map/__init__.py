import typer

from .density import density
from .coverage import coverage
from .burden_map import burden_map
from .sankey import sankey
from .headline import headline

app = typer.Typer()
app.command('density', help='Render the study-density maps')(density)
app.command('coverage', help='Render the country/region and HDI coverage figures')(coverage)
app.command('burden-map', help='Render the 3-panel studies-per-1000-climate-deaths map')(burden_map)
app.command('sankey', help='Render the driver -> impact -> attributable sankey')(sankey)
app.command('headline', help='Compute the headline statistics and tables')(headline)

__all__ = [
    'app',
    'density',
    'coverage',
    'burden_map',
    'sankey',
    'headline',
]
