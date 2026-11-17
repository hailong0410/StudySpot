# StudySpot Sprint 5 release plan

Group 6 | Hai Long Ha | Draft November 17, 2026

## Checkpoints (Nashville time)

| Due | Evidence |
| --- | --- |
| Nov 20, 11:59 p.m. | GitHub Projects backlog with Must-haves marked. Deployment diagram and ADR committed. Container and Compose merged through green PR CI. |
| Dec 1, 11:59 p.m. | Main push publishes a digest, staging deploys it automatically, three smoke checks pass and health is live. |
| Dec 6, 11:59 p.m. | v1.0.0-rc1 tagged and staged. Production reviewer and environment configured. Feature freeze. |
| Dec 8, 11:59 p.m. | v1.0.0 production release, real monitored rollback drill, report PDF, review video, final slides PDF, teamwork survey and live demo. Finish the drill before Dec 8. |

## Proposed product scope

Use the estimates in the Sprint 3 report as a provisional reference. Those are
retrospective estimates, and the report explicitly says approval was pending.
The listed 20 stories sum to 54 points. Final completion must use the approved
baseline and the Sprint 5 Definition of Done. Round up to 46 points for the
85 percent band if the 54-point denominator is approved. Add an approved
rebaseline if the scope or acceptance criteria change.

| Story | Points | Proposed priority | Candidate status |
| --- | ---: | --- | --- |
| US01 Browse study spaces | 2 | Must-have | Six verified rooms in the candidate. Confirm change from eight rooms. |
| US02 Case-insensitive search | 2 | Must-have | Locally verifiable. |
| US03 Empty result and reset | 1 | Must-have | Locally verifiable. |
| US04 Individual/group filter | 2 | Must-have | Locally verifiable. |
| US05 Outlet filter | 1 | Should-have | Sample data only. Real outlet data needs verification. |
| US06 Quiet-space filter | 1 | Must-have | Locally verifiable. |
| US07 Combined filters | 2 | Must-have | Locally verifiable. |
| US08 Space details | 2 | Must-have | Locally verifiable. |
| US09 Save crowd/noise report | 3 | Must-have | Locally verifiable, anonymous reporting. |
| US10 Latest report and age | 3 | Must-have | Locally verifiable on detail and search cards. |
| US11 Five-report history | 2 | Must-have | Locally verifiable in Flask. |
| US12 Verified campus data | 3 | Must-have | Six entries in the catalog. |
| US13 Real map links | 1 | Must-have | Directions on each official space page. |
| US14 Registration | 5 | Scope decision | Separate PR #5. Candidate includes anonymous access. |
| US15 Login/logout | 5 | Scope decision | Separate PR #5. Staging gateway access is separate from app login. |
| US16 Favorites | 3 | Optional | Planned. |
| US17 Location admin | 5 | Optional | Planned. |
| US18 Report moderation | 3 | Scope decision | Planned. |
| US19 Abuse/rate limiting | 3 | Must-have | Network + room cooldown exists. Confirm acceptance for shared Wi-Fi and the retention requirement in issue #6. |
| US20 Online deployment | 5 | Must-have | Pilot exists. Staging and production container acceptance pending. |

Priorities are recommendations for the release planning meeting. Ask the
instructor about the approved baseline, the six-space acceptance change,
disposition of US14/15 and US18, any accepted replacement for teammate review,
and an independent production approver for a solo group. Vanderbilt SSO has
no existing configuration in this branch. If confirmed as required, record it
as a separate acceptance requirement. Do not count an anonymous flow as an
account story.

## Sprint work and evidence to collect

| Work | Initial estimate (proposed) | Actual time | Evidence |
| --- | ---: | --- | --- |
| Container, local Compose and PR build | 4 h | Student to record | Container job logs and run link |
| Hosting approval, staging configuration and smoke tests | 6 h | Student to record | Staging URL, deploy IDs, pass and controlled fail |
| Production gate and release | 4 h | Student to record | Approval, release tag and matching digest |
| Monitor, backup and rollback drill | 4 h | Student to record | Alert and detection/recovery timestamps |
| Backlog reconciliation, report, slides and recording | 6 h | Student to record | Story point calculation, PDFs, MP4 and contribution links |

## Submission

Submit the Sprint 5 report PDF with 5–7 body pages, excluding cover and
appendices, in 11–12 point Arial or Cambria and spacing at most 1.2. Include a
brief retrospective and the prompt log. Submit slides as `final-group6.pdf`.
Use `sprint5-group6-video.mp4` or a text file with the unlisted link. The video
instructions say 5–6 minutes while the grading section says 4–5 minutes. Aim
for 5:00. Complete the Brightspace teamwork survey individually.

Video timing: 0:00–1:05 PR and main pipeline; 1:05–1:55 staging digest and smoke;
1:55–2:40 approval and production; 2:40–3:45 alert and rollback; 3:45–5:00 feature
tour. Prepare a screenshot for each release event and save run links. Refer to
the actual pipeline and use the production URL for the class demo.

## Local verification

103 Python tests passed with 95.50% combined statement and branch coverage.
Branch coverage was 89.19% overall, 86.67% in app.py, and 100% in domain.py.
Ruff and mypy passed. Four hosted Worker tests passed using an isolated local
fixture. Three HTTP smoke checks also passed against a local HTTPS staging
fixture with gateway authentication. Public deployments, monitor and rollback
evidence remain pending.

Radon cyclomatic complexity across the application and release scripts:

| Function | Score |
| --- | ---: |
| app.create_app | 25 |
| scripts/smoke.py check | 16 |
| scripts/build_artifact.py build | 9 |
| domain.build_space_query | 6 |
| domain.report_view | 5 |
