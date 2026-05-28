"""SurveyBundle — in-memory bundle of files ready to be deployed."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SurveyBundle:
    """A self-contained survey artefact (HTML + assets) ready to publish.

    ``files`` maps relative paths to file contents (``str`` for text files,
    ``bytes`` for binary). ``manifest`` carries metadata for the deploy layer.
    """

    files: dict[str, str | bytes] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)

    def write_to(self, target: str | Path) -> Path:
        """Write all files to ``target`` directory. Returns the directory path."""

        path = Path(target)
        path.mkdir(parents=True, exist_ok=True)
        for relative, content in self.files.items():
            destination = path / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                destination.write_bytes(content)
            else:
                destination.write_text(content, encoding="utf-8")
        return path

    def to_zip(self) -> bytes:
        """Return the bundle packaged as a single ZIP archive."""

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative, content in self.files.items():
                if isinstance(content, str):
                    archive.writestr(relative, content.encode("utf-8"))
                else:
                    archive.writestr(relative, content)
        return buffer.getvalue()

    def manifest_json(self) -> str:
        return json.dumps(self.manifest, ensure_ascii=False, indent=2, sort_keys=True)

    def compute_digest(self) -> str:
        """Compute SHA-256 digest of all bundle file contents for cache busting."""
        import hashlib

        h = hashlib.sha256()
        for name in sorted(self.files.keys()):
            content = self.files[name]
            if isinstance(content, str):
                h.update(content.encode("utf-8"))
            else:
                h.update(content)
        return h.hexdigest()[:16]

    def with_hashed_filenames(self) -> SurveyBundle:
        """Return a new bundle with content-hashed filenames for cache busting.

        E.g. app.js -> app.a1b2c3d4.js
             style.css -> style.e5f6g7h8.css
        """
        import re

        digest = self.compute_digest()
        new_files: dict[str, str | bytes] = {}
        mapping: dict[str, str] = {}

        js_css_pattern = re.compile(r"^(.+)\.(js|css)$")
        for name, content in self.files.items():
            m = js_css_pattern.match(name)
            if m and m.group(2) in ("js", "css"):
                file_hash = digest[:8]
                new_name = f"{m.group(1)}.{file_hash}.{m.group(2)}"
                new_files[new_name] = content
                mapping[name] = new_name
            else:
                new_files[name] = content

        # Update references in HTML
        html = new_files.get("index.html")
        if html and isinstance(html, str):
            for old_name, new_name in mapping.items():
                html = html.replace(f'src="{old_name}"', f'src="{new_name}"')
                html = html.replace(f'href="{old_name}"', f'href="{new_name}"')
            new_files["index.html"] = html

        return SurveyBundle(files=new_files, manifest=self.manifest)
