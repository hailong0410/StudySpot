# StudySpot Sprint 4 demo guide

## Run locally

On Windows, extract the complete project folder and open `run_windows.bat`.
For a manual start, install Python 3.12 and run the following in PowerShell.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-ci-lock.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/spaces/1 in two visible browser windows side by
side. Separate normal and private windows make it easy to distinguish the
reporter and viewer. A hidden browser tab pauses polling. If the room has
existing observations, use a different campus room to start at an empty state.

## Suggested recording order (5 minutes 30 seconds)

| Time | Show on screen | English narration |
|---|---|---|
| 0:00–0:35 | Explore page, then Central Library · Sixth Floor in both windows. | “StudySpot helps students compare study spaces. This build uses six real Vanderbilt study spaces. A report records what a visitor observed about crowd level and noise.” |
| 0:35–1:45 | Keep the right viewer visible. On the left, select Very busy and Loud and save. Wait for the right panel. | “I will keep this page open while a second visitor submits what they observe. The viewer checks the server every five seconds. When the report appears, the crowd, noise and timestamp change while the page stays open.” |
| 1:45–2:20 | Point to the timestamp, the recent-observations list and the update notice. Optionally use a previously seeded stale report. | “The timestamp shows when someone reported the conditions. At sixty minutes, the app marks the observation as stale. A viewer may still see an old report if nobody sends a newer one.” |
| 2:20–3:25 | Show the baseline regression failing with a second 303, then the candidate rejecting a repeat report with 429 and Retry-After. | “Before the fix, the same source could submit twice in quick succession and both writes would succeed. In the candidate, the second request is rejected during the sixty-second window. The limit and report write share one SQLite transaction, and the concurrent test confirms only one write succeeds.” |
| 3:25–4:35 | Show GitHub security red and green runs once they are available. Use actual local audit output for a rehearsal. | “Bandit checks the Python source, pip-audit checks the locked versions, and gitleaks checks the Git history. The earlier dependency versions caused pip-audit to exit with a failure. After the upgrades, both lockfile scans pass. Coverage is checked separately.” |
| 4:35–5:30 | Return to the two windows and recap the measured behavior and drawbacks. | “This is a community reporting signal. It depends on people contributing accurate, recent observations. Polling adds a short delay and creates a request for each visible viewer every five seconds. A shared network address can also make two users share one report cooldown.” |

Use the merged main or a team-owned staging deployment for the graded recording.
The candidate is currently available for local rehearsal. Use a local test database for simulated observations. On the shared site, submit only what you observe at that location.

## Repeatable security demonstration

On the candidate, run these tests against temporary databases.

```powershell
.\.venv\Scripts\python.exe -m pytest -q test_security.py -k cooldown
```

The tests cover a 429 at 59 seconds, a successful write at 60 seconds, distinct
spaces and sources, and simultaneous writes. The report PDF includes the actual
baseline failure and fixed result from the local audit. Never try these tests
against another team's deployed application.
