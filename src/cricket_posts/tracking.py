"""Campaign links and the QR code that carries them.

A poster has two audiences for the same destination and they need different
things from it.

A person reads the URL and types it from memory, so it has to be short and free
of query strings — ``axon22yards.com/join`` gets typed correctly,
``…/join?location=houston&utm_source=instagram`` does not.

A phone camera does not care how long the link is, so the QR can carry the full
tagged URL. That is where attribution actually comes from: without it every
signup arrives as "direct traffic" and there is no way to tell which post
earned it.

So the printed link and the scanned link are deliberately different strings
pointing at the same place. Nothing here alters the copy on the poster; the
tagged URL exists only inside the QR and in the line printed for the caption.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_MEDIUM = "social"


def tracked_url(
    destination: str,
    *,
    campaign: str | None = None,
    source: str | None = None,
    medium: str = DEFAULT_MEDIUM,
) -> str:
    """Add UTM parameters to a destination, keeping any it already carries.

    ``?location=houston`` is a real routing parameter, not tracking, so it
    survives — merging rather than replacing is what keeps a link working when
    someone later adds a campaign tag to it.
    """
    if not destination:
        return ""
    if not campaign and not source:
        return destination

    parts = urlsplit(destination)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if source:
        query["utm_source"] = source
    if campaign:
        query["utm_campaign"] = campaign
    if source or campaign:
        query.setdefault("utm_medium", medium)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


#: Rendered pixels each QR module needs to survive screenshotting and
#: compression. Below about this, detectors start failing on the phone that is
#: actually pointed at the poster even though the code looks fine on a monitor.
MIN_PX_PER_MODULE = 4

#: Error correction level. "h" recovers the most damage but needs the most
#: modules, and modules are the scarce resource here — at "h" this URL needs 57
#: of them and the code has to be a fifth of the poster wide to stay readable.
#: "q" still recovers a quarter of the symbol and costs four fewer rows.
ERROR_LEVEL = "q"


@dataclass
class QrCode:
    data_uri: str
    #: Modules per side of the symbol itself, excluding the quiet border.
    modules: int
    #: Modules per side of the PNG, quiet border included. Sizing must follow
    #: *this* one: the border is part of the image, so sizing from the symbol
    #: silently shrinks every real module by the border's share — 212px across
    #: 57 rendered modules is 3.7px each, not the 4 it was asked for.
    image_modules: int

    def rendered_px(self, minimum: int = MIN_PX_PER_MODULE) -> int:
        """Width the image needs so each module lands on `minimum` pixels."""
        return self.image_modules * minimum


def qr_code(url: str, *, scale: int = 8, border: int = 2) -> QrCode | None:
    """A QR for `url` as an inline PNG, with the module count needed to size it.

    Inlined rather than written to disk because the renderer loads the page
    from a temporary file: a relative path would not resolve, and one more
    stray asset per poster is one more thing to clean up.
    """
    if not url:
        return None
    import segno

    code = segno.make(url, error=ERROR_LEVEL)
    buffer = io.BytesIO()
    code.save(buffer, kind="png", scale=scale, border=border)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return QrCode(
        data_uri=f"data:image/png;base64,{encoded}",
        modules=code.symbol_size(border=0)[0],
        image_modules=code.symbol_size(border=border)[0],
    )
