# -*- coding: utf-8 -*-
from .base import CheckAdapter

# 日本語を含むので UTF-8 で保存してください
BANNED = {"殺害", "テロ", "差別", "違法", "児童", "暴力"}

class ModerationAdapter(CheckAdapter):
    async def run(self, payload):
        text = ((payload or {}).get("text") or (payload or {}).get("prompt") or "")
        hits = [w for w in BANNED if w in text]
        severity = 0.8 if hits else 0.0
        return {"severity": severity, "hits": hits}

    def normalize(self, raw):
        return float(raw.get("severity", 0.0))
