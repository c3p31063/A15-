# fastapi/app/adapters/plag.py
from .base import CheckAdapter

class PlagiarismAdapter(CheckAdapter):
    async def run(self, payload):
        text = (payload or {}).get("text", "")
        # �_�~�[�ގ����F�������x�[�X�i���ƂŊO��API�ɒu���j
        ratio = min(len(text) / 2000.0, 1.0)
        return {"ratio": ratio}

    def normalize(self, raw):
        return float(raw.get("ratio", 0.0))
