# Security Policy

## Public Repository Rules

This repository is intended to be public open source. Do not commit:

- `.env`, `.env.local`, or `.env.production`
- OAuth client secret files
- OAuth token files
- SQLite databases or backups
- Uploaded clips, generated videos, screenshots, or local test media
- Service account keys or private keys

Use `env.example` for placeholders only. Real production values live on the server or in a secret manager.

## If A Secret Is Exposed

1. Revoke or rotate the exposed credential immediately.
2. Remove the file from the repository.
3. Rewrite public Git history only after coordinating with maintainers, because force-pushing a public repo affects every clone.
4. Redeploy with fresh credentials.

## Reporting

Report security issues privately to the repository owner. Do not open public issues containing tokens, logs with secrets, or exploitable details.
