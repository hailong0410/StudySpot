# ADR 0001 - Host the StudySpot release containers on Linux

Status: proposed. Review at the Sprint 5 release-plan checkpoint.

## Context and choice

The release must support two URLs, separate data, automated staging and
promotion of the exact image checked in staging. The team currently has a
Flask/SQLite app and a separate Worker/D1 pilot. The pilot has its own
deployment path and dataset.

Use a Linux VM available through a school lab allocation or approved student
credits, with Docker Compose and Caddy. GHCR stores each commit image.
Run one app container per environment and use different Compose projects,
loopback bindings, TLS domains, SSH keys, signing keys and SQLite volumes.
Prefer separate VMs when available. A shared VM lowers cost and gives both
environments a common host-level failure domain. SQLite matches the existing
transaction logic and single-instance deployment. Production stays on one app
instance and needs SQLite backups and tested restores.

## Alternatives and cost

| Option | Consequence |
| --- | --- |
| Linux VM, chosen | Exact digest deploys and persistent SQLite. VM, disk, backups and DNS costs depend on the provider and school allocation. Aim for zero out-of-pocket cost using school credits. Provisioning, TLS and host maintenance are the team's responsibility. |
| Managed container host and Postgres | Less VM maintenance. Porting SQLite queries and migrations would add work before feature freeze. Confirm persistent-storage, region, cost and any idle sleep for the chosen plan. |
| Existing Worker/D1 pilot | Reuses the preview link and shared observations. Would need an equivalent promotion gate and a documented split between the Worker and Flask containers. The pilot stays a separate implementation and database. |

Choose a U.S. region with an accessible school account. Actual provider, city,
capacity limits and monthly cost remain pending. Keep both TLS endpoints warm
before class, and monitor disk space on the host. Keep test observations in
staging only. The app stores anonymous observations and short-lived cooldown
keys.

GitHub Environments hold deployment credentials. Configure an independent
required reviewer and prevent self-review for production. Group 6 needs an
instructor-approved reviewer or an explicitly approved equivalent. See
[GitHub deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
