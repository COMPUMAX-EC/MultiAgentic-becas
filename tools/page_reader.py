from __future__ import annotations

import socket
import urllib.error
import urllib.request

from config.settings import settings


class PageReadError(RuntimeError):
    pass


def read_page(url: str) -> str:
    if not url or not url.strip():
        raise PageReadError("Page URL cannot be empty.")

    request = urllib.request.Request(
        url=url.strip(),
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=settings.PAGE_READ_TIMEOUT_SECONDS
        ) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                raise PageReadError(f"Unsupported content type: {content_type}")
            return response.read().decode("utf-8", errors="ignore")
    except socket.timeout as exc:
        raise PageReadError(
            f"Page read timed out after {settings.PAGE_READ_TIMEOUT_SECONDS} seconds."
        ) from exc
    except urllib.error.HTTPError as exc:
        raise PageReadError(f"HTTP error while reading page: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise PageReadError("Connection error while reading page.") from exc
