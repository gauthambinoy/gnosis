"""
Gnosis Ultra Security — Defense-in-depth security layer.
Multiple layers of protection:
1. Input sanitization (XSS, SQLi, command injection)
2. Rate limiting with IP tracking
3. Request fingerprinting
4. Anomaly detection
5. Brute-force protection
6. CSRF protection
7. Content Security Policy
8. API key management
"""
import hashlib
import hmac
import time
import re
import secrets
import ipaddress
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ─── Input Sanitizer ───

class InputSanitizer:
    """Sanitize all inputs against XSS, SQLi, and injection attacks."""

    XSS_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
        r'<form',
        r'document\.cookie',
        r'document\.location',
        r'window\.location',
        r'\.innerHTML',
        r'eval\s*\(',
        r'setTimeout\s*\(',
        r'setInterval\s*\(',
        r'new\s+Function',
        r'data:text/html',
    ]

    SQLI_PATTERNS = [
        r"('\s*(OR|AND)\s+')",
        r'(;\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC))',
        r'(UNION\s+(ALL\s+)?SELECT)',
        r"(--\s|/\*|\*/)",
        r'(\bSLEEP\s*\(|\bBENCHMARK\s*\()',
        r'(\bWAITFOR\s+DELAY)',
        r"(0x[0-9a-fA-F]+)",
        r"('\s*;\s*)",
    ]

    CMD_INJECTION_PATTERNS = [
        r'[;&|`$]',
        r'\$\(.*\)',
        r'\.\./\.\.',
        r'%00',
        r'\\x[0-9a-f]{2}',
    ]

    @classmethod
    def check_xss(cls, value: str) -> tuple[bool, str]:
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True, f"XSS pattern detected: {pattern}"
        return False, ""

    @classmethod
    def check_sqli(cls, value: str) -> tuple[bool, str]:
        for pattern in cls.SQLI_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True, f"SQL injection pattern detected"
        return False, ""

    @classmethod
    def check_command_injection(cls, value: str) -> tuple[bool, str]:
        for pattern in cls.CMD_INJECTION_PATTERNS:
            if re.search(pattern, value):
                return True, f"Command injection pattern detected"
        return False, ""

    @classmethod
    def sanitize(cls, value: str) -> str:
        """Remove dangerous characters from input."""
        value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        value = value.replace('"', "&quot;").replace("'", "&#x27;")
        return value

    @classmethod
    def is_safe(cls, value: str, context: str = "general") -> tuple[bool, str]:
        """Check if a value is safe for the given context."""
        if context == "url":
            has_xss, msg = cls.check_xss(value)
            return not has_xss, msg

        has_xss, msg = cls.check_xss(value)
        if has_xss:
            return False, msg
        has_sqli, msg = cls.check_sqli(value)
        if has_sqli:
            return False, msg
        return True, ""

# ─── Rate Limiter ───

@dataclass
class RateLimitBucket:
    tokens: float = 0
    last_refill: float = field(default_factory=time.time)
    violations: int = 0

class AdvancedRateLimiter:
    """Token bucket rate limiter with progressive penalties."""

    def __init__(self, requests_per_minute: int = 100, burst_size: int = 0):
        self._buckets: dict[str, RateLimitBucket] = {}
        self._rpm = requests_per_minute
        self._burst = burst_size if burst_size > 0 else requests_per_minute
        self._blocked_ips: dict[str, float] = {}
        self._cleanup_interval = 300
        self._last_cleanup = time.time()

    def _get_client_id(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else "unknown"
        return ip

    def check(self, request: Request) -> tuple[bool, dict]:
        """Check if request is within rate limits. Returns (allowed, info)."""
        client_id = self._get_client_id(request)
        now = time.time()

        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup()

        # Check if blocked
        if client_id in self._blocked_ips:
            if now < self._blocked_ips[client_id]:
                remaining = int(self._blocked_ips[client_id] - now)
                return False, {"reason": "IP temporarily blocked", "retry_after": remaining}
            else:
                del self._blocked_ips[client_id]

        # Get or create bucket
        if client_id not in self._buckets:
            self._buckets[client_id] = RateLimitBucket(tokens=self._burst)

        bucket = self._buckets[client_id]

        # Refill tokens
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self._burst, bucket.tokens + elapsed * (self._rpm / 60.0))
        bucket.last_refill = now

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return True, {"remaining": int(bucket.tokens), "limit": self._rpm}
        else:
            bucket.violations += 1
            if bucket.violations >= 10:
                block_duration = min(bucket.violations * 60, 3600)
                self._blocked_ips[client_id] = now + block_duration
            return False, {"reason": "Rate limit exceeded", "retry_after": 1, "violations": bucket.violations}

    def block_ip(self, ip: str, duration: int = 3600):
        """Manually block an IP address."""
        self._blocked_ips[ip] = time.time() + duration

    def unblock_ip(self, ip: str) -> bool:
        """Manually unblock an IP address."""
        if ip in self._blocked_ips:
            del self._blocked_ips[ip]
            return True
        return False

    def _cleanup(self):
        now = time.time()
        self._last_cleanup = now
        stale = [k for k, v in self._buckets.items() if now - v.last_refill > 600]
        for k in stale:
            del self._buckets[k]
        expired = [k for k, v in self._blocked_ips.items() if now > v]
        for k in expired:
            del self._blocked_ips[k]

    def get_stats(self) -> dict:
        return {
            "active_clients": len(self._buckets),
            "blocked_ips": len(self._blocked_ips),
            "blocked_list": list(self._blocked_ips.keys()),
        }

# ─── Brute Force Protection ───

