# OAuth2 Scopes Audit

Periodic review of the OAuth scopes Gnosis requests from upstream identity providers.
**Principle of least privilege**: never request a scope we don't actively use.

Last reviewed: 2026-04-21.

---

## Google OAuth (Sign-In with Google)

| Scope | Why we request it | Used in code |
|-------|-------------------|--------------|
| `openid` | Standard OIDC identity | `app/auth/google.py:verify_id_token` |
| `email` | Primary account identifier | User record creation |
| `profile` | Display name + avatar URL | User profile UI |

**Not requested (and we don't want them):**
- `https://www.googleapis.com/auth/drive*` — no Drive access
- `https://www.googleapis.com/auth/gmail*` — no Gmail access
- `https://www.googleapis.com/auth/calendar*` — no Calendar access

**Action items:** None. Current scopes are minimal.

---

## GitHub OAuth (Sign-In with GitHub)

| Scope | Why we request it | Used in code |
|-------|-------------------|--------------|
| `read:user` | Get login + display name | `app/auth/github.py:fetch_user` |
| `user:email` | Primary email when private | `app/auth/github.py:fetch_emails` |

**Not requested:**
- `repo` — we don't read user repos
- `admin:org` — never
- `delete_repo` — never
- `gist` — no
- `workflow` — no

**Action items:** None.

---

## Microsoft / Entra ID (planned)

Not yet integrated. When added, request only:
- `openid`
- `email`
- `profile`

Reject any PR that adds `Mail.Read`, `Files.Read`, `User.ReadWrite.All` etc. unless we have a documented product need.

---

## SSO via SAML (Enterprise)

SAML is assertion-based, not scope-based. We require these attributes:
- `email` (NameID)
- `name` (DisplayName)
- `groups` (optional, for role mapping)

We do **not** consume any other claim.

---

## Audit Procedure (run quarterly)

1. `grep -RIn "scope" backend/app/auth/` — list every scope string
2. For each scope, confirm it appears in this document with a justification
3. For each justified scope, confirm the cited code path still uses it
4. Open a PR removing any unused scope; bump the version note above

```bash
cd backend
grep -RIn "scope=" app/auth/ | grep -v test
```

## Revocation

If a user revokes Gnosis from their Google/GitHub account:
- Their next request returns `401`
- They must re-authenticate (re-grant the scopes above)
- Their existing data and agents are preserved
