# fastapi/app/adapters/clip.py
from .base import CheckAdapter

class CLIPAdapter(CheckAdapter):
    async def run(self, payload):
        # ダミー：本来は画像→埋め込み・近似
        # ここでは「プロンプト有りなら少し高め」を擬似
        prompt = (payload or {}).get("prompt") or ""
        score = 0.45 if prompt else 0.30
        return {"distance": score}  # 距離が大きいほどリスク高とみなす想定

    def normalize(self, raw):
        return float(raw.get("distance", 0.0))
