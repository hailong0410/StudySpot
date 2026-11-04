# ICA15 Threat Model for StudySpot

**Group 6 · Hai Long Ha · November 4, 2026**

**Scope.** StudySpot main at 343aebb. The local demo binds to 127.0.0.1:5000. Flask renders HTML and stores anonymous crowd and noise observations in SQLite. The eight locations are fictional. This revision has no staging deployment, user accounts, admin routes, booking, or external runtime APIs. GitHub Actions publishes a runnable ZIP.

## 1. Data flow diagram

Dashed boxes mark trust zones. The host storage zone is on the same computer as Flask and is governed by OS file permissions.

~~~mermaid
flowchart TB
  subgraph U["Browser zone"]
    browser["Visitor browser"]
  end
  subgraph A["Application zone"]
    flask["Flask routes and Jinja templates"]
  end
  subgraph D["Host storage zone"]
    db[("SQLite file")]
    key[("Session signing key file")]
  end
  subgraph C["GitHub delivery zone"]
    actions["GitHub Actions build"]
    zip[("Runnable ZIP artifact")]
    actions -->|"Versioned runnable ZIP"| zip
  end
  browser -->|"B1: queries, filters, space ID, cookie and report form"| flask
  flask -->|"B1: HTML, cookie, redirect and CSRF token"| browser
  flask -->|"B2: parameterized reads and report writes"| db
  db -->|"B2: space and report records"| flask
  flask -->|"B2: generated key on first launch"| key
  key -->|"B2: local key at startup"| flask
  zip -.->|"B3: operator downloads, installs and runs the ZIP"| flask
  classDef boundary fill:none,stroke:#607080,stroke-width:1.5px,stroke-dasharray:5 4;
  class U,A,D,C boundary;
~~~

| Boundary | Data crossing it | Who controls each side |
|---|---|---|
| B1 Browser / Flask | Search and filter inputs, space IDs, report choices, cookie, CSRF token, HTML | Visitors control requests. Flask validates input and produces responses. |
| B2 Flask / host storage | SQL statements and values, result rows, local signing key | Flask reads and writes. The host OS controls access to the files. |
| B3 GitHub delivery / local runtime | ZIP containing source and runtime dependency list | GitHub Actions builds the ZIP. The local operator downloads and runs it. |

## 2. Assets

| Asset | Where it lives | Impact if lost or changed |
|---|---|---|
| Crowd and noise observations | SQLite status_reports and rendered pages | Medium. False reports mislead visitors about conditions. |
| Sample locations | SQLite study_spaces | Medium. Corrupt entries can break discovery or detail pages. |
| Session signing key | instance/session.key or STUDYSPOT_SECRET | Medium. A leaked key allows forgery of sessions carrying form state and flash messages. |
| Demo availability and storage | Flask process and local SQLite file | Medium. Write floods or lock contention can interrupt the demo. |
| Runnable application code | GitHub, Actions artifact and extracted ZIP | High. A modified build runs with the operator's privileges. |

## 3. STRIDE analysis

S = spoofing, T = tampering, R = repudiation, I = information disclosure, D = denial of service, E = elevation of privilege. Test references identify existing test coverage.

| ID | Boundary | STRIDE | Asset and threat | Existing control and evidence | Gap or result |
|---|---|---|---|---|---|
| T1 | B1 | S | Session state. A malicious site tries to submit a report as a visitor through the visitor's browser. | Session-bound CSRF token and SameSite=Lax. Tests reject missing and wrong tokens without a write. | Covered for missing and wrong tokens. |
| T2 | B1 | T | Reports. A visitor posts fabricated but valid values to replace the latest observation. | Server validates allowed choices and creates the timestamp. Tests reject invalid values. | F01. Repeated valid reports are accepted. |
| T3 | B1 | D | Storage. A bot submits small valid reports repeatedly to grow SQLite and compete for writes. | Tested 16 KiB request cap. Detail pages display at most five recent rows. | F01. Stored rows are unbounded. |
| T4 | B1 | R | Report history. An abusive submitter can deny sending an observation because the anonymous row carries no actor identity. | Server timestamp and report ID establish that a record exists. | F04. Add privacy-preserving abuse monitoring and retain anonymity. |
| T5 | B2 | T | Sample spaces. An attacker supplies SQL syntax in a search term to alter the query. | Bound SQL parameters. Existing tests cover literal wildcard search and escaped HTML. | Covered for the reviewed query path. |
| T6 | B2 | I | Signing key. A second local OS account reads the key if host permissions allow it. | Random key generation and instance/ exclusion from Git. | F02. File access depends on host permissions. |
| T7 | B2 | T | Report integrity. A local process with file write access changes a report directly, bypassing the Flask form checks. | SQLite field constraints and foreign keys on the app connection. | F02. File access still permits edits to valid values. |
| T8 | B2 | D | Detail page. A corrupt stored timestamp or an unavailable database causes an affected route to fail. | SQLite timeout and transaction context. Custom handlers cover 400, 404 and 413. | F05. Storage and stored-value failures need controlled handling. |
| T9 | B3 | T | Build integrity. An operator runs an altered ZIP after download. | Main-only artifact publication after checks and a source SHA in the filename. | F03. No independent ZIP verification is documented. |
| T10 | B3 | E | Local execution. A compromised upstream action inserts code that runs with the operator's permissions when the build is launched. | CI contents permission is read-only. Python dependency versions are pinned. | F03. Action references use movable tags. |