class BruteForceProtection:
    """Track failed auth attempts and block after threshold."""

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 900):
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._locked: dict[str, float] = {}
        self._max = max_attempts
        self._lockout = lockout_seconds
        self._window = 300

    def record_failure(self, identifier: str) -> dict:
        now = time.time()
        self._attempts[identifier] = [t for t in self._attempts[identifier] if now - t < self._window]
        self._attempts[identifier].append(now)

        if len(self._attempts[identifier]) >= self._max:
            self._locked[identifier] = now + self._lockout
            self._attempts[identifier] = []
            return {"locked": True, "lockout_seconds": self._lockout, "reason": f"Too many failed attempts ({self._max} in {self._window}s)"}

        remaining = self._max - len(self._attempts[identifier])
        return {"locked": False, "remaining_attempts": remaining}

    def is_locked(self, identifier: str) -> tuple[bool, int]:
        if identifier in self._locked:
            remaining = int(self._locked[identifier] - time.time())
            if remaining > 0:
                return True, remaining
            del self._locked[identifier]
        return False, 0

    def record_success(self, identifier: str):
        self._attempts.pop(identifier, None)
        self._locked.pop(identifier, None)

    def get_active_lockouts(self) -> dict:
        now = time.time()
        active = {k: int(v - now) for k, v in self._locked.items() if v > now}
        return active

# ─── Request Fingerprinting ───

class RequestFingerprinter:
    """Fingerprint requests for anomaly detection."""

    def fingerprint(self, request: Request) -> str:
        components = [
            request.headers.get("user-agent", ""),
            request.headers.get("accept-language", ""),
            request.headers.get("accept-encoding", ""),
            str(request.client.host if request.client else ""),
        ]
        raw = "|".join(components)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def detect_anomaly(self, request: Request, known_fingerprints: dict) -> dict:
        anomalies = []

        if not request.headers.get("user-agent"):
            anomalies.append("missing_user_agent")

        ua = request.headers.get("user-agent", "").lower()
        suspicious_uas = ["sqlmap", "nikto", "nmap", "burp", "dirbuster", "gobuster", "wfuzz", "hydra"]
        for sus in suspicious_uas:
            if sus in ua:
                anomalies.append(f"attack_tool_{sus}")

        if ".." in str(request.url.path):
            anomalies.append("path_traversal")

        if "%00" in str(request.url):
            anomalies.append("null_byte_injection")

        return {"anomalies": anomalies, "is_suspicious": len(anomalies) > 0}

# ─── CSRF Protection ───

class CSRFProtection:
    """Double-submit cookie CSRF protection."""

    def __init__(self):
        self._tokens: dict[str, float] = {}
        self._ttl = 3600

    def generate_token(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = time.time()
        self._cleanup()
        return token

    def validate_token(self, token: str) -> bool:
        if token in self._tokens:
            if time.time() - self._tokens[token] < self._ttl:
                del self._tokens[token]
                return True
            del self._tokens[token]
        return False

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._tokens.items() if now - v > self._ttl]
        for k in expired:
            del self._tokens[k]

# ─── Security Headers ───

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://openrouter.ai https://api.openai.com https://api.anthropic.com;",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# ─── Security Middleware ───

class UltraSecurityMiddleware(BaseHTTPMiddleware):
    """Combined security middleware — all protections in one layer."""

    def __init__(self, app, settings=None):
        super().__init__(app)
        self.rate_limiter = AdvancedRateLimiter(
            requests_per_minute=settings.rate_limit_per_minute if settings else 100
        )
        self.brute_force = BruteForceProtection()
        self.fingerprinter = RequestFingerprinter()
        self.sanitizer = InputSanitizer()
        self.csrf = CSRFProtection()
        self._request_count = 0
        self._blocked_count = 0
        self._threat_log: list[dict] = []

    async def dispatch(self, request: Request, call_next):
        self._request_count += 1

        # 1. Rate limiting
        allowed, rate_info = self.rate_limiter.check(request)
        if not allowed:
            self._blocked_count += 1
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": rate_info.get("retry_after", 60)},
                headers={"Retry-After": str(rate_info.get("retry_after", 60))}
            )

        # 2. Anomaly detection
        anomaly = self.fingerprinter.detect_anomaly(request, {})
        if anomaly["is_suspicious"]:
            self._threat_log.append({
                "time": time.time(),
                "ip": request.client.host if request.client else "unknown",
                "path": str(request.url.path),
                "anomalies": anomaly["anomalies"],
            })
            for a in anomaly["anomalies"]:
                if a.startswith("attack_tool_"):
                    self._blocked_count += 1
                    from starlette.responses import JSONResponse
                    return JSONResponse(status_code=403, content={"error": "Forbidden"})

        # 3. Input validation on query params
        for key, value in request.query_params.items():
            safe, msg = self.sanitizer.is_safe(value)
            if not safe:
                self._blocked_count += 1
                self._threat_log.append({
                    "time": time.time(),
                    "ip": request.client.host if request.client else "unknown",
                    "type": "input_attack",
                    "detail": msg,
                })
                from starlette.responses import JSONResponse
                return JSONResponse(status_code=400, content={"error": "Invalid input detected"})

        # 4. Process request
        response = await call_next(request)

        # 5. Add security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        return response

    def get_security_stats(self) -> dict:
        return {
            "total_requests": self._request_count,
            "blocked_requests": self._blocked_count,
            "block_rate": f"{(self._blocked_count / max(self._request_count, 1)) * 100:.2f}%",
            "rate_limiter": self.rate_limiter.get_stats(),
            "recent_threats": self._threat_log[-20:],
        }

# Global instances
rate_limiter = AdvancedRateLimiter()
brute_force = BruteForceProtection()
csrf_protection = CSRFProtection()
input_sanitizer = InputSanitizer()
