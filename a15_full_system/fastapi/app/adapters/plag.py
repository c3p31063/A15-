# fastapi/app/adapters/plag.py
from .base import CheckAdapter

class PlagiarismAdapter(CheckAdapter):
    async def run(self, payload):
        text = (payload or {}).get("text", "")
        # ダミー類似率：文字数ベース（あとで外部APIに置換）
        ratio = min(len(text) / 2000.0, 1.0)
        return {"ratio": ratio}

    def normalize(self, raw):
        return float(raw.get("ratio", 0.0))
