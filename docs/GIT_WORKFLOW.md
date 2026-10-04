# Git workflow (solo / 2-3 person hackathon)
- `main` is always demoable. Work on `feat/<name>` branches, merge via PR (CI must pass).
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
- Tag the demo build: `git tag v0.1-demo`.
- Secrets: never commit `.env` or service-account JSON (both are in `.gitignore`). If one leaks, rotate it; deleting the commit is not enough.
- Real retailer data stays out of git; use `data/seed.py` for synthetic data.
- Android/Termux: install `git`; HTTPS pushes use a GitHub personal access token as the password.
