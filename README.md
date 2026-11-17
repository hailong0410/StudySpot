# StudySpot

[![StudySpot CI](https://github.com/hailong0410/StudySpot/actions/workflows/ci.yml/badge.svg)](https://github.com/hailong0410/StudySpot/actions/workflows/ci.yml)


StudySpot is a student-built app for finding real Vanderbilt study spaces. The
catalog links to official library hours and room information, with directions to
each building. The crowd and noise panel shows observations submitted by
visitors and starts empty for every space.

## Start with Docker Compose

From a checkout of this branch:

```bash
cp .env.example .env
docker compose up --build
```

Open http://127.0.0.1:5000. On PowerShell use
`Copy-Item .env.example .env` for the first command. SQLite runs inside the app
and keeps your reports in the Compose volume. `docker compose down` stops the
app and retains that volume.

## Start on Windows

1. Install Python 3.10 or newer if it is not already installed.
2. Extract this folder from the ZIP. Do not run files inside the ZIP preview.
3. Double-click `run_windows.bat` and leave its window open.
4. Open **http://127.0.0.1:5000** in your browser.
5. Press Ctrl+C in the terminal to stop the app.

The first launch needs internet access to install Flask. After that the app has no
CDN, map API, web font, or other external runtime dependency.

Manual Windows commands (PowerShell; activation is not required):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## What works now

- Browse six study spaces listed by Vanderbilt Libraries.
- Search by name, case insensitive, with a clear empty result.
- Filter individual/group use and designated quiet spaces. Filters combine.
- Read location details.
- Submit an anonymous crowd/noise observation and save it to SQLite.
- View the latest observation, its Nashville timestamp (CST or CDT), and up to five recent reports.
- Refresh the latest crowd and noise report on each search card and on the space-detail page every five seconds in a visible tab.
- Mark cards with no reports as unknown and reports at least 60 minutes old as potentially outdated.
- See a warning for reports at least 60 minutes old, or a connection notice when updates cannot load.
- Limit anonymous repeat reports from the same direct network address for the same space for 60 seconds.
  The stored limiter key is a short-lived HMAC, and the check and report write share a SQLite transaction.
- Basic server validation, parameterized SQL, escaped HTML, and CSRF form tokens.

The Flask app accepts anonymous observations and links to the official hours and directions. Anonymous reporting is an explicit temporary scope
choice. The cooldown limits repeated submissions from one address. People sharing an address
share a cooldown, and different addresses can bypass this control. Deployments behind a reverse
proxy need a trusted peer-address configuration or an account-based limiter before sharing the app.
Community observations are unverified and may differ from current conditions.

## Data and reset

The app creates `instance/studyspot-campus.sqlite3` and a local random session key on first
launch. Older fictional-space data stays in `instance/studyspot.sqlite3`. On POSIX, the app restricts the instance folder and local signing key to the running user.
On Windows, place the project inside the user profile and use private inherited ACLs on the instance folder.
Use `STUDYSPOT_SECRET` for an externally managed signing key. Existing session keys are reused.
Reports persist after restarting. The campus catalog never imports older sample reports.
Tests use their own temporary databases.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

On macOS/Linux replace the executable with `.venv/bin/python`.
Checks run against temporary databases, not your demonstration data.

## Main files

`app.py`: app factory, routes, SQLite queries, report validation and timestamp logic.
`schema.sql`: the two current database tables and report lookup index.
`templates/`: server-rendered Jinja pages. `static/style.css`: local responsive CSS.
`test_app.py`: acceptance and robustness tests. No ORM or Bootstrap dependency is used
in this snapshot, although earlier proposals listed them as possible choices.

## Course submission

Group 6 individual project: Hai Long Ha.

Sprint 2 slides and the architecture report are submitted as PDFs on Brightspace.
The individual teamwork assessment is submitted separately. The architecture report
contains the AI usage log, including assistance with implementation, checks, and
document drafts.

## Sprint 3 checks and delivery

Install pinned CI dependencies with `python -m pip install -r requirements-ci-lock.txt`. Run `python -m ruff check .`, `python -m mypy app.py domain.py --ignore-missing-imports --check-untyped-defs`, then `python -m pytest -q --cov=app --cov=domain --cov-branch --cov-report=json:coverage.json --cov-fail-under=70`.

Unit and integration cases have separate markers. `domain.py` contains pure search, validation and report-age rules; Flask routes retain request/session/database operations.

GitHub Actions checks PRs targeting main and pushes to main. After a successful push to main, a separate delivery job builds and publishes `StudySpot-<commit SHA>.zip` as a versioned runnable Actions artifact. The ZIP contains the application, templates, static assets, schema and pinned runtime dependencies, with no databases or session keys.

To run a downloaded artifact, extract it, install `requirements-runtime-lock.txt`, and run `python app.py`. It needs Python 3.12 for the pinned Sprint 3 build. The ZIP is separate from the container release pipeline.

The Sprint 4 candidate adds parallel Bandit, pip-audit and gitleaks checks. See
[the local security audit](docs/security/sprint4-audit.md) and
[the demo guide](docs/SPRINT4_DEMO_GUIDE.md).

## Shared web deployment

The hosted pilot uses the same catalog and study-space UI with a shared D1
database. See [hosting/README.md](hosting/README.md) for deployment architecture
and isolated verification commands. The web and local databases are separate.

## Sprint 5 release

The container staging and production URLs will be added here after provisioning.
The public candidate flow uses no StudySpot account. Staging has a separate
smoke-test credential stored in GitHub Environments. See
[deployment architecture](docs/ops/DEPLOYMENT.md),
[hosting decision](docs/adr/0001-sprint5-hosting.md) and
[runbook](docs/ops/RUNBOOK.md).

## Quick guide and future work

Search for a library, optionally filter for quiet spaces, and open a result.
Choose Official hours or Directions before visiting. If you are at the space,
choose its current crowd and noise levels and save the observation. The latest
reported status refreshes on the space and search pages.

Future work includes account-aware reporting, moderation and verifying outlet
availability per campus space. See the [release plan](docs/SPRINT5_PLAN.md).
