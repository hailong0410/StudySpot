#!/usr/bin/env bash
# Executed on the GitHub Actions runner. Host identity must be pinned out of band.
set -euo pipefail
umask 077
ssh_files=$(mktemp -d)
trap 'rm -rf "$ssh_files"' EXIT
printf '%s\n' "${DEPLOY_KEY:?}" > "$ssh_files/key"
printf '%s\n' "${DEPLOY_KNOWN_HOSTS:?}" > "$ssh_files/known_hosts"
if [[ ! "$1" =~ ^ghcr\.io/hailong0410/studyspot@sha256:[0-9a-f]{64}$ ]] ||
   [[ ! "${DEPLOY_TARGET:?}" =~ ^[a-z_][a-z0-9_-]*@[A-Za-z0-9.-]+$ ]]; then
    echo "Invalid registry digest or SSH target." >&2
    exit 1
fi
ssh -F /dev/null -i "$ssh_files/key" -o IdentitiesOnly=yes -o BatchMode=yes \
    -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$ssh_files/known_hosts" \
    "$DEPLOY_TARGET" bash -s -- "$1" < scripts/deploy.sh
