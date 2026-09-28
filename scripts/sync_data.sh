#!/usr/bin/env bash
# Sync the LivingPipeline data tree between ts01 and the repo's (git-ignored) data/.
#
# Usage:
#   scripts/sync_data.sh pull [SUBPATH]   # remote -> local (default)
#   scripts/sync_data.sh push [SUBPATH]   # local  -> remote
# Preview without transferring:
#   DRY_RUN=1 scripts/sync_data.sh pull
# A SUBPATH (e.g. exports/) limits the sync to that part of the tree.
# Override the endpoints:
#   REMOTE=ts01:/some/path/ LOCAL=/some/data/ scripts/sync_data.sh pull
set -euo pipefail

REMOTE="${REMOTE:-ts01:/data/rd5/ecs/Data/LancetCountdown/LivingPipeline/data/}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL="${LOCAL:-${REPO_ROOT}/data/}"

RSYNC_OPTS=(-avh --partial --info=progress2)
[[ "${DRY_RUN:-0}" == "1" ]] && RSYNC_OPTS+=(--dry-run)

direction="${1:-pull}"
subpath="${2:-}"

case "${direction}" in
    pull) src="${REMOTE}${subpath}"; dst="${LOCAL}${subpath}" ;;
    push) src="${LOCAL}${subpath}";  dst="${REMOTE}${subpath}" ;;
    *) echo "usage: $0 {pull|push} [subpath]" >&2; exit 2 ;;
esac

echo ">> ${direction}: ${src} -> ${dst}"
[[ "${direction}" == "pull" && "${DRY_RUN:-0}" != "1" ]] && mkdir -p "${dst}"
rsync "${RSYNC_OPTS[@]}" "${src}" "${dst}"
