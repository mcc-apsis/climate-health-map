# Data retrieval

The pipeline data lives in the shared group drive and is synced into the repo's (git-ignored)
top-level `data/` with `rsync` over `ssh ts01`:

    ts01:/data/rd5/ecs/Data/LancetCountdown/LivingPipeline/data

`config/default.env` sets `NACSOS_DATA_ROOT=data`, available in code as `Settings.DATA_ROOT`.

## Sync

```bash
scripts/sync_data.sh pull [SUBPATH]   # remote -> local (default)
scripts/sync_data.sh push [SUBPATH]   # local  -> remote
DRY_RUN=1 scripts/sync_data.sh pull   # preview without transferring
```

The full tree is ~28G, most of it model/training artifacts (`trained/`, `offline_models/`,
`models/`, `logs/`). Pass a `SUBPATH` to fetch only what you need, e.g.:

```bash
scripts/sync_data.sh pull exports/
scripts/sync_data.sh pull shapes_2026/
```

Endpoints can be overridden with the `REMOTE` / `LOCAL` environment variables.
