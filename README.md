# StudySpot Sprint 2

A small, working Flask + SQLite prototype for Hai Long Ha's individual project.
All eight locations and amenities are **fictional sample data**. No live Vanderbilt
availability, occupancy measurement, official booking, or verified campus dataset is included.

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

- Browse eight sample locations.
- Search by name, case insensitive, with a clear empty result.
- Filter individual/group use, outlets, and usual quiet atmosphere. Filters combine.
- Read location details.
- Submit an anonymous crowd/noise observation and save it to SQLite.
- View the latest observation, its UTC timestamp, and up to five recent reports.
- See a warning for reports at least 60 minutes old.
- Basic server validation, parameterized SQL, escaped HTML, and CSRF form tokens.

Accounts, favorites, administration, verified real locations, map links and public
hosting are **not implemented**. Anonymous reporting is an explicit temporary scope
choice, with spam prevention and identity planned for a later sprint.

## Data and reset

The app creates `instance/studyspot.sqlite3` and a local random session key on first
launch. Reports persist after restarting. To reset demo reports, stop the app,
delete `instance/studyspot.sqlite3`, then restart. This removes only sample data and
demo reports. Do not delete a database you need to keep.

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
