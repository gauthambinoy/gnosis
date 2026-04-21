# Gnosis Billing & Pricing

How usage is metered, what each tier includes, and how invoices are calculated.

---

## Tiers

| Tier | Monthly Price | Included Executions | Rate Limit | Concurrent Agents | Support |
|------|---------------|---------------------|------------|-------------------|---------|
| **Free** | $0 | 100 | 10/min | 1 | Community |
| **Starter** | $29 | 5,000 | 60/min | 5 | Email (48h) |
| **Pro** | $99 | 25,000 | 200/min | 25 | Email (24h) + Slack |
| **Business** | $499 | 200,000 | 1,000/min | 100 | Priority + dedicated CSM |
| **Enterprise** | Custom | Unlimited | Custom | Unlimited | 24/7 + SLA |

All paid tiers include: SSO, audit logs, custom domains, webhook delivery, RPA browser hours.

---

## What Counts as Usage

### Billable
- **Execution**: A single `POST /api/v1/agents/{id}/execute` call that completes
- **LLM tokens**: Prompt + completion tokens passed through the gateway
- **RPA browser-minutes**: Wall-clock time a browser session is open
- **Webhook deliveries**: Each successful POST to your endpoint

### Not Billed
- Failed executions where the LLM was never called (e.g., validation rejected the input)
- Cached LLM responses (when prompt cache hits)
- Health-check, auth, and admin API calls
- Read-only API calls (`GET` listings of your own resources)

---

## Pricing Formulas

```
monthly_charge = base_subscription
               + max(0, executions_used   - executions_included)   * $0.005
               + llm_tokens_used                                   * provider_pass_through
               + max(0, browser_minutes   - browser_minutes_inc)   * $0.01
```

### Examples

**Pro user with 30,000 executions, 1.2M tokens, 80 browser minutes:**
- Base: $99
- Executions overage: (30,000 - 25,000) × $0.005 = $25
- LLM tokens: 1.2M × Anthropic rate (passed through, ~$3.60)
- Browser minutes: included
- **Total: ~$127.60**

LLM tokens are billed at-cost from the upstream provider with a 10% platform fee. We never markup.

---

## Quota Enforcement

Configured in `backend/app/core/quota_engine.py`. When you exceed an included quota:

1. **Soft limit** (within 110%): Request succeeds, header `X-Quota-Warning: true` added
2. **Hard limit** (above 110%): Request fails with `429 Quota Exceeded`
3. **Rate limit** (per-minute): Always enforced, returns `429 Rate Limited` with `Retry-After`

Check current usage:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/billing/usage
```

---

## Invoicing

- Billing cycle: 1st of each month, prorated for mid-month upgrades
- Payment: Stripe-managed cards, ACH (Business+), wire (Enterprise)
- Invoices: Auto-emailed on the 5th, downloadable from `/api/v1/billing/invoices`
- Currency: USD (EUR/GBP available for Enterprise)

### Refunds
- Within 7 days of charge for unused service: full refund
- Otherwise: pro-rated credit toward next invoice
- Disputed charges: see `RUNBOOK.md` → "Billing Disputes"

---

## Tier Changes

- **Upgrade**: Effective immediately, charged the prorated difference
- **Downgrade**: Effective at next billing cycle (no refund for unused upgrade)
- **Cancel**: Service continues until end of paid period, then auto-downgrades to Free

```bash
curl -X POST http://localhost:8000/api/v1/billing/change-tier \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"new_tier": "pro"}'
```

---

## Enterprise Add-ons

- **Custom SLA**: 99.9% / 99.95% / 99.99% uptime guarantees
- **Dedicated infra**: Single-tenant ECS cluster, isolated RDS, private VPC peering
- **Compliance**: SOC 2 report, BAA for HIPAA, DPA for GDPR
- **Custom contracts**: NET-30/60 invoicing, multi-year discounts

Contact sales at the email in `README.md`.

---

## Where the Code Lives

- **Tier definitions**: `backend/app/models/billing_tier.py`
- **Quota enforcement**: `backend/app/core/quota_engine.py`
- **Usage metering**: `backend/app/core/usage_meter.py`
- **Stripe webhooks**: `backend/app/api/billing_webhooks.py`
- **Pricing config**: `backend/app/config/pricing.yaml`

---

## FAQ

**Q: Do failed LLM calls count?**
Yes — once we send tokens to the provider, they're billed. Failures *before* the LLM call are free.

**Q: How are tokens counted with streaming?**
Final completion size, after the stream finishes (or is cancelled).

**Q: What if my browser session crashes?**
You're billed for the wall-clock time the session was alive, capped at the configured timeout (default 5 min).

**Q: Can I get a usage alert before hitting the limit?**
Yes — set `BILLING_ALERT_THRESHOLD=0.8` in your workspace settings to email you at 80% usage.
