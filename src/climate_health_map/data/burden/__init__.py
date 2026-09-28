import typer

from .merge import merge
from .matching import match_grid
from .attribute import attribute
from .gbd import load_gbd
from .corvetto import climate_mortality

app = typer.Typer()
app.command('merge', help='Assemble the spatially-resolved health-impact literature database')(merge)
app.command('match-grid', help='Match study places to a grid and attach population + D&A categories')(match_grid)
app.command('attribute', help='Score studies as attributable from the detection/attribution grid')(attribute)
app.command('load-gbd', help='Load and tidy GBD 2021 mortality with cause/location hierarchy')(load_gbd)
app.command('climate-mortality', help='Combine GBD mortality with Corvetto attributable fractions')(climate_mortality)

__all__ = [
    'app',
    'merge',
    'match_grid',
    'attribute',
    'load_gbd',
    'climate_mortality',
]
