"""Single maintainer sessions; no credentials are embedded in the web bundle."""

import hmac
from fastapi import HTTPException, Request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.config import get_settings

COOKIE = "f1_review"


def signer():
    settings = get_settings()
    if not settings.ADMIN_TOKEN or len(settings.SESSION_SECRET) < 32:
        raise HTTPException(
            503, "Review credentials are not configured. Run scripts/configure.py."
        )
    return URLSafeTimedSerializer(settings.SESSION_SECRET, salt="f1-review-v1")


def is_admin(request: Request) -> bool:
    token = request.headers.get("authorization", "")
    expected = get_settings().ADMIN_TOKEN
    if (
        expected
        and token.startswith("Bearer ")
        and hmac.compare_digest(token[7:].encode(), expected.encode())
    ):
        return True
    cookie = request.cookies.get(COOKIE)
    if cookie:
        try:
            return signer().loads(cookie, max_age=43200) == "maintainer"
        except (BadSignature, SignatureExpired, HTTPException):
            pass
    return False


def require_admin(request: Request):
    if not is_admin(request):
        raise HTTPException(401, "Sign in to review releases.")
    # Browser writes require same-origin fetch intent, in addition to SameSite cookies.
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not request.headers.get(
        "authorization"
    ):
        if request.headers.get("x-f1-review") != "1":
            raise HTTPException(403, "Missing review request header.")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Cross-site review requests are not allowed.")
