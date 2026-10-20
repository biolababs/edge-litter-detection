# Security policy

## Secrets

- Never place Roboflow, NGC, cloud, or repository tokens in source files,
  notebooks, command history, screenshots, or model metadata.
- Use environment variables or a local `.env` file that is excluded by
  `.gitignore`.
- Revoke the historical Roboflow key before publishing any legacy artifact.

## Model and data safety

- Treat downloaded model checkpoints as executable-like artifacts. Obtain them
  from an official source and record a checksum.
- Do not collect identifiable faces, license plates, private-property imagery,
  or location metadata unless the approved research protocol requires it.
- Keep raw data private by default. Publish only a reviewed, licensed,
  de-identified release.

## API deployment

- The API binds to `127.0.0.1` by default and has no built-in authentication.
- Do not expose it directly to the public internet. Use a firewall and an
  authenticated reverse proxy if remote access is required.
- Keep the request-size limit enabled to reduce accidental or malicious memory
  pressure.
- Run the service as a dedicated non-root user with read-only model/config
  mounts.
- Stream credentials and URL query parameters are removed from generated event
  and summary evidence. Do not place secrets in local filenames or model paths.

## Reporting

Do not publish a vulnerability, credential, or private dataset sample in a
public issue. Contact the repository owner privately.

