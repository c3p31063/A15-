from typing import Any, Dict

class CheckAdapter:
    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
    def normalize(self, raw: Dict[str, Any]) -> float:
        raise NotImplementedError
