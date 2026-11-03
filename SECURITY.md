# Security and responsible disclosure

TerraCouncil integrates external model and text-to-speech APIs. API credentials must be supplied at runtime through environment configuration or an approved local credential mechanism. Never commit keys, tokens, `.env` files with real values, request headers, private scientific traces, user-specific paths or logs.

The repository intentionally excludes generated audio, PDFs and private scientific input archives from the source snapshot. Their absence is not a claim that the services or local demo never used them.

**Before publishing this repository publicly**, inspect all source files and history for secrets and personal information. A scanner result of zero issues is a useful preliminary signal, not a guarantee.

Report suspected exposures privately to the repository owner. Revoke and rotate exposed credentials before removing their traces from Git history.

This source package is intended for technical review. It does not contain validated regulatory recommendations or certified field science.