## 4. OWASP Top 10 2025 checklist

Hai Long Ha owns all categories as the sole member of Group 6. Results reflect source and test-code review within the stated scope. Category names follow the [OWASP Top 10 2025](https://top10.owasp.org/2025/).

| Category | Owner | Review and evidence | Result |
|---|---|---|---|
| A01 Broken Access Control | Hai Long Ha | Reviewed routes, public space IDs, unknown-ID 404 and report CSRF gate. | Pass for reviewed routes. No private or admin objects exist for an IDOR test. |
| A02 Security Misconfiguration | Hai Long Ha | Reviewed loopback binding, debug disabled and instance/ excluded from Git. | F02. Local file permissions need enforcement. |
| A03 Software Supply Chain Failures | Hai Long Ha | Reviewed pinned requirements and CI workflow. | F03. Actions use movable tags. |
| A04 Cryptographic Failures | Hai Long Ha | Reviewed random key generation and HttpOnly cookie setting. | F02. Key file access depends on host permissions. |
| A05 Injection | Hai Long Ha | Reviewed bound SQL, Jinja HTML rendering and escaped-output regression coverage. | Pass for reviewed inputs. |
| A06 Insecure Design | Hai Long Ha | Traced anonymous reports through the insert path. | F01. No throttling or retention. |
| A07 Authentication Failures | Hai Long Ha | Checked scope for login, passwords and privileged sessions. | N/A. The demo has no user accounts. |
| A08 Software or Data Integrity Failures | Hai Long Ha | Reviewed artifact publication and documented install flow. | F03. No independent ZIP verification is documented. |
| A09 Security Logging and Alerting Failures | Hai Long Ha | Reviewed report route and rejection handling. | F04. Add structured abuse events without logging cookies or tokens. |
| A10 Mishandling of Exceptional Conditions | Hai Long Ha | Reviewed error handlers, database connection and timestamp parsing. | F05. Add controlled handling and tests for storage failures and malformed rows. |

## 5. Top three risks and next actions

1. **F01 · Limit anonymous report abuse.** Repeated valid reports can replace the latest display and consume storage, particularly if the demo is shared. Add throttling and retention. Verify excess requests return 429 without writing, unrelated clients can still submit, and cleanup preserves the latest observation for each space. [Issue 6](https://github.com/hailong0410/StudySpot/issues/6)
2. **F02 · Restrict local access to the database and signing key.** Enforce local file restrictions and document POSIX permissions and Windows ACLs. Verify a second unprivileged account cannot read the key or alter SQLite, and confirm restart still works. [Issue 7](https://github.com/hailong0410/StudySpot/issues/7)
3. **F03 · Verify build integrity.** Pin Actions to reviewed commit SHAs and publish an authenticated ZIP digest or provenance. Verify a genuine build and reject a modified one. [Issue 8](https://github.com/hailong0410/StudySpot/issues/8)

**Other backlog.** F04 adds structured rejection and throttling events without recording cookies, tokens or unnecessary personal data. F05 covers controlled errors and regression tests for unavailable storage and malformed timestamps.

**Project evidence.** [StudySpot source snapshot](https://github.com/hailong0410/StudySpot/tree/343aebb42e919057ca6552e68872086ce08f8de7) includes app.py, domain.py, schema.sql, test_app.py, test_boundaries.py, the runtime lockfile, CI workflow and artifact build script.
