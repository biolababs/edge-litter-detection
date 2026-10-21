# Security review

Review date: 2026-10-21

## Scope

This review covers the tracked Python application, launcher, dashboard,
container and Compose files, GitHub Actions, download helpers, SQLite storage,
and public-model loading path. It is a secure-development review, not a
penetration test, safety certification, or claim of formal compliance.

The control set was organized against:

- OWASP Application Security Verification Standard concepts for validation,
  secure configuration, files, APIs, and communications;
- NIST Secure Software Development Framework practices for protecting source,
  producing well-secured releases, and responding to vulnerabilities; and
- OpenSSF supply-chain practices for pinned automation, dependency updates,
  vulnerability scanning, and project security policy.

## Implemented controls

| Area | Control |
|---|---|
| Network exposure | API loopback default; Compose host port bound to `127.0.0.1`; wildcard binds rejected outside an explicit container boundary |
| Authentication boundary | No public exposure supported; remote use requires an authenticated gateway or SSH tunnel |
| Input validation | Pydantic constraints; bounded image bytes and pixels; JPEG/PNG/WebP signatures; bounded stream counts |
| Browser hardening | CSP, frame denial, no-sniff, no-referrer, restrictive permissions, no-index, and no-store API responses |
| Model supply chain | Immutable Hugging Face revisions, SafeTensors, remote code disabled, SHA-pinned custom remote reference requirement |
| Download integrity | HTTPS validation, redirect validation, size limits, media signatures, temporary files, and SHA-256 |
| Data storage | Parameterized SQL, foreign keys, constrained statuses, SQLite account permissions, and atomic JSON output |
| Least privilege | Non-root container user and read-only GitHub workflow permissions except CodeQL result upload |
| CI supply chain | GitHub Actions pinned to full commits; Ruff, Bandit, CodeQL, dependency review, and Dependabot |
| Secrets | Repository/history pattern scan; ignored runtime credentials and data; private vulnerability process |
| Machinery safety | Perception output remains advisory; collection confirmation is separate from observation |

## Verification completed

- full dependency-light unit suite;
- real OmDet-Turbo image inference through `startup.sh`;
- Ruff correctness scan;
- Bandit medium-and-higher scan;
- Python dependency vulnerability audit;
- package build, bytecode compilation, release-scaffold validation, shell
  syntax check, and launcher regression test;
- tracked-file and credential-pattern review; and
- repository-wide wildcard-bind review.

## Residual risks and required deployment controls

1. The API does not implement identities or authorization. Keep it private or
   place it behind a mature authenticated gateway.
2. A trusted stream operator can ask the server to open an HTTP or RTSP source.
   Treat stream creation as an administrative permission and restrict outbound
   network access in managed deployments.
3. Some JetPack environments remain on Python 3.10 and cannot install Pillow
   13. Keep those deployments private, retain upload limits, and move to a
   validated Python 3.11 vendor stack when available.
4. Public open-vocabulary detections can be wrong or biased by scene and prompt.
   Use representative accuracy evaluation and human review.
5. The software is not a safety-rated motion controller and cannot authorize
   machinery movement.
6. Jetson Orin 8 GB completed a constrained coexistence validation and a
   3,622-frame stability run, but the community container base still requires
   production supply-chain approval and multi-hour endurance remains pending.
   AMD Strix Halo remains untested.
7. GitHub branch rules and mandatory reviewer policies require repository-owner
   workflow decisions and are not enabled automatically.

## Release checks

```bash
python -m pip install -e ".[dev]"
make validate
make security
```

Review Dependabot and CodeQL findings before every release. Re-run target-device
acceptance when the model, runtime, input resolution, camera, or device image
changes.

