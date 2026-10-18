
"""
Browser authentication endpoints for BRAG.

The browser uses a server-managed, HttpOnly session cookie.
Developer API-key authentication remains independent.

Security notes:
- Browser state-changing requests require a trusted Origin.
- Logout requires a session-bound CSRF token.
- Registration and login have basic per-process rate limits.
- Production requires HTTPS and a trusted reverse proxy.
- Multi-worker deployments require shared rate-limit storage.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

from collections import defaultdict, deque
from urllib.parse import urlsplit

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.api.browser_auth_schemas import (
    AccountResponse,
    CredentialsRequest,
    SessionResponse,
)
from app.core.config import get_brag_environment
from app.db.database import get_database_session
from app.services.account_registration_service import (
    AccountRegistrationService,
    DuplicateEmailError,
    RegistrationError,
)
from app.services.browser_session_service import (
    BrowserSessionService,
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Browser Authentication"],
)

COOKIE_NAME = "brag_session"
COOKIE_MAX_AGE = 12 * 60 * 60

RATE_LIMIT_WINDOW_SECONDS = 15 * 60
LOGIN_ATTEMPT_LIMIT = 10
REGISTRATION_ATTEMPT_LIMIT = 5

# These counters are intentionally process-local.
# Replace with shared storage before multi-worker deployment.
_rate_limit_lock = threading.Lock()
_rate_limit_attempts: dict[
    tuple[str, str],
    deque[float],
] = defaultdict(deque)


def cookie_is_secure() -> bool:
    """Require HTTPS-only cookies in production."""
    return get_brag_environment() == "production"


def require_trusted_origin(request: Request) -> None:
    """
    Reject requests from a different browser origin.

    The deployment proxy must validate Host headers and preserve
    the public scheme and host.
    """
    origin = request.headers.get("origin")

    if not origin:
        raise HTTPException(
            status_code=403,
            detail="A valid request origin is required.",
        )

    parsed = urlsplit(origin)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid request origin.",
        )

    expected_origin = str(request.base_url).rstrip("/")

    if origin != expected_origin:
        raise HTTPException(
            status_code=403,
            detail="Request origin is not permitted.",
        )


def require_json_request(request: Request) -> None:
    """Reject non-JSON content on credential endpoints."""
    content_type = request.headers.get(
        "content-type",
        "",
    ).split(";", 1)[0].strip().lower()

    if content_type != "application/json":
        raise HTTPException(
            status_code=415,
            detail="Application/json is required.",
        )


def check_rate_limit(
    request: Request,
    action: str,
    limit: int,
) -> None:
    """
    Apply a basic rate limit to an authentication endpoint.

    The IP is obtained from the ASGI connection, not from an
    untrusted X-Forwarded-For header.
    """
    client_ip = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    key = (action, client_ip)
    now = time.monotonic()

    with _rate_limit_lock:
        attempts = _rate_limit_attempts[key]

        while (
            attempts
            and now - attempts[0] >= RATE_LIMIT_WINDOW_SECONDS
        ):
            attempts.popleft()

        if len(attempts) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please try again later.",
                headers={"Retry-After": "900"},
            )

        attempts.append(now)


def csrf_for_session(session_token: str) -> str:
    """Derive a CSRF token bound to one browser session."""
    return hmac.new(
        session_token.encode("utf-8"),
        b"brag-browser-csrf-v1",
        hashlib.sha256,
    ).hexdigest()


def get_current_browser_session(
    request: Request,
    database_session: Session,
):
    """Return the active account and its session token."""
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    user = BrowserSessionService(
        database_session
    ).authenticate(token)

    if user is None or user.email is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return user, token


@router.post(
    "/register",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    credentials: CredentialsRequest,
    request: Request,
    database_session: Session = Depends(get_database_session),
):
    """Create a new email/password account."""
    require_trusted_origin(request)
    require_json_request(request)

    check_rate_limit(
        request,
        "register",
        REGISTRATION_ATTEMPT_LIMIT,
    )

    service = AccountRegistrationService(database_session)

    try:
        user = service.register(
            credentials.email,
            credentials.password,
        )
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=409,
            detail="Unable to register this email address.",
        ) from exc
    except RegistrationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return AccountResponse(
        user_id=user.user_id,
        email=user.email,
    )


@router.post(
    "/login",
    response_model=SessionResponse,
)
def login(
    credentials: CredentialsRequest,
    request: Request,
    response: Response,
    database_session: Session = Depends(get_database_session),
):
    """Verify credentials and issue a browser session."""
    require_trusted_origin(request)
    require_json_request(request)

    check_rate_limit(
        request,
        "login",
        LOGIN_ATTEMPT_LIMIT,
    )

    account_service = AccountRegistrationService(
        database_session
    )

    user = account_service.verify_credentials(
        credentials.email,
        credentials.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    session_service = BrowserSessionService(
        database_session
    )

    # Only revoke a session if it belongs to this same user.
    old_token = request.cookies.get(COOKIE_NAME)

    if old_token:
        old_user = session_service.authenticate(old_token)

        if old_user is not None and old_user.id == user.id:
            session_service.revoke(old_token)

    created = session_service.create(user)

    response.set_cookie(
        key=COOKIE_NAME,
        value=created.token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=cookie_is_secure(),
        samesite="strict",
        path="/",
    )

    return SessionResponse(
        user_id=user.user_id,
        email=user.email,
        csrf_token=csrf_for_session(created.token),
    )


@router.get(
    "/me",
    response_model=SessionResponse,
)
def me(
    request: Request,
    database_session: Session = Depends(get_database_session),
):
    """Return the signed-in account and its CSRF token."""
    user, token = get_current_browser_session(
        request,
        database_session,
    )

    return SessionResponse(
        user_id=user.user_id,
        email=user.email,
        csrf_token=csrf_for_session(token),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
    database_session: Session = Depends(get_database_session),
):
    """Revoke the active browser session and clear its cookie."""
    require_trusted_origin(request)

    _, token = get_current_browser_session(
        request,
        database_session,
    )

    expected_token = csrf_for_session(token)

    if (
        not x_csrf_token
        or not secrets.compare_digest(
            x_csrf_token,
            expected_token,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token.",
        )

    BrowserSessionService(
        database_session
    ).revoke(token)

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=cookie_is_secure(),
        httponly=True,
        samesite="strict",
    )

    response.status_code = 204
    return None
