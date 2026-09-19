"""Static-serving helpers: cache policy + selective gzip compression.

Extracted from app.py so the header/compression behaviour can be regression
tested without importing the full application.

Two responsibilities:

1. RevalidatingStaticFiles - replaces the blanket ``Cache-Control: no-cache``
   that used to be applied to every .js/.css/.html static response. That
   policy forced ~160 conditional revalidation round-trips on every page
   load (the measured waterfall bottleneck). The new policy:

   - .html  -> ``no-cache`` (unchanged intent): the HTML shell is always
     revalidated so a new deployment's index/login is discovered
     immediately, along with any version-query changes it references.
   - Text deploy assets (.js/.mjs/.css/.json/.svg/.map/.txt) ->
     ``max-age=300, stale-while-revalidate=86400``: warm loads serve from the
     browser cache with zero round-trips for 5 minutes; after that the
     cached copy is served while a background revalidation pulls fresh
     bytes. Worst case after a deploy: a user runs one stale page-load of
     JS until their next navigation/reload - never permanently stranded,
     because HTML (which carries the ``?v=`` query strings) is always fresh.
   - Binary/media assets (fonts, raster images, audio/video, archives) ->
     ``max-age=2592000, immutable``: they only change when the image itself
     is rebuilt, and are excluded from compression anyway.

2. SelectiveGZipMiddleware - Starlette's GZipMiddleware (as of 1.3.1) only
   excludes ``text/event-stream``. That meant already-compressed formats
   (png, jpeg, woff2, zip, ...) were pointlessly re-compressed per request
   (CPU burn on multi-hundred-KB binaries). This subclass extends the
   exclusion list with media types that are already compressed, while
   leaving all text types (.js/.css/.html/.json/.svg/...) compressible.
"""

from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, GZipResponder, IdentityResponder
from starlette.staticfiles import StaticFiles

# Cache-Control for text assets that change with deployments. Short max-age
# + stale-while-revalidate: instant warm loads, background-refreshed after
# 5 minutes, guaranteed re-discovery of new deploys on the next navigation.
TEXT_ASSETS_CACHE_CONTROL = "max-age=300, stale-while-revalidate=86400"

# Cache-Control for binary assets that only change when the container image
# changes. 30 days, immutable (no revalidation RTTs at all).
MEDIA_ASSETS_CACHE_CONTROL = "max-age=2592000, immutable"

# HTML must be revalidated so new deployments are discovered immediately.
HTML_CACHE_CONTROL = "no-cache"

_TEXT_DEPLOY_SUFFIXES = (".js", ".mjs", ".css", ".json", ".svg", ".map", ".txt")
_MEDIA_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".bmp", ".tiff",
    ".ico", ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".webm", ".ogg", ".wav", ".m4a",
    ".zip", ".gz", ".7z", ".rar", ".pdf",
)
_HTML_SUFFIXES = (".html", ".htm")

# Content types that are already compressed - recompressing them wastes CPU
# for ~0% size win. Prefix-matched against the lowercased media type
# (parameters like "; charset=utf-8" are stripped first). Note: image/svg+xml
# is intentionally NOT listed - SVG is text and compresses well.
ALREADY_COMPRESSED_CONTENT_TYPES = (
    "text/event-stream",
    # Raster / pre-encoded image formats.
    "image/png", "image/jpeg", "image/webp", "image/avif", "image/gif",
    "image/bmp", "image/tiff", "image/heic", "image/heif",
    "image/x-icon", "image/vnd.microsoft.icon",
    # Media containers.
    "video/", "audio/",
    # Web fonts: woff/woff2/eot are internally compressed (ttf/otf are not
    # and remain compressible via their own types).
    "font/woff", "font/woff2", "font/collection", "application/vnd.ms-fontobject",
    # Archives and document formats with internal compression.
    "application/zip", "application/gzip", "application/x-gzip",
    "application/x-zip-compressed", "application/x-7z-compressed",
    "application/x-rar-compressed", "application/vnd.rar", "application/pdf",
    # Generic binary streams.
    "application/octet-stream",
)


class RevalidatingStaticFiles(StaticFiles):
    """StaticFiles with a per-asset-class Cache-Control policy.

    See module docstring for the policy and its deploy-update rationale.
    ETag/Last-Modified are untouched, so conditional requests still return
    cheap 304s (with the policy header preserved on the 304 as well).
    """

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        lower = path.lower()
        if lower.endswith(_HTML_SUFFIXES):
            resp.headers["Cache-Control"] = HTML_CACHE_CONTROL
        elif lower.endswith(_TEXT_DEPLOY_SUFFIXES):
            resp.headers["Cache-Control"] = TEXT_ASSETS_CACHE_CONTROL
        elif lower.endswith(_MEDIA_SUFFIXES):
            resp.headers["Cache-Control"] = MEDIA_ASSETS_CACHE_CONTROL
        return resp


class SelectiveGZipResponder(GZipResponder):
    """GZipResponder that also skips already-compressed content types."""

    async def send_with_compression(self, message):
        if message["type"] == "http.response.start":
            # Base class records initial_message and applies the default
            # (text/event-stream-only) exclusion; extend it afterwards.
            await super().send_with_compression(message)
            headers = Headers(raw=message["headers"])
            content_type = headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type.startswith(ALREADY_COMPRESSED_CONTENT_TYPES):
                self.content_type_is_excluded = True
            return
        await super().send_with_compression(message)


class SelectiveGZipMiddleware(GZipMiddleware):
    """GZipMiddleware that does not compress already-compressed media."""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # pragma: no cover
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        if "gzip" in headers.get("Accept-Encoding", ""):
            responder = SelectiveGZipResponder(
                self.app, self.minimum_size, compresslevel=self.compresslevel
            )
        else:
            responder = IdentityResponder(self.app, self.minimum_size)
        await responder(scope, receive, send)
