# Attribution of grid-cell temperature and precipitation trends

## Methods

The method follows the grid-cell trend assessments of Knutson et al. (2013) for temperature and Knutson and Zeng (2018) for precipitation,
as applied with CMIP6 models in Callaghan et al. (2021). 
In contrast to each of these, it uses re-analysis data from ERA5 for observed trends.

### Data

Observed near-surface air temperature is taken from the ERA5 reanalysis (Hersbach et al., 2020),
using monthly means for 1940–2023 from the Copernicus Climate Data Store.
Annual means are computed with each month weighted by its length,
and are regridded to the regular 2.5° grid of the CMIP6-ng files (72 × 144 cells) with an area-conservative scheme.

Simulated near-surface air temperature is taken from four CMIP6 experiments (Eyring et al., 2016).
These are historical simulations with all forcings (1850–2014),
their continuation under the SSP3-7.0 scenario (ssp370, from 2015),
historical simulations with natural forcings only (hist-nat, from DAMIP; Gillett et al., 2016),
and pre-industrial control simulations (piControl).
Annual means are taken from CMIP6-ng (Brunner et al., 2020) on its 2.5° grid.

Precipitation uses ERA5 total precipitation (converted from m/day to kg m⁻² s⁻¹) and the CMIP6-ng `pr` files on the same grid.
The same experiments, models, run selection and trend method are used as for temperature.
Precipitation trends are absolute (kg m⁻² s⁻¹ per century), as in Knutson and Zeng (2018),
who report absolute trends and mask cells only by observational data coverage.
ERA5 has no gaps, so no cells are masked.

### Models and runs

Each simulation run is identified by its variant label,
which combines realisation, initialisation, physics and forcing indices (for example r1i1p1f1).
Historical and ssp370 runs are paired by variant label,
so each all-forcing series continues the same run across 2014/2015.
Within a model, only one variant family (one combination of initialisation, physics and forcing indices) is used.
This is the family with the most paired runs.
Historical and hist-nat runs are restricted to that family.
The piControl runs are those from which the selected historical runs branched,
as recorded in their `parent_variant_label` metadata.

A model is used if it provides at least one paired all-forcing run, at least three hist-nat runs and a piControl run.
Seven models are used:

| Model | Paired historical + ssp370 | Historical | hist-nat | piControl |
|---|---|---|---|---|
| ACCESS-ESM1-5 | 40 | 40 | 3 | 1 |
| BCC-CSM2-MR | 1 | 3 | 3 | 1 |
| CanESM5 | 25 | 25 | 25 | 1 |
| GFDL-ESM4 | 1 | 3 | 3 | 1 |
| IPSL-CM6A-LR | 11 | 33 | 10 | 1 |
| MIROC6 | 3 | 50 | 50 | 1 |
| NorESM2-LM | 1 | 3 | 3 | 1 |

Several models have many more historical runs than ssp370 continuations.
To use all historical runs, the all-forcing ensemble mean of each model is formed in two parts.
Up to 2014 it is the mean of all historical runs of the selected family.
From 2015 it is the mean of the paired ssp370 runs,
shifted by the difference between the mean of all historical runs and the mean of the paired historical runs over 1995–2014.
The ensemble size underlying the mean therefore does not change at 2015,
and the 2015 continuation is aligned with the full historical ensemble.
The natural-only ensemble mean is the mean of the hist-nat runs.

### Trends

Linear trends are ordinary least-squares slopes, expressed per century.
They are computed for each end year Y from 1989 to 2023.
The first end year is the grid year of the earliest studies (published 1990, matched to the year before publication).
Model trends cover 1951–Y and are computed from the all-forcing and natural-only ensemble means of each model.
The hist-nat simulations end in 2020,
so natural-only trends for end years 2021–2023 cover 1951–2020.
Observed trends cover 1940–Y.

### Internal variability

Internal variability is estimated from the piControl simulations.
In each piControl run, a linear fit is subtracted from every grid cell to remove model drift,
and the drift-corrected runs of a model are averaged.
For each end year, 50 segments with the length of the model trend window (Y − 1951 + 1 years)
are drawn at random start years from the drift-corrected control,
and the linear trend of each segment is computed.

