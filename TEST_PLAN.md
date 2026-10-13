# Test Plan — StudySpot
Sprint 3 | Owner: Hai Long Ha | Date: October 13, 2026

## Baseline
Measured before the ICA10 changes on main commit 89b435675b0856054830180c092318d766f640f5.

- Tests: 12 passing, 0 failing.
- Branch coverage: 28/36 = 77.78%.
- Line coverage: 102/111 = 91.89%.
- Least-covered measured production module: app.py. It is the only Python production module.
- Existing tests use Flask routes and a real temporary SQLite database. They are integration tests, not browser E2E tests.

The coverage tool's combined line-and-branch percentage was 88.44%; that is different from branch coverage alone.

## Targets
- Course floor: at least 60% coverage and integration tests.
- Plan target: branch coverage >= 70% overall and >= 85% for app.py, the core module.
- All tests pass; invalid requests must not write reports.
- Tests use temporary databases and a fixed clock for time boundaries.
- Add focused unit tests when pure validation/time helpers become public and separate from Flask routes.

## Priorities
Likelihood and impact use a 1–3 scale. Priority = likelihood x impact. Scores are planning judgments, not measured defect counts.

| Feature | Likelihood | Impact | Priority | Unit | Integration | E2E | Owner |
|---|---:|---:|---:|---|---|---|---|
| Report input and CSRF validation | 3 | 3 | 9 | Planned | Yes | Planned | Hai Long Ha |
| Report age, latest report and stale warning | 3 | 3 | 9 | Planned | Yes | Planned | Hai Long Ha |
| Report storage and restart persistence | 2 | 3 | 6 | No | Yes | Planned | Hai Long Ha |
| Search and combined filters | 2 | 2 | 4 | Planned | Yes | Planned | Hai Long Ha |
| Space details, history limit and errors | 2 | 2 | 4 | No | Yes | Planned | Hai Long Ha |
| Startup, session key and health check | 2 | 2 | 4 | UTC helper only | Yes | No | Hai Long Ha |

Report validation ranks high because a bad request could write bad data. Report freshness ranks high because current crowd/noise information is central to the product. There are no payments in this project.

## EP and BVA
Chosen function: report_view(row), app.py:63–69, reached through GET /spaces/<id>.

- Less than one minute old, including a future timestamp: show Just now; fresh.
- One to 59 full minutes old: show minutes; fresh.
- 60 to 1439 full minutes old: show hours; stale.
- 1440 full minutes or older: show days; stale.
- Core rule from the project README: stale starts at exactly 60 minutes.
- New deterministic cases: -60, 0, 59, 60, 3540, 3599, 3600, 3660, 86340, 86400 and 86460 seconds of age.
- The clock is stubbed; the real route, database and template still run.
- Tests inspect the latest report's displayed age and fresh/stale state.

The finer age labels and future-time clamp follow the current implementation. They are recorded here as the intended rules for this plan. The current display uses '1 hours ago' and '1 days ago'; copy edits can be handled separately.

## Integration seams to test
- GET search -> filter validation -> parameterized SQLite query -> result template.
- POST report -> space lookup -> CSRF and input validation -> database write -> redirect -> detail page.
- GET detail -> latest five reports ordered by time and id -> age conversion -> fresh/stale display.
- App startup -> schema creation -> sample seed -> persistent session key -> database health check.
- Restart -> same SQLite database -> saved report still visible.

Use a real SQLite database in a temporary directory. Do not mock the application, SQL operations or functions under test. Stub the clock only when checking age boundaries. There is no external API in the current app.

## Critical E2E journeys
Planned manual browser checks, not claimed as executed in this run:
1. Open Explore -> search/filter -> open a matching space.
2. Open a space -> submit a valid crowd/noise report -> see the saved update.
3. Submit a report -> restart the app -> reopen the space -> see the same saved report.

## Not testing
- Accounts, favorites, admin, maps and live campus data: not implemented.
- External APIs: none in the current app.
- Exact CSS appearance in every browser: outside this short test plan; use a basic manual desktop/mobile check later.
- Flask or SQLite internals: test our use of them instead.
- The development server launcher: route tests do not start a real server. Browser smoke checks will cover startup later.
- None/malformed rows passed directly to nested report_view: the current route only passes saved database rows. Revisit if the helper becomes a public API.

## How to run
Install first:
```bash
python -m pip install -r requirements-dev.txt
```
Unit/non-integration tests:
```bash
python -m pytest -q -m "not integration"
```
Integration tests:
```bash
python -m pytest -q -m integration
```
Full coverage:
```bash
python -m pytest -q --cov=app --cov-branch --cov-report=term-missing --cov-report=json:coverage.json
```
Branch coverage = covered_branches / num_branches in coverage.json. Do not substitute the combined Cover column.

## ICA10 result
- Added 25 cases: 24 integration cases and 1 unit case.
- Total: 37 passing, 0 failing.
- Levels: 1 unit case, 36 integration cases; browser E2E not executed.
- Branch coverage: 34/36 = 94.44%.
- Line coverage: 109/111 = 98.20%.
- Combined line-and-branch coverage: 97.28%.
- Both branch targets are met. This does not prove the app has no bugs.
- app.py, schema.sql and templates were not changed.
- Remaining uncovered code: report_view's None/empty-row guard and the development server launcher.

## Git delivery
Changes are prepared on branch ica10-test-plan. Commit the plan, tests, marker configuration and pytest-cov dependency together. Push the branch and open a PR against main. The PR should describe the new boundaries and include the 12-to-37 test and 77.78%-to-94.44% branch results. Do not call the PR complete until it exists on GitHub.

## Project Sprint 3 preparation
The pure rules are now in domain.py and have dedicated unit tests. This refactor keeps the existing routes and user-visible pricing-free report behavior. Fixtures are shared through conftest.py.

The current local suite has 85 cases: 45 unit and 40 integration. It covers all current pure search/validation/age rules and includes a valid POST checked directly against a real temporary database. The old ICA10 figures above describe that earlier snapshot, not this refactored build.

The revised workflow installs requirements-ci-lock.txt, runs lint and type checks, then unit and integration steps, then full coverage. On a successful push to main it builds and publishes a SHA-versioned runnable Actions artifact. The CD choice is an artifact, not a live deployment.

Publishing, main protection, an independent approving review, a red-to-green PR run and the sprint3 tag are still pending. Do not treat a local pass as a green main run. Backlog progress by story points and actual time require the original records; feature count alone is not the percentage.
