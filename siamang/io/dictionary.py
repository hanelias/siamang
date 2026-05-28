"""Variable metadata dictionary I/O."""

from __future__ import annotations

import json
from pathlib import Path

from siamang.core.variable import VariableMap


class DictionaryWriter:
    def write(self, variables: VariableMap, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = variables.to_dict()
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output


class DictionaryReader:
    def read(self, path: str | Path) -> VariableMap:
        source = Path(path)
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Dictionary file must contain a JSON object.")
        return VariableMap.from_dict(payload)
