"""Pure URL helpers for opt-in search recovery. Never changes Home."""
import re
from urllib.parse import urlparse, parse_qs, urlencode


def is_google_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(re.fullmatch(
            r"(?:www\.)?google\.(?:com|[a-z]{2}|co\.[a-z]{2}|com\.[a-z]{2})", parsed.hostname or ""))
    except ValueError:
        return False


def needs_search_help(url, ok=True, blocked=False):
    return is_google_url(url) and (not ok or blocked or urlparse(url).path.startswith("/sorry"))


def duckduckgo_url(url):
    if not is_google_url(url):
        return "https://duckduckgo.com/"
    args = parse_qs(urlparse(url).query)
    onward = args.get("continue", [""])[0]
    if onward and is_google_url(onward):
        args = parse_qs(urlparse(onward).query)
    query = args.get("q", [""])[0]
    return "https://duckduckgo.com/" + ("?" + urlencode({"q": query}) if query else "")
