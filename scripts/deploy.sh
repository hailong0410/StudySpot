#!/usr/bin/env bash
# Executed on the deployment host under the selected environment's SSH account.
set -euo pipefail
image=${1:?Supply a GHCR digest}
if [[ ! "$image" =~ ^ghcr\.io/hailong0410/studyspot@sha256:[0-9a-f]{64}$ ]]; then
    echo "Invalid image reference." >&2
    exit 1
fi
cd "$HOME/studyspot"
exec 9> deploy.lock
flock -x 9
if [ -s current-image ]; then
    previous=$(<current-image)
fi
export STUDYSPOT_IMAGE="$image"
docker compose pull
docker compose up -d --wait --wait-timeout 90
if [ "${previous:-}" != "$image" ] && [ -n "${previous:-}" ]; then
    printf '%s\n' "$previous" > previous-image
fi
printf '%s\n' "$image" > current-image.tmp
mv current-image.tmp current-image
