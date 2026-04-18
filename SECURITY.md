# Security Policy

## Supported Versions

| Version / Branch | Supported          |
| ---------------- | ------------------ |
| `main`           | ✅ Active support  |
| All other refs   | ❌ Not supported   |

---

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

### Option A – GitHub Private Security Advisory (preferred)

Go to **Security → Advisories → New draft security advisory** in this repository and submit a private report. The maintainer will be notified immediately.

### Option B – Email

Send a detailed report to **gauthambinoy@users.noreply.github.com** with the subject line:
`[gnosis] Security Vulnerability Report – <brief description>`

### What to include

- A clear description of the vulnerability and its impact
- Steps to reproduce (ideally a minimal proof-of-concept)
- Affected component(s) and endpoint(s)
- Any suggested mitigations

### Response Timeline

| Milestone                   | Target SLA   |
| --------------------------- | ------------ |
| Initial acknowledgement     | ≤ 48 hours   |
| Triage & severity rating    | ≤ 5 days     |
| Patch / workaround released | ≤ 30 days    |
| Public disclosure           | After patch  |

---

## Scope

### In Scope

- Authentication & authorisation bypass (JWT validation, role checks)
- Secrets/API key leakage (environment variables, logs, LLM responses)
- Prompt injection that leads to data exfiltration or privilege escalation
- Arbitrary code execution via the `system_control` endpoint
- Insecure direct object references on agent/task resources
- Missing or bypassable rate-limiting on `/agents/run` (abuse/DoS)
- Dependency vulnerabilities with a working exploit path (CVSS ≥ 7.0)
- SSRF via outbound HTTP calls made by agents or integrations

### Out of Scope

- Security issues in third-party services (OpenAI, Anthropic, etc.)
- Self-XSS or issues requiring a compromised browser
- Rate-limiting findings that require unrealistic client co-operation
- Feature requests disguised as security reports
- Reports from automated scanners with no accompanying proof-of-concept

---

## Threat Model

Gnosis is a **multi-tenant agent orchestration platform** that:

1. **Handles JWT authentication** – tokens are issued by the backend and verified on every request. Token signing keys must be rotated if a breach is suspected; short-lived access tokens with refresh-token rotation are the target design.

2. **Stores and proxies LLM API keys** – provider API keys (OpenAI, Anthropic, etc.) are stored encrypted at rest and injected into LLM calls server-side. A compromise of the database encryption key exposes all tenant API keys. Keys must never appear in logs, LLM responses, or error messages.

3. **Executes RPA / system-control actions** – the `system_control` endpoint can invoke browser automation and OS-level commands on behalf of agents. This is the highest-risk surface: strict input validation, sandbox isolation (e.g. Docker or gVisor), and a deny-by-default capability list are required. Any bypass here may yield RCE on the host.

4. **Calls untrusted LLM output** – agent pipelines pass LLM-generated content back into tool calls and other LLM prompts. Prompt injection (direct or indirect via retrieved documents) can hijack agent behaviour. All tool-call parameters should be validated against a schema before execution; LLM output should never be concatenated raw into privileged operations.

5. **Exposes a public `/agents/run` endpoint** – without per-tenant rate-limiting and concurrency caps this endpoint is an amplification vector for both cost abuse and DoS. Rate limits must be enforced at the API gateway layer, not only inside the application.

Maintainers should review findings in this order of priority: **RCE > secrets leakage > auth bypass > prompt injection > DoS > information disclosure**.
