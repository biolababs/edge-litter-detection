# Security policy

## Supported versions

Security fixes are applied to the latest release on `main`. Older tags are not
maintained unless a release note explicitly says otherwise.

## Report a vulnerability

Use GitHub private vulnerability reporting from the repository **Security**
tab when available. Otherwise contact the repository owner privately through
their verified GitHub profile.

Do not disclose a vulnerability, credential, private image, stream URL, device
inventory, or location record in a public issue. Include a minimal
reproduction, affected revision, impact, and suggested mitigation. You should
receive an acknowledgement within seven days.

## Deployment boundary

The dashboard and API have no built-in user authentication. They bind to
loopback by default, and the Compose port is published only on
`127.0.0.1`.

- Do not bind the service directly to a public or shared network interface.
- Use an SSH tunnel for temporary remote testing.
- Use an authenticated, TLS-terminating reverse proxy or private service mesh
  for a managed deployment.
- `LITTER_CONTAINER_INTERNAL_BIND=true` is only for an internal container
  listener whose host port remains private.
- Keep firewall and cloud security-group rules closed to the API port.

Interactive OpenAPI documentation is disabled by default. A trusted local
developer may enable it with `LITTER_ENABLE_API_DOCS=true`.

## Implemented controls

- JPEG, PNG, and WebP are the only accepted image-upload types.
- Image request bytes, decoded pixels, and concurrent image requests are
  bounded.
- Active and retained stream sessions are bounded.
- Security response headers deny framing, content-type sniffing, indexing, and
  unnecessary browser capabilities.
- Downloaded default Hugging Face models use immutable commit revisions,
  SafeTensors, and `trust_remote_code=False`.
- The attributed demonstration video is HTTPS-only, size-bounded, format
  checked, and SHA-256 verified before publication.
- SQLite values are parameterized and the database is restricted to the
  service account where the operating system permits it.
- Generated JSON files are written atomically.
- CI actions are pinned to complete commit SHAs; CodeQL, dependency review,
  Dependabot, Ruff, and Bandit checks are configured.

## Secrets and operational data

- Keep tokens and stream credentials in environment variables or a secret
  manager, never in source, arguments recorded by another process, screenshots,
  notebooks, or model metadata.
- Prefer credential-free camera network paths or a protected local proxy.
- Protect `state/litter-edge.db`; it can contain vehicle, route, review, and
  collection information.
- Do not commit raw camera media, datasets, model weights, generated reports,
  or device inventories.
- Apply a retention policy to annotated media and per-detection records.

## Model and dependency safety

Treat checkpoints as executable-like supply-chain artifacts. Use project
defaults, immutable revisions, or a reviewed local artifact. Custom remote
Transformers references must use `owner/model@40-character-commit`.

Python 3.11 and later install Pillow 13. JetPack vendor environments that remain
on Python 3.10 use the latest compatible Pillow 12 release and must keep the API
private with upload limits enabled. Prefer a validated Python 3.11 device
runtime when the vendor PyTorch stack supports it.

Run:

```bash
python -m pip install -e ".[dev]"
make security
```

Review tool output before release; automated scanners do not prove that an
application is vulnerability-free.

## Vehicle and machinery safety

Detection and separation events are advisory. This software must never directly
energize a hydraulic, pneumatic, or electric arm. A safety-rated controller
must retain final authority with emergency-stop, exclusion-zone, proximity,
motion-limit, stale-signal, and fail-safe interlocks.

`litter.object.confirmed` means a tracked observation. Only an authenticated
human or controller workflow with positive pickup evidence may create
`litter.collection.confirmed`.

