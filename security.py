"""
Enterprise Security Module
Implements salted password hashing, Role-Based Access Control (RBAC),
API key authentication, HTTP security headers, input sanitization, and audit trails.
"""

import os
import re
import hmac
import functools
from typing import List, Optional, Callable
from flask import request, session, redirect, url_for, jsonify, current_app, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Default Enterprise API Key for service-to-service communication
DEFAULT_API_KEY = os.environ.get("ENTERPRISE_API_KEY", "resume_matcher_enterprise_key_2026")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}
MAX_ALLOWED_FILE_SIZE = 16 * 1024 * 1024  # 16 MB


# =========================================================================
# PASSWORD CRYPTOGRAPHY
# =========================================================================

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256 with random salt."""
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    return generate_password_hash(password, method="pbkdf2:sha256:600000")


def verify_password(plain_password: str, hashed: str) -> bool:
    """Verify plain password against hashed password."""
    if not plain_password or not hashed:
        return False
    return check_password_hash(hashed, plain_password)


# =========================================================================
# INPUT VALIDATION & SANITIZATION
# =========================================================================

def is_allowed_file(filename: str) -> bool:
    """Verify file extension against whitelist."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def sanitize_input_text(text: str, max_length: int = 50000) -> str:
    """Strip null bytes, trim control chars, and enforce length boundaries."""
    if not text:
        return ""
    # Strip null bytes and non-printable control chars except tabs and newlines
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return clean[:max_length].strip()


def validate_file_payload(file_obj) -> tuple[bool, str]:
    """Validate uploaded file object for extension, filename safety, and content existence."""
    if not file_obj or file_obj.filename == "":
        return False, "No file payload received."
    
    filename = secure_filename(file_obj.filename)
    if not is_allowed_file(filename):
        return False, f"File format not supported. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
    
    return True, filename


# =========================================================================
# RBAC & AUTHENTICATION DECORATORS
# =========================================================================

def login_required(f: Callable) -> Callable:
    """Ensure active user session is present."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please sign in.", "code": "UNAUTHORIZED"}), 401
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles: List[str]) -> Callable:
    """Enforce role-based access control (e.g., ['hr'] or ['candidate'])."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get("user")
            if not user:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required.", "code": "UNAUTHORIZED"}), 401
                return redirect(url_for("login"))
            
            user_type = user.get("user_type", "").lower()
            if user_type not in [r.lower() for r in allowed_roles]:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({
                        "error": f"Access denied. Required role: {', '.join(allowed_roles)}.",
                        "code": "FORBIDDEN"
                    }), 403
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_key_required(f: Callable) -> Callable:
    """Authenticate automated external API calls via X-API-Key header."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # Fall back to user session if present
            if session.get("user"):
                return f(*args, **kwargs)
            return jsonify({"error": "Missing X-API-Key authorization header.", "code": "API_KEY_REQUIRED"}), 401
        
        # Constant-time comparison to prevent timing attacks
        expected_key = os.environ.get("ENTERPRISE_API_KEY", DEFAULT_API_KEY)
        if not hmac.compare_digest(api_key, expected_key):
            return jsonify({"error": "Invalid API Key.", "code": "INVALID_API_KEY"}), 403
        
        return f(*args, **kwargs)
    return decorated_function


# =========================================================================
# HTTP SECURITY HEADERS MIDDLEWARE
# =========================================================================

def apply_security_headers(response: Response) -> Response:
    """Inject hardened HTTP security headers into every server response."""
    # Content Security Policy (allows local fonts, Lucide icons, inline scripts for initialization)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


def get_client_ip() -> str:
    """Extract real client IP considering proxy headers safely."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"
