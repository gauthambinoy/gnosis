# Gnosis Compliance & Security Controls

Production security posture verification checklist.

## GDPR Compliance

### ✅ Data Protection Implementation

- **PII Scrubber** (`backend/app/core/pii_scrubber.py`):
  - Detects personal identifiable information in logs, LLM outputs
  - Masks: email addresses, phone numbers, SSN, credit cards, IP addresses
  - Scrubs before: logs, LLM responses, audit trails, error messages

- **Consent Management** (`backend/app/api/consent.py`):
  - Explicit opt-in for marketing communications
  - Cookie consent tracking
  - Third-party data sharing consent

- **Data Retention** (`backend/app/core/retention_engine.py`):
  - Auto-delete executions after 90 days (configurable)
  - Archive old agent configurations
  - Purge unused API keys

- **Right to Deletion** (`backend/app/api/gdpr.py`):
  - User can request account deletion
  - Cascade delete: agents, executions, webhooks, API keys
  - Audit log entry created for deletion request

### ✅ Data Access

- **Audit Logging** (`backend/app/core/audit_log.py`):
  - All data access logged
  - Timestamp, user, action, resource, IP address
  - 1-year retention by default

- **Access Controls**:
  - Multi-tenant isolation (workspace-level)
  - Per-agent permissions (owner, admin, executor roles)
  - API key scoping (read-only, execution-only, full-access)

### ✅ International Data Transfers

- **Data Residency** (`backend/app/api/residency.py`):
  - EU data stays in EU regions
  - Configure: `RESIDENCY_REGION="eu-west-1"`
  - Standard Contractual Clauses for subprocessor data flows

### Verification

```bash
# Test PII scrubber
curl -X POST http://localhost:8000/api/v1/pii/detect \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text": "Contact me at john.doe@example.com"}'
# Should detect: email address

# Check retention settings
curl http://localhost:8000/api/v1/retention/policies \
  -H "Authorization: Bearer $TOKEN"

# Request data export
curl -X POST http://localhost:8000/api/v1/gdpr/export \
  -H "Authorization: Bearer $TOKEN"
```

---

## SOC 2 Type II Controls

### ✅ CC1: Organization & Management

- **Security Policy**: SECURITY.md defines threat model & response procedures
- **Incident Response Plan**: Contact escalation in RUNBOOK.md
- **Risk Assessment**: Documented in SECURITY.md (threat models, attack vectors)

### ✅ CC2: Communication & Accountability

- **Security Incidents**: Reported to CISO and affected users within 72 hours
- **Change Management**: All code changes go through GitHub PR review + CI/CD
- **Security Training**: New engineers required to read SECURITY.md before access

### ✅ CC6: Secure Processing

- **Input Validation**: `backend/app/core/input_sanitizer.py`
  - SQL injection detection and prevention
  - XSS payload detection
  - Prompt injection detection via `detect_injection()`

- **Output Encoding**: Error messages, logs, LLM responses sanitized
- **Secrets Management**: Encrypted at rest (KMS), never in logs/errors

### ✅ CC7: Monitoring & Detection

- **Intrusion Detection**: Rate limiting, brute-force detection, anomaly alerts
- **Audit Logs**: All API access, data modifications logged
- **Alerts**: Error spike (5xx >1%), auth failures (>100/min), memory pressure (>80%)

### ✅ CC8: Incident Response

- **Incident Response Plan**: See RUNBOOK.md - Escalation Path section
- **Post-Incident Review**: Documented in private GitHub issues
- **Metrics**: Track MTTR (mean time to resolution), success rate

### ✅ A1: Logical Separation

- **Multi-Tenancy**: Each workspace isolated at database level
  - Row-level security on agents, executions, webhooks
  - API keys scoped to workspace

- **Environment Separation**: dev, staging, prod with distinct credentials

### ✅ A2: Physical Separation

- **Hosting**: AWS ECS Fargate (managed container isolation)
- **Database**: RDS with encryption at rest (KMS)
- **Network**: Private subnets, security groups, NACLs

### Verification

