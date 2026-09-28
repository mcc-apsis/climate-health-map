# Disease burden (GBD)

Cross-references the spatially-resolved health-impact literature database with the Global Burden of
Disease (GBD 2021) and Corvetto et al. (2024) attributable fractions.

## Commands

```bash
healthmap burden merge              # assemble the literature database + clean places
healthmap burden match-grid         # match study places to grid, attach population + attribution
healthmap burden attribute          # score studies as attributable
healthmap burden load-gbd           # tidy GBD mortality + cause/location hierarchy
healthmap burden climate-mortality  # apply attributable fractions; climate mortality + coverage
```

## Notes

- Place-to-grid matching reuses the `data/geographies` readers (`load_grid_data`,
  `read_places_export`) rather than re-implementing the grid logic.
- The health-impact to GBD cause crosswalk is kept explicit and reviewable.
