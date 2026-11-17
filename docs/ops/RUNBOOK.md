# StudySpot release runbook

## System and access

- Repository and CI: [StudySpot](https://github.com/hailong0410/StudySpot/actions).
- Registry: `ghcr.io/hailong0410/studyspot`, addressed by SHA-256 digest.
- Maintainer: Hai Long Ha. Production reviewer and host administrator to be confirmed.
- Staging and production URL and uptime dashboard: add once provisioned.
- Data: one private SQLite volume per environment, initialized by the app at container startup.

## Bootstrap

1. Provision approved Linux infrastructure with Docker Engine, Docker Compose
   v2, Bash and `flock`. Set up two appropriately scoped deploy accounts and
   projects. Docker access on the host is privileged. Restrict SSH keys and
   access to the deployment machines to authorized operators.
2. Under each deploy account, install `docs/ops/compose.host.yml` as
   `~/studyspot/compose.yaml`. Create its mode-600 `~/studyspot/.env` with
   unique `COMPOSE_PROJECT_NAME`, `HOST_PORT`, `STUDYSPOT_ENV` and
   `STUDYSPOT_SECRET`. Generate a unique signing secret for each environment,
   for example with `openssl rand -hex 32`. Choose different ports on a shared
   host, for example 15000 and 25000.
3. Configure HTTPS domains and reverse-proxy each to its own port. The container
   assumes exactly one trusted proxy. Caddy should set forwarding headers from
   the direct connection. Keep the backend loopback-only. Guard staging with
   HTTP Basic authentication and give the smoke check a dedicated credential.
   Production should allow the public demo and the monitor to open `/health`.
4. Make the package publicly readable if allowed, or provision read-only GHCR
   credentials on the hosts. Pin the independently verified SSH host public
   key in the corresponding environment variable.
5. Create GitHub environments `staging` and `production`. For each set
   `APP_URL`, `DEPLOY_TARGET` (an SSH user and host), `DEPLOY_KNOWN_HOSTS`
   and the secret `DEPLOY_KEY`. For staging add secrets `SMOKE_USER` and
   `SMOKE_PASSWORD` and enable the repo variable `ENABLE_STAGING=true`.
   Restrict both deployments to main. In production configure the required
   reviewer and prevent self-review before dispatching a release.
6. Configure an external uptime monitor for production `/health` and send
   alerts to the team's selected channel. Confirm the grader access plan.

## Staging and promotion

1. Check an approved PR has green checks, security and container-build jobs
   before merging. A main push publishes a GHCR image and deploys it to staging
   when enabled. Watch the CI run and record time to readiness from its timestamps.
2. After the smoke tests pass, capture the run ID, commit and staged-image
   artifact. A failed smoke test produces no staging artifact. Capture a
   deliberate staging failure using a controlled test configuration, restore it,
   and rerun the job before promotion. Never submit smoke observations to
   production. Keep staging credentials outside screenshots and logs.
3. For the release candidate, merge a PR setting `VERSION` to `1.0.0-rc1`;
   after a green staging run tag that commit `v1.0.0-rc1`. Only bug, test and
   documentation changes follow the freeze.
4. Merge the stable `VERSION` and changelog entry, then create `v1.0.0` on
   the staging-verified commit. From main dispatch **StudySpot production
   release** with the tag and the matching main CI run ID. The verification job
   requires a successful staging artifact with the same tag version and SHA.
   The reviewer checks the staging run and approves the production job.
5. Confirm production `/health` reports the new SHA and version, browse from a
   separate browser, and check the GitHub Release. Save the evidence and retain
   known-good registry digests and staging metadata.

## Rollback and incident response

- Before the drill, write down the stable release, digest and staging run ID.
  Keep the previous version and its deployment artifact available. For longer
  incidents where CI evidence expires, have the authorized infrastructure
  operator recover from the release's audited digest and host deploy records.
- For the drill, get the harmless incident design approved. For example make
  a non-critical page return 503 and configure an external secondary check
  for just that route. Demonstrate stage smoke coverage on the normal
  catalog and report paths. Record when the monitor detects the problem.
- Dispatch the production workflow from main with the previous **published**
  release tag and staging run ID and select rollback. After approval verify the
  previous SHA, version, restored page and monitor recovery. Record detection
  and recovery timestamps with timezone and calculate elapsed time.
- Read container logs using `docker compose logs --since 30m app` from the
  environment's project. Supply `STUDYSPOT_IMAGE` from `current-image` for Compose
  commands that parse the image field. Filter logs by X-Request-ID and route.
  Before a first successful deploy, use the digest logged by the Actions run.
- If schema initialization fails, inspect the host logs and stop repeated
  deploys. The baseline schema and catalog run in one transaction. For future
  migrations, establish compatibility and take a verified SQLite backup before
  rollout. Prefer a forward fix for a committed incompatible migration. Restore
  from backup only after stopping writes and accounting for new observations.
- For startup delays, compare health SHA and container readiness. On storage
  pressure check free disk and Docker log usage. On invalid credentials rotate
  only the affected staging or production secret. A failed deployment can leave
  the new container running or restarting. Check `docker compose ps` before
  following the rollback steps.
