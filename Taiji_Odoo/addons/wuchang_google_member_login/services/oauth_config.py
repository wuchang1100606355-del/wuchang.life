from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit


GOOGLE_MEMBER_CALLBACK_PATH = "/google/member/callback"
LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain"}
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
TRUSTED_GOOGLE_AUTHORIZATION_URLS = {
    "https://accounts.google.com/o/oauth2/auth",
    GOOGLE_AUTHORIZATION_URL,
}
TRUSTED_GOOGLE_USERINFO_URLS = {
    "https://www.googleapis.com/oauth2/v1/userinfo",
    "https://www.googleapis.com/oauth2/v2/userinfo",
    GOOGLE_USERINFO_URL,
}


def _normalized(value):
    return (value or "").strip().rstrip("/")


def trusted_google_authorization_url(configured_url):
    candidate = _normalized(configured_url)
    return (
        candidate
        if candidate in TRUSTED_GOOGLE_AUTHORIZATION_URLS
        else GOOGLE_AUTHORIZATION_URL
    )


def trusted_google_userinfo_url(data_endpoint=None, validation_endpoint=None):
    for value in (data_endpoint, validation_endpoint):
        candidate = _normalized(value)
        if candidate in TRUSTED_GOOGLE_USERINFO_URLS:
            return candidate
    return GOOGLE_USERINFO_URL


def build_callback_uri(
    explicit_redirect_uri=None,
    configured_base_url=None,
    web_base_url=None,
    request_base_url=None,
):
    explicit = _normalized(explicit_redirect_uri)
    if explicit:
        return explicit
    base_url = next(
        (
            value
            for value in (
                _normalized(configured_base_url),
                _normalized(web_base_url),
                _normalized(request_base_url),
            )
            if value
        ),
        "",
    )
    return f"{base_url}{GOOGLE_MEMBER_CALLBACK_PATH}" if base_url else ""


def public_base_url_from_callback(callback_uri):
    try:
        parsed = urlsplit(_normalized(callback_uri))
    except ValueError:
        return ""
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def public_base_url_state(base_url):
    try:
        parsed = urlsplit(_normalized(base_url))
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
            return "INVALID_REF" if base_url else "MISSING"
        if hostname in LOCAL_HOSTNAMES or hostname.endswith(".localhost"):
            return "INVALID_REF"
        try:
            if ip_address(hostname).is_loopback:
                return "INVALID_REF"
        except ValueError:
            pass
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return "INVALID_REF"
        return "PRESENT"
    except ValueError:
        return "INVALID_REF" if base_url else "MISSING"


def callback_uri_state(callback_uri):
    try:
        parsed = urlsplit(_normalized(callback_uri))
    except ValueError:
        return "INVALID_REF" if callback_uri else "MISSING"
    base_url = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    if public_base_url_state(base_url) != "PRESENT":
        return "INVALID_REF" if callback_uri else "MISSING"
    if parsed.path != GOOGLE_MEMBER_CALLBACK_PATH or parsed.query or parsed.fragment:
        return "INVALID_REF"
    return "PRESENT"


def login_health_state(
    provider_exists,
    provider_active,
    client_id_present,
    client_secret_present,
    public_base_url,
    callback_uri,
):
    ready = all(
        (
            provider_exists,
            provider_active,
            client_id_present,
            client_secret_present,
            public_base_url_state(public_base_url) == "PRESENT",
            callback_uri_state(callback_uri) == "PRESENT",
        )
    )
    return "PASS" if ready else "HOLD_CONFIGURATION_REQUIRED"
