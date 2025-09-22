from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
from .adapters.plag import PlagiarismAdapter
from .adapters.moderation import ModerationAdapter
from .adapters.clip import CLIPAdapter
from .adapters.websearch import WebSearchAdapter


app = FastAPI(title="A15 Risk Engine")

class Risk(BaseModel):
    total: float
    level: str
    threshold_version: str

class EvidenceItem(BaseModel):
    source: str
    score: float
    detail: Dict[str, Any] = {}

class CheckResponse(BaseModel):
    job_id: str
    risk: Risk
    evidence: List[EvidenceItem]

POLICY_VERSION = date.today().isoformat()

def decide(total: float) -> str:
    if total >= 0.65:
        return "auto_block"
    if total >= 0.35:
        return "manual_review"
    return "auto_pass"

@app.post("/health")
async def health():
    return {"ok": True}

@app.post("/check/text", response_model=CheckResponse)
async def check_text(text: str = Form(...), prompt: Optional[str] = Form(None)):
    # Adapter呼び出し
    plag = PlagiarismAdapter()
    mod = ModerationAdapter()
    raw_plag = await plag.run({"text": text})
    raw_mod  = await mod.run({"text": text, "prompt": prompt})

    ev = [
        {"source": "Plagiarism", "score": plag.normalize(raw_plag), "detail": raw_plag},
        {"source": "Moderation", "score": mod.normalize(raw_mod),    "detail": raw_mod},
    ]
    # （任意）将来BERT等を追加
    weights = {"Plagiarism": 0.40, "Moderation": 0.10}
    total = sum(e["score"] * weights.get(e["source"], 0.0) for e in ev)
    level = decide(total)
    return {
        "job_id": "text-" + POLICY_VERSION,
        "risk": {"total": round(total, 4), "level": level, "threshold_version": POLICY_VERSION},
        "evidence": ev
    }

@app.post("/check/image", response_model=CheckResponse)
async def check_image(file: UploadFile = File(...), prompt: Optional[str] = Form(None)):
    # バイト読み取り（将来：EXIF除去等）
    content = await file.read()
    clip = CLIPAdapter()
    raw_clip = await clip.run({"image_bytes": content, "prompt": prompt})

    # 将来：TinEye / Vision を実装して追加
    ev = [
        {"source": "CLIP", "score": clip.normalize(raw_clip), "detail": raw_clip},
    ]
    weights = {"CLIP": 0.30}
    total = sum(e["score"] * weights.get(e["source"], 0.0) for e in ev)
    level = decide(total)
    return {
        "job_id": "img-" + POLICY_VERSION,
        "risk": {"total": round(total, 4), "level": level, "threshold_version": POLICY_VERSION},
        "evidence": ev
    }

# --- debug endpoints (temporary) ---
import os
from fastapi import Query
from typing import Optional
from .adapters.websearch import WebSearchAdapter

@app.get("/debug/env")
def debug_env():
    return {
        "SERPAPI_KEY_present": bool(os.getenv("SERPAPI_KEY")),
        "SERPAPI_KEY_preview": (os.getenv("SERPAPI_KEY") or "")[:6] + "..." if os.getenv("SERPAPI_KEY") else None,
    }

@app.get("/debug/websearch")
def debug_websearch(q: str = Query(..., description="query")):
    ws = WebSearchAdapter()
    items = ws.search(q)
    return {"count": len(items), "items": items[:5]}  # 先頭5件だけプレビュー
# --- end debug ---
