# Frontend Security Notes

## Token storage model (issue H11)

### Background

Earlier versions of the frontend used Zustand's `persist` middleware to write
the entire auth state — including both `accessToken` and `refreshToken` —
into `localStorage` under the key `gnosis-auth`. Anything in `localStorage`
is readable from JavaScript, so a single XSS would have been sufficient to
exfiltrate long-lived credentials.

### Current (interim) model

Implemented in `src/lib/auth.ts`:

| Token        | Storage            | Lifetime              | JS-readable |
| ------------ | ------------------ | --------------------- | ----------- |
| accessToken  | In-memory only     | Until reload / logout | Yes (same realm) |
| refreshToken | `sessionStorage`   | Until tab close       | Yes (same realm) |

- `localStorage` is **not** used for any auth material.
- The store key in `sessionStorage` is `gnosis-auth-refresh` and persists
  only the `refreshToken` field via Zustand's `partialize`.
- A one-time migration runs at module load: if a legacy `gnosis-auth`
  entry exists in `localStorage`, the refresh token is moved to
  `sessionStorage` and the legacy entry is deleted. Existing logged-in
  users therefore stay logged in across the upgrade without ever having
  their refresh token re-written to `localStorage`.
- `src/lib/api.ts` reads tokens exclusively via the in-memory store
  (`useAuth.getState().accessToken`); it never touches `localStorage`.

### Why this is only an interim fix

Even with `sessionStorage`, the refresh token is reachable from any script
running in the same origin. We are accepting that risk temporarily because
removing `localStorage` exposure is the high-value win and can ship without
backend changes.

### Planned migration to httpOnly cookies

The follow-up work, owned by the backend team, is to issue the refresh
token as a cookie with:

- `HttpOnly` — not reachable from JavaScript at all.
- `Secure` — sent only over HTTPS.
- `SameSite=Strict` — never sent on cross-site navigations.
- `Path=/api/v1/auth/refresh` (or similar narrow scope).
- Short-lived `Max-Age` matching the refresh token TTL.

Once that is in place:

1. `/auth/login` and `/auth/register` will set the refresh cookie instead
   of returning `refresh_token` in the JSON body.
2. `/auth/refresh` will read the cookie and ignore the request body.
3. The frontend will drop the `sessionStorage` persistence entirely and
   keep only the access token in memory.
4. `useAuth.refreshAccessToken` will call `/auth/refresh` with
   `credentials: "include"` and no body.

Until the backend ships those changes, the storage model documented above
is the intended state.
