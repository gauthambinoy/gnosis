"""
Security Dashboard API — monitoring and management endpoints.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from app.config import get_settings
from app.core.auth import get_current_user_id
from app.core.security_hardened import (
    SECURITY_HEADERS,
    rate_limiter,
    brute_force,
    csrf_protection,
)

router = APIRouter(prefix="/api/v1/security", tags=["security"])

settings = get_settings()


# ─── Schemas ───


class BlockIPRequest(BaseModel):
    ip: str
    duration: int = 3600  # seconds


class UnblockIPRequest(BaseModel):
    ip: str


# ─── Helpers ───


def _get_middleware(request: Request):
    """Retrieve the UltraSecurityMiddleware instance from the app."""
    for middleware in getattr(request.app, "user_middleware", []):
        mw_cls = getattr(middleware, "cls", None)
        if mw_cls and mw_cls.__name__ == "UltraSecurityMiddleware":
            break
    # Walk the middleware stack to find UltraSecurityMiddleware
    from app.core.security_hardened import UltraSecurityMiddleware

    app = request.app
    # Starlette stores the middleware stack via app.middleware_stack
    stack = getattr(app, "middleware_stack", None)
    while stack is not None:
        if isinstance(stack, UltraSecurityMiddleware):
            return stack
        stack = getattr(stack, "app", None)
    return None


# ─── Endpoints ───


@router.get("/stats")
async def security_stats(request: Request, user_id: str = Depends(get_current_user_id)):
    """Overall security statistics."""
    mw = _get_middleware(request)
    if mw:
        return mw.get_security_stats()
    # Fallback using global instances
    return {
        "total_requests": 0,
        "blocked_requests": 0,
        "block_rate": "0.00%",
        "rate_limiter": rate_limiter.get_stats(),
        "recent_threats": [],
    }


@router.get("/threats")
async def recent_threats(request: Request, user_id: str = Depends(get_current_user_id)):
    """Recent threat log."""
    mw = _get_middleware(request)
    threats = mw._threat_log[-50:] if mw else []
    return {"threats": threats, "total": len(threats)}


@router.get("/blocked-ips")
async def blocked_ips(request: Request, user_id: str = Depends(get_current_user_id)):
    """Currently blocked IP addresses."""
    mw = _get_middleware(request)
    rl = mw.rate_limiter if mw else rate_limiter
    return {
        "blocked_ips": rl.get_stats()["blocked_list"],
        "total": rl.get_stats()["blocked_ips"],
    }


@router.post("/block-ip")
async def block_ip(body: BlockIPRequest, request: Request, user_id: str = Depends(get_current_user_id)):
    """Manually block an IP address."""
    mw = _get_middleware(request)
    rl = mw.rate_limiter if mw else rate_limiter
    rl.block_ip(body.ip, body.duration)
    return {"status": "blocked", "ip": body.ip, "duration": body.duration}


@router.post("/unblock-ip")
async def unblock_ip(body: UnblockIPRequest, request: Request, user_id: str = Depends(get_current_user_id)):
    """Unblock an IP address."""
    mw = _get_middleware(request)
    rl = mw.rate_limiter if mw else rate_limiter
    unblocked = rl.unblock_ip(body.ip)
    if not unblocked:
        raise HTTPException(status_code=404, detail="IP not found in block list")
    return {"status": "unblocked", "ip": body.ip}


# PUBLIC: CSRF token must be retrievable before login to protect auth POST endpoints
@router.get("/csrf-token")
async def get_csrf_token():
    """Generate a CSRF token."""
    token = csrf_protection.generate_token()
    return {"csrf_token": token}


@router.post("/scan")
async def security_scan(request: Request, user_id: str = Depends(get_current_user_id)):
    """Run a security self-scan and return score + findings."""
    findings = []
    score = 100

    # 1. Check SECRET_KEY
    if settings.secret_key == "gnosis-secret-key-change-in-production-minimum-32-chars":
        findings.append(
            {
                "severity": "critical",
                "category": "authentication",
                "title": "Default SECRET_KEY in use",
                "description": "The secret key has not been changed from the default value. This makes JWT tokens predictable.",
                "remediation": "Set a unique SECRET_KEY environment variable with at least 32 random characters.",
            }
        )
        score -= 30

    # 2. Check DEBUG mode
    if settings.debug:
        findings.append(
            {
                "severity": "high",
                "category": "configuration",
                "title": "Debug mode enabled",
                "description": "Debug mode exposes stack traces and internal details to attackers.",
                "remediation": "Set DEBUG=false in production.",
            }
        )
        score -= 15

    # 3. Check CORS configuration
    wildcard_origins = any(o == "*" for o in settings.allowed_origins)
    if wildcard_origins:
        findings.append(
            {
                "severity": "high",
                "category": "cors",
                "title": "CORS allows all origins",
                "description": "Wildcard CORS allows any website to make authenticated requests.",
                "remediation": "Restrict allowed_origins to specific trusted domains.",
            }
        )
        score -= 15

    # 4. Check security headers
    mw = _get_middleware(request)
    expected_headers = list(SECURITY_HEADERS.keys())
    missing_headers = []
    if not mw:
        missing_headers = expected_headers
        findings.append(
            {
                "severity": "medium",
                "category": "headers",
                "title": "Security middleware not detected",
                "description": "UltraSecurityMiddleware is not active in the middleware stack.",
                "remediation": "Add UltraSecurityMiddleware to the FastAPI application.",
            }
        )
        score -= 10
    else:
        for h in expected_headers:
            if h not in SECURITY_HEADERS:
                missing_headers.append(h)
        if missing_headers:
            findings.append(
                {
                    "severity": "medium",
                    "category": "headers",
                    "title": f"Missing security headers: {', '.join(missing_headers)}",
                    "description": "Some recommended security headers are not configured.",
                    "remediation": "Ensure all security headers are set in the middleware.",
                }
            )
            score -= 5

    # 5. Check rate limiting
    if settings.rate_limit_per_minute > 200:
        findings.append(
            {
                "severity": "low",
                "category": "rate_limiting",
                "title": "High rate limit threshold",
                "description": f"Rate limit is set to {settings.rate_limit_per_minute}/min which may be too permissive.",
                "remediation": "Consider lowering rate_limit_per_minute to 100 or less.",
            }
        )
        score -= 5

    # 6. Check token expiry
    if settings.access_token_expire_minutes > 60:
        findings.append(
            {
                "severity": "medium",
                "category": "authentication",
                "title": "Long access token expiry",
                "description": f"Access tokens expire after {settings.access_token_expire_minutes} minutes. Shorter lifetimes reduce risk.",
                "remediation": "Set access_token_expire_minutes to 30 or less.",
            }
        )
        score -= 5

    # 7. Check HTTPS enforcement (HSTS header presence)
    hsts_present = "Strict-Transport-Security" in SECURITY_HEADERS
    if not hsts_present:
        findings.append(
            {
                "severity": "high",
                "category": "transport",
                "title": "HSTS header not configured",
                "description": "HTTP Strict Transport Security is not set.",
                "remediation": "Add Strict-Transport-Security header to enforce HTTPS.",
            }
        )
        score -= 10

    # 8. Check brute force protection is active
    bf = mw.brute_force if mw else brute_force
    active_lockouts = bf.get_active_lockouts()
    if active_lockouts:
        findings.append(
            {
                "severity": "info",
                "category": "brute_force",
                "title": f"{len(active_lockouts)} active lockout(s)",
                "description": f"Identifiers locked: {', '.join(active_lockouts.keys())}",
                "remediation": "Review locked accounts for potential ongoing attacks.",
            }
        )

    score = max(0, score)

    return {
        "score": score,
        "grade": "A+"
        if score >= 95
        else "A"
        if score >= 85
        else "B"
        if score >= 70
        else "C"
        if score >= 50
        else "F",
        "findings": findings,
        "findings_count": {
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "high": sum(1 for f in findings if f.get("severity") == "high"),
            "medium": sum(1 for f in findings if f.get("severity") == "medium"),
            "low": sum(1 for f in findings if f.get("severity") == "low"),
            "info": sum(1 for f in findings if f.get("severity") == "info"),
        },
        "security_headers": {h: True for h in SECURITY_HEADERS.keys()},
        "brute_force_lockouts": active_lockouts,
    }