The resampled trends are scaled so that the model's variability matches the observed variability in each cell.
Observed variability is the standard deviation over time of 7-year running means of the observed annual series for 1940–2023,
after subtracting the mean of all all-forcing runs of all models.
Model variability is the same statistic computed from the piControl series.
The scaling factor is the ratio of observed to model variability.
In both statistics, the last six running means are left out.

For each model and end year, the all-forcing distribution consists of the 50 scaled control trends added to the model's all-forcing trend,
and the natural-only distribution consists of the same 50 trends added to its natural-only trend.
The distributions of all models are pooled with equal weight, giving 350 samples each.

### Attribution categories

For temperature, a normal distribution is fitted to each pooled distribution (by its sample mean and standard deviation).
For precipitation, which is not normally distributed, the distribution of each model is summarised by its percentiles (0 to 100 in steps of 1),
and the percentiles are averaged over the models.
This gives an average distribution whose percentiles are the means of the model percentiles,
following Knutson and Zeng (2018) and Callaghan et al. (2021).
The observed percentile is interpolated linearly between the averaged percentiles.
The observed trend of each cell and end year is placed on both distributions as percentiles,
p_AF for the all-forcing distribution and p_NAT for the natural-only distribution.
The sign of the all-forcing mean gives the expected direction of change.
A trend is detectable if it lies beyond the natural-only range in its own direction (p_NAT ≥ 95 for a positive trend, p_NAT ≤ 5 for a negative one).
Categories are assigned as follows, with the sign of the observed trend:

- 0: the trend is not detectable, including trends within the natural-only range and trends in the direction opposite to a natural-only range that it lies beyond.
- ±4: the trend is detectable and has the opposite sign to the all-forcing mean.
- ±3: the trend is detectable, has the sign of the all-forcing mean and is stronger than the all-forcing range (p_AF ≥ 95 for a warming trend).
- ±2: the trend is detectable, has the sign of the all-forcing mean and lies within the all-forcing range (5 < p_AF < 95).
- ±1: the trend is detectable, has the sign of the all-forcing mean and is weaker than the all-forcing range (p_AF ≤ 5 for a warming trend).

Categories ±2 and ±3 are attributable in part to human influence.
Cells with a zero observed trend, a zero all-forcing mean or missing inputs have no category.
A trend that would be ±3 must also be closer to the all-forcing mean than to the natural-only mean,
and is otherwise ±1 (Knutson and Zeng, 2018).

Category ±4 covers 5.7% (1989) and 8.7% (2023) of the precipitation area, and 1.0% (1989) and none (2023) of the temperature area (latitude-weighted).

### Paper-level attribution

Papers are deemed to show attributable climate impacts when the climate drivers causing impacts show attributable trends in the locations studied.

Locations are extracted using the geoparser mordecai, and each paper contains 0 or more locations.
For attribution, each location is resolved to a place polygon (Natural Earth admin-1, physical and marine regions; countries and unresolved admin-1 through admin-0 boundaries),
and a location with no polygon falls back to the cell containing its point.
A place that contains one of the paper's finer places is dropped, so "São Paulo, Brazil" is scored on São Paulo alone.
The paper's score is the share of its deduplicated cell weight that lies in categories ±2 or ±3
of the variable its driver classifier picked, in the grid year before publication.
`SCORING.weight` selects the weight column (population per cell from WorldPop 2026, the default, or cell area),
and a paper is `grid_attributable` when its larger share reaches `SCORING.threshold` (default 0.5, read as "the majority of the study area's people live in attributable cells").
Papers the classifier did not assign to either variable, or whose places matched no grid cell, stay unattributed with share `NA`.

### References

- Brunner, L., Hauser, M., Lorenz, R. and Beyerle, U. (2020). The ETH Zurich CMIP6 next generation archive: technical documentation. Zenodo. https://doi.org/10.5281/zenodo.3734128
- Callaghan, M. et al. (2021). Machine-learning-based evidence and attribution mapping of 100,000 climate impact studies. Nature Climate Change, 11, 966–972.
- Eyring, V. et al. (2016). Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. Geoscientific Model Development, 9, 1937–1958.
- Gillett, N. P. et al. (2016). The Detection and Attribution Model Intercomparison Project (DAMIP v1.0) contribution to CMIP6. Geoscientific Model Development, 9, 3685–3697.
- Hersbach, H. et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146, 1999–2049.
- Knutson, T. R. and Zeng, F. (2018). Model assessment of observed precipitation trends over land regions: detectable human influences and possible low bias in model trends. Journal of Climate, 31, 4617–4637.
- Knutson, T. R., Zeng, F. and Wittenberg, A. T. (2013). Multimodel assessment of regional surface temperature trends: CMIP3 and CMIP5 twentieth-century simulations. Journal of Climate, 26, 8709–8743.

