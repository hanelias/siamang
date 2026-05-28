"""Media attachment for questions and answer options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_VALID_KINDS = {"image", "video", "audio"}
_EXT_TO_KIND = {
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "webp": "image",
    "svg": "image",
    "avif": "image",
    "mp4": "video",
    "webm": "video",
    "mov": "video",
    "m4v": "video",
    "ogv": "video",
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "m4a": "audio",
    "flac": "audio",
}


@dataclass(frozen=True, slots=True)
class Media:
    """A media attachment that can be rendered next to a question or option.

    ``kind`` is normalised to one of: image, video, audio. When omitted, it is
    inferred from the URL extension; a URL without a recognisable extension
    requires ``kind`` to be specified explicitly.
    """

    url: str
    kind: str | None = None
    alt: str | None = None
    caption: str | None = None
    autoplay: bool = False
    loop: bool = False
    controls: bool = True

    def __post_init__(self) -> None:
        if not self.url or not self.url.strip():
            raise ValueError("Media.url must not be empty.")
        kind = (self.kind or "").strip().lower() or _infer_kind(self.url)
        if kind is None:
            raise ValueError(
                f"Media.kind could not be inferred from URL {self.url!r}. "
                f"Specify kind explicitly: one of {sorted(_VALID_KINDS)}."
            )
        if kind not in _VALID_KINDS:
            raise ValueError(f"Unknown media kind {self.kind!r}. Allowed: {sorted(_VALID_KINDS)}.")
        object.__setattr__(self, "kind", kind)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": self.url, "kind": self.kind}
        if self.alt is not None:
            payload["alt"] = self.alt
        if self.caption is not None:
            payload["caption"] = self.caption
        if self.autoplay:
            payload["autoplay"] = True
        if self.loop:
            payload["loop"] = True
        if not self.controls:
            payload["controls"] = False
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Media:
        return cls(
            url=payload["url"],
            kind=payload.get("kind"),
            alt=payload.get("alt"),
            caption=payload.get("caption"),
            autoplay=bool(payload.get("autoplay", False)),
            loop=bool(payload.get("loop", False)),
            controls=bool(payload.get("controls", True)),
        )


def _infer_kind(url: str) -> str | None:
    path = url.split("?", 1)[0].split("#", 1)[0]
    dot = path.rfind(".")
    if dot < 0:
        return None
    ext = path[dot + 1 :].lower()
    return _EXT_TO_KIND.get(ext)