```bash
# Verify encryption at rest
aws rds describe-db-instances \
  --db-instance-identifier gnosis-prod-postgres \
  --query 'DBInstances[0].StorageEncrypted'
# Should return: True

# Audit recent access
aws logs filter-log-events \
  --log-group-name /ecs/gnosis-prod/backend \
  --filter-pattern '{ $.level = "ERROR" }' \
  --start-time $(date -d '1 hour ago' +%s000)
```

---

## Security Headers

### ✅ HTTP Security Headers Enabled

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

Configured in: `backend/app/middleware/security.py`

### ✅ TLS/SSL

- **Production**: TLS 1.3 only (enforced via CloudFront)
- **Minimum Cipher Suites**: AES256-GCM, ChaCha20-Poly1305
- **Certificate**: AWS Certificate Manager (auto-renewal)

---

## Dependency Security

### ✅ Dependency Scanning

- **GitHub Dependabot**: Auto-creates PRs for security updates
- **Lock Files**: requirements.txt pinned versions, package-lock.json for npm
- **Audit**: `pip audit`, `npm audit` run in CI/CD

### ✅ Vulnerability Management

- **CVSS >= 7.0**: Hotfix required within 7 days
- **CVSS 5.0-6.9**: Fix required within 30 days
- **CVSS < 5.0**: Fix in next release

---

## Data Encryption

### ✅ In Transit

- TLS 1.3 for all HTTP traffic
- Encrypted WebSocket connections (wss://)
- Database connections use SSL

### ✅ At Rest

| Data | Encryption | Key Management |
|------|-----------|-----------------|
| Database (PostgreSQL) | AES-256 (KMS) | AWS KMS, rotated annually |
| LLM API Keys | AES-256 (KMS) | AWS Secrets Manager |
| Backups | AES-256 (S3) | S3 default encryption |
| User Passwords | bcrypt | Salted hash, 12 rounds |

---

## Third-Party Assessment

### NIST Cybersecurity Framework

| Function | Status | Note |
|----------|--------|------|
| Identify | ✅ | Assets catalogued, risk assessment done |
| Protect | ✅ | Access controls, encryption, security hardening |
| Detect | ✅ | Logging, monitoring, alerting in place |
| Respond | ✅ | Incident response plan documented |
| Recover | ✅ | Backups tested, RTO/RPO defined |

### Required Assessments

- [ ] Third-party pen test (annual, Q4)
- [ ] Annual SOC 2 Type II audit
- [ ] GDPR Data Protection Impact Assessment (annually)
- [ ] Supply chain risk assessment (dependencies, cloud providers)

---

## Reporting & Remediation

### ✅ Vulnerability Disclosure

See [SECURITY.md](SECURITY.md) for responsible disclosure policy.

- Private reporting: GitHub Security Advisories or gauthambinoy@users.noreply.github.com
- Response SLA: 48 hours acknowledgement, 5 days triage, 30 days patch
- Public disclosure: After patch available

### ✅ Compliance Reporting

Annual reports to:
- Security team: Q4
- Legal/Privacy: Q1 (GDPR compliance)
- Finance/Audit: Q1 (SOC 2 findings)

---

## Checklists

### Pre-Production Deployment

- [ ] Secrets validated (no hardcoded credentials)
- [ ] TLS certificate installed and valid
- [ ] CORS configured (only expected origins)
- [ ] Rate limiting enabled and tested
- [ ] Database backups configured and tested
- [ ] Audit logging enabled
- [ ] Error messages sanitized (no PII leakage)
- [ ] Security headers present
- [ ] WAF rules applied
- [ ] Health checks configured
- [ ] Monitoring and alerting active

### Ongoing Compliance

- [ ] Weekly: Check Dependabot security alerts
- [ ] Monthly: Review audit logs for anomalies
- [ ] Quarterly: Dependency and CVSS audit
- [ ] Annually: Pen test + SOC 2 assessment
- [ ] Ad-hoc: Security incident reporting

---

## Support

Questions on compliance? Open issue with `compliance` label.

See: [SECURITY.md](SECURITY.md), [RUNBOOK.md](RUNBOOK.md), [DEPLOYMENT.md](DEPLOYMENT.md)