## Open decisions

- Observed trends start in 1940 and model trends in 1951.
- Observed variability is computed against a mean pooled over all all-forcing runs of all models, so models are weighted by their number of runs.
- The trimming of the last six running means in the variability estimate.
- Adding CNRM-CM6-1, which meets the selection criteria (6 paired runs, 10 hist-nat runs) but is not in the model list.
- HadGEM3-GC31-LL, which has no ssp370 runs in the current inputs, pending ESGF.
- Both variables use the 2.5° grid, the only grid of the precipitation inputs. For temperature, the 2.5° attributable share (categories ±2 and ±3) is 0.5 to 3 percentage points lower than on 5° (2020: 79.2% against 80.4% globally and 86.5% against 87.5% on land), and 90–95% of cells have the same category on both grids. A return to 5° requires regridding the precipitation inputs. Retrieval of the 2.5° inputs from ESGF is open.
- ssp245 as scenario, for which `ssp245-nat` exists for only four models.
- Temperature uses the pooled distribution of Knutson et al. (2013) and Callaghan et al. (2021), and precipitation the average distribution. Both papers give this split.
- The closer-to-the-all-forcing-mean condition of Knutson and Zeng (2018) is applied, although Callaghan et al. (2021) do not state it.
  The category given to trends failing the condition (±1) is an interpretation.
- The category rules follow the text of Callaghan et al. (2021).
  Whether their published precipitation map follows the same rules is not checked.
- ERA5 precipitation variability is larger than modelled variability in most cells (median scaling factor 1.2 to 1.4, up to 20),
  whereas Callaghan et al. (2021) find models overestimating variability against GPCC.
- ERA5 covers the oceans, so precipitation categories are assigned there too, where Knutson and Zeng use land-only GPCC.

## Implementation

```bash
healthmap attribution download     # ERA5 monthly means of tas or pr (--variable)
healthmap attribution trends       # drift-corrected trends + resampling (--variable tas or pr)
healthmap attribution categorize   # per-cell attribution category (--variable tas or pr)
healthmap attribution export-grid  # per-(cell, year) attribution grid CSV
```

Decisions are recorded in this document and in `config/attribution.yaml`, which is read through `settings.ATTRIBUTION` (and `settings.SCORING` for the paper-level scoring of the exports).
The configuration holds the model list, grid (`g025`), scenario (`ssp370`), observation start year (1940),
trend start year (1951), first and last end year (1989 and 2023), minimum number of hist-nat runs (3),
number of resampled segments (50) with seed 2023, and the splice baseline (1995–2014).
The category tail (5%) is a keyword default of `assign_categories`.
`trends --variable pr` writes to `data/attribution/trends/pr_g025`,
and `categorize --variable pr` writes `data/attribution/categories/pr_g025.nc`,
whose `distribution` attribute records the distribution used.
A change to a decision updates this document in the same commit as the code that depends on it.

`trends` writes one netCDF file per model and `obs.nc` to `data/attribution/trends/<variable>_<grid>`.
Each model file records its selected variant labels in the attributes `members_af`, `members_hist`, `members_hn` and `members_pi`.
Unpaired runs and piControl parents without a file are logged.

### Provenance

The variable and grid are part of the output path (`trends/<variable>_<grid>`, `categories/<variable>_<grid>.nc`).
The other settings that shape an output are all other fields of `ATTRIBUTION` in the configuration.
`trends` writes them to `provenance.json` in its output directory,
and `categorize` writes `<variable>_<grid>.provenance.json` next to its output, with the provenance of the trend files it read.
A sidecar is removed when a run starts and written when it ends, so an interrupted run leaves none.

`categorize` checks the provenance of the trend files against the current settings and stops if it is missing or differs.
The recorded and expected models must be the same set, because the observed variability that scales the resampled trends of every model is computed from the mean over all models.
All other settings must be equal.
Other code that reads outputs derives the path with `trends_dir` or `categories_path` and calls `check_provenance` with `used_settings(settings)`,
which raises `StaleOutputError` with the command that regenerates the output.
