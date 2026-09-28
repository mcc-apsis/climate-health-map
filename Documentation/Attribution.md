# Attribution (climate trends)

Grid-cell human-attributable change in climate drivers (temperature and precipitation).

## Commands

```bash
healthmap attribution download     # ERA5 + CMIP6 (g5) inputs for tas and pr
healthmap attribution trends       # drift-corrected trends + resampling
healthmap attribution categorize   # per-cell attribution category
healthmap attribution export-grid  # per-(cell, year) attribution grid CSV
```

## xesmf / ESMF

Regridding uses `xesmf`, which depends on the ESMF C library (`esmpy`). This does not install cleanly
via pip/uv on all machines, so it is kept out of the `analysis` extra; install it via conda-forge:

```bash
conda install -c conda-forge esmpy xesmf
```

Let `esmpy` discover ESMF at runtime rather than setting `ESMFMKFILE` by hand.

## Precipitation

The precipitation pipeline reuses the temperature one over the `pr` variable. Categorization fits
normal distributions to trend samples; precipitation trends are typically non-normal and need a
distribution-appropriate treatment.
