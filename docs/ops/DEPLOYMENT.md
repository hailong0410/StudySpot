# StudySpot deployment and release

Each container serves the catalog, forms and live endpoints. SQLite is
embedded in the Flask process and persists on a named volume. Staging and
production are configured as different Compose projects. The Sites pilot is
a separate runtime.

```mermaid
flowchart TB
  Browser --> Caddy["Caddy / HTTPS"]
  Caddy --> Staging["Staging container"]
  Caddy --> Production["Production container"]
  Staging --> StageData["Staging SQLite volume"]
  Production --> ProdData["Production SQLite volume"]
  Monitor["External uptime monitor"] --> Caddy
```

```mermaid
flowchart TD
  PR["Pull request"] --> CI["Tests, coverage, security, container build"]
  CI --> Main["Approved merge to main"]
  Main --> Build["Publish commit image to GHCR"]
  Build --> Stage["Deploy registry digest to staging"]
  Stage --> Smoke["Health, entry, stored report"]
  Smoke -->|Pass| Evidence["Save digest and commit"]
  Smoke -->|Fail| Stop["Promotion blocked"]
  Evidence --> Approve["Verify release tag and approve"]
  Approve --> Prod["Deploy same digest to production"]
  Prod --> Release["Verify health and publish release"]
```

A transaction runs the additive schema and catalog setup when a container starts.
The staging sample space is initialized within the same transaction. Its smoke
workflow signs in at the staging web gateway, opens the catalog, submits an
observation to the sample space and reads it back in a second session. Production
verification is read-only.
