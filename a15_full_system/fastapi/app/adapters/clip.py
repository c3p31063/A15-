# fastapi/app/adapters/clip.py
from .base import CheckAdapter

class CLIPAdapter(CheckAdapter):
    async def run(self, payload):
        # �_�~�[�F�{���͉摜�����ߍ��݁E�ߎ�
        # �����ł́u�v�����v�g�L��Ȃ班�����߁v���[��
        prompt = (payload or {}).get("prompt") or ""
        score = 0.45 if prompt else 0.30
        return {"distance": score}  # �������傫���قǃ��X�N���Ƃ݂Ȃ��z��

    def normalize(self, raw):
        return float(raw.get("distance", 0.0))
