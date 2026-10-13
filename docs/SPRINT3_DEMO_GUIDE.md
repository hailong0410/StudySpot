# StudySpot Sprint 3 demo preparation

This is a recording and live-demo guide, not a completed video. Do not show a local branch as main or claim a GitHub run that has not happened.

## Before recording

Publish the prepared code through a PR. Enable protection on main with required PRs, one independent approving review, required CI and enforcement for administrators. Confirm the actual Actions check name before selecting it. A solo author cannot approve their own PR; ask the instructor for an approved reviewer or a documented exception. Do not waive the rule silently.

After approval, merge through GitHub, wait for the green main checks and versioned artifact, then tag that exact passing main commit as sprint3. Save screenshots of the green main run, red/fixed PR checks and protection settings. Record actual time spent and restore the original story-point baseline before claiming an effort completion percentage.

## Eight minute live presentation

No PowerPoint or UI slides. Use the running app, repository, Actions page and test evidence directly.

- 0:00–0:40: goal and scope. “StudySpot helps students find a study space and check recent crowd and noise reports. This demonstration uses sample locations. I will show the app, tests and delivery workflow.”
- 0:40–2:20: browse, case-insensitive search, group plus outlets filters, and space details. Explain which stories these actions cover.
- 2:20–3:30: submit a valid report. Show the success message, crowd/noise labels, UTC time and latest history.
- 3:30–4:30: reload or restart the app and show persistence. Explain the real SQLite database seam and stale threshold.
- 4:30–6:15: show actual PR checks, a blocked red run and its fix, then a green main run. Explain install, lint, types, unit, integration and coverage in order. Show the automatically published runnable ZIP.
- 6:15–7:00: show unit/integration counts and branch coverage. Explain “Unit tests check pure rules; integration tests send real Flask requests and inspect a temporary SQLite database.”
- 7:00–8:00: discuss limits and questions. Accounts, maps, favorites and verified campus data are not in this build. Give only the measured weighted progress from the approved backlog. State the AI support accurately.

## Four to five minute sprint review video

Suggested target: 4 minutes 40 seconds. File name: sprint3-group6-video.mp4.

- 0:00–0:20: group, project and actual main/tag version.
- 0:20–1:50: search/filter/detail/report and saved update.
- 1:50–3:00: actual blocked PR run, failure message, corrected commit and green check.
- 3:00–4:00: green main delivery job, versioned artifact, download/extract/run proof.
- 4:00–4:40: integration seam, coverage, completed stories and remaining work.

Record the real browser/app. Speak over the real actions; do not use fabricated CI screenshots. If a staged failure is used, label it clearly as a pipeline verification exercise.

## Red-to-green PR exercise

Prefer a real failure. If every real change passes and the instructor accepts a staged check, use a separate branch with one clearly documented intentional failing test. The red run must actually execute on GitHub. Fix the test in a later commit on the same PR and retain both runs. Never merge the failing commit or report a local failure as a blocked GitHub PR. This exercise is not yet performed.

## Individual teamwork assessment

Use the actual Brightspace survey questions and answer individually. The team has one member, Hai Long Ha. Do not invent a teammate or peer review. Report your actual effort and distinguish implementation assistance, automated checks and document preparation. Required file name: sprint3-Ha.pdf. The survey itself has not been provided, so no completed assessment is claimed.

## Student information still needed

Original estimates/story points, actual time records, and the permitted independent-review arrangement for the solo project. Add the contact email required by the course.
