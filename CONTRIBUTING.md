# Contributing to Gnosis

Thank you for your interest in contributing! This document covers everything you need to get started: local setup, branching, commit conventions, pre-PR checks, and coding standards.

---

## Local Setup

Follow the **[README Quickstart](README.md#quickstart)** to get the backend and frontend running.

Quick summary:

```bash
# Backend
cd backend
pip install -r requirements.txt
export SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export DEBUG=true
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm ci
npm run dev
```

Run database migrations before starting the backend against a real PostgreSQL instance:

```bash
cd backend
alembic upgrade head
```

---

## Branching Model

| Branch | Purpose |
|--------|---------|
| `main` | Protected, always-green. Direct pushes are disabled. |
| `feat/<scope>-<short-desc>` | New features |
| `fix/<scope>-<short-desc>` | Bug fixes |
| `chore/<scope>-<short-desc>` | Maintenance (deps, tooling, config) |
| `docs/<scope>-<short-desc>` | Documentation-only changes |
| `refactor/<scope>-<short-desc>` | Code restructuring without behaviour change |
| `ci/<scope>-<short-desc>` | CI / CD pipeline changes |
| `perf/<scope>-<short-desc>` | Performance improvements |

Examples: `feat/memory-decay-tuning`, `fix/auth-token-refresh-race`, `docs/runbook-redis`.

All changes to `main` must go through a pull request and pass CI.

---

## Conventional Commits

Gnosis uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit message **must** follow this format:

```
<type>(<optional scope>): <short summary in present tense>

[optional longer body]

[optional footers, e.g. Co-authored-by:]
```

### Allowed types

| Type | When to use |
|------|------------|
| `feat` | New user-visible feature |
| `fix` | Bug fix |
| `chore` | Maintenance; no prod code or test change |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or correcting tests |
| `ci` | CI / CD configuration changes |
| `style` | Formatting, white-space, linting (no logic change) |
| `perf` | Performance improvement |

### Examples

```
feat(agents): add persona inheritance to agent creation flow

fix(auth): prevent token refresh race condition under concurrent requests

docs(runbook): add Redis failure recovery steps

chore(deps): bump fastapi from 0.110 to 0.111

test(billing): add regression test for quota enforcement on free tier

ci: add frontend vitest step to CI matrix
```

Breaking changes must include `BREAKING CHANGE:` in the commit footer:

```
feat(api)!: rename /api/v1/awaken to /api/v1/awakening

BREAKING CHANGE: The /awaken prefix is removed. Update all clients.
```

---

## Required Pre-PR Checks

All checks below must pass locally before opening a PR. They mirror `.github/workflows/ci.yml` exactly.

### Backend

```bash
cd backend

# Lint (ruff)
pip install -q ruff
ruff check .
ruff format --check .

# Tests
export DEBUG=true
export SECRET_KEY="ci-test-secret-key-not-for-production-use-only"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
pytest tests/ -v --tb=short

# (Optional) coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
npx vitest run
```

If any check fails, fix it before pushing. PRs with failing CI will not be reviewed.

---

## Pull Request Guidance

When opening a PR:

1. **Title** — must be a valid Conventional Commit subject line (e.g. `feat(oracle): surface cross-agent cost outliers in dashboard`).
2. **What changed** — list the files/modules touched and why.
3. **Why** — link the issue or describe the motivation.
4. **How tested** — describe the test cases added or the manual test steps followed.
5. **Screenshots** — required for any UI change; annotate with arrows if behaviour is non-obvious.
6. **Breaking changes** — call them out explicitly in the PR description and in the commit footer.

Keep PRs small and focused. A PR that touches more than ~400 lines of logic (excluding generated code, migrations, and lock files) should usually be split.

---

## Code Style

### Python (backend)

- Formatter: **ruff format** (configured in `pyproject.toml` or `ruff.toml` if present; otherwise uses ruff defaults).
- Linter: **ruff check** with the default rule set.
- **Type annotations are required on all new public functions and methods.** Private helpers (`_foo`) should be annotated too unless genuinely trivial.
- Use `async def` for all I/O-bound functions; never block the event loop with synchronous database or network calls.
- Pydantic v2 models for all request/response contracts in `app/schemas/`; do not expose raw ORM models in API responses.
- New env vars must be added to `app/config.py` `Settings` class **and** documented in the README tech-stack / quickstart section.

### TypeScript / React (frontend)

- Linter: **ESLint** with `eslint-config-next`.
- Formatter: Prettier (if configured) — otherwise follow the existing file style.
- Components live in `frontend/src/components/`; pages in `frontend/src/app/`.
- Prefer server components (Next.js App Router defaults) unless you need client-side state or browser APIs; add `"use client"` only when necessary.
- State management: **Zustand** (existing store pattern). Do not introduce a second state library.

---

## Test Policy

| Change type | Required test |
|-------------|--------------|
| Bug fix | Regression test that reproduces the bug before the fix |
| New API endpoint | Integration test in `backend/tests/` exercising the happy path and at least one error path |
| New core engine method | Unit test covering the main logic branch |
| New frontend component | At minimum a render smoke-test via Vitest + `@testing-library/react` |
| Refactor | All existing tests must continue to pass; add new tests if coverage drops |

SQLite in-memory / file-based database is used for backend tests (see `DATABASE_URL` above). Tests must not require a live Redis or LLM provider key.

---

## Adding New Environment Variables

1. Add the variable to the `Settings` class in `backend/app/config.py` with a sensible default and a type annotation.
2. If the variable is required in production (no safe default), add a `model_validator` or raise in `validate_environment()` (`app/core/env_validator.py`).
3. Document it in the **Tech Stack** or **Quickstart** section of `README.md`.
4. Update `infra/terraform/secrets.tf` or `infra/terraform/ssm.tf` if it is a secret or environment-specific value that should be injected via AWS Secrets Manager / SSM Parameter Store in production.

---

## Questions?

Open a GitHub Discussion or tag `@gauthambinoy` in your PR.
