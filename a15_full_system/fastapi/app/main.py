from fastapi import FastAPI, UploadFile, File, Form, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
import os

from .adapters.plag import PlagiarismAdapter
from .adapters.moderation import ModerationAdapter
from .adapters.clip import CLIPAdapter
from .adapters.web_search import WebSearchAdapter  # ← 1ファイルに集約したアダプタ

app = FastAPI(title="A15 Risk Engine")

# =========================
# Pydantic models (既存)
# =========================
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

# =========================
# Health
# =========================
@app.post("/health")
async def health():
    return {"ok": True}

# =========================
# Text check (既存)
# =========================
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
    # 将来BERT等を追加するならここに重みを足す
    weights = {"Plagiarism": 0.40, "Moderation": 0.10}
    total = sum(e["score"] * weights.get(e["source"], 0.0) for e in ev)
    level = decide(total)
    return {
        "job_id": "text-" + POLICY_VERSION,
        "risk": {"total": round(total, 4), "level": level, "threshold_version": POLICY_VERSION},
        "evidence": ev
    }

# =========================
# Image check (既存: CLIPのみ)
# =========================
@app.post("/check/image", response_model=CheckResponse)
async def check_image(file: UploadFile = File(...), prompt: Optional[str] = Form(None)):
    # バイト読み取り（将来：EXIF除去等）
    content = await file.read()
    clip = CLIPAdapter()
    raw_clip = await clip.run({"image_bytes": content, "prompt": prompt})

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

# =========================================================
# ★ 新規: 画像アップロード → Web候補20件 → 類似度スコア(0..100)
# =========================================================
@app.post("/check/image_webscore")
async def check_image_webscore(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    top_k: int = Form(20),
):
    """
    1) 画像バイトを受け取り
    2) WebSearchAdapter.search_and_score_image_bytes() で
       Google Vision Web Detection による候補収集 + ローカル類似度スコア付与
    3) Django がそのまま保存・表示できる JSON を返す
    """
    ws = WebSearchAdapter()
    content = await file.read()

    # 類似候補 + 類似度スコア(0..100)
    result = ws.search_and_score_image_bytes(content, max_results=top_k)

    # 代表値として max_score を total に採用（運用方針に合わせて算出方法は調整可）
    total = float(result.get("max_score", 0.0))
    level = "manual_review"  # Web候補がある時点で一旦要確認扱い（運用で変更可）

    payload = {
        "job_id": "img-web-" + POLICY_VERSION,
        "risk": {"total": total, "level": level, "threshold_version": "vision+hash"},
        "similar_images": result.get("similar_images", []),  # [{url, thumbnail, score}, ...]
        "evidence": [
            {"source": "gcv_web_pages", "score": 0.0, "detail": {"url": p["url"]}}
            for p in result.get("pages", [])
        ],
    }
    return payload

# =========================================================
# 追加: SerpAPI ベースの利用（任意）
# =========================================================
@app.post("/websearch/text")
async def websearch_text(query: str = Form(...), num: int = Form(20)):
    """
    SerpAPI を使った通常のGoogle検索（テキスト）
    """
    ws = WebSearchAdapter()
    hits = ws.search_text(query, num=num)
    return {"organic_results": hits}

@app.post("/websearch/image_url")
async def websearch_image_url(image_url: str = Form(...), top_k: int = Form(20)):
    """
    SerpAPI の Google Lens。公開画像URLから類似を取得（bytes直投入ではない点に注意）
    """
    ws = WebSearchAdapter()
    result = ws.search_image_by_url(image_url, max_results=top_k)
    # Django側の SimilarImage 保存に合わせた形に整形
    return {
        "risk": {"total": 0.0, "level": "manual_review", "threshold_version": "google_lens"},
        "similar_images": [
            {"url": it["url"], "thumbnail": it.get("thumbnail") or it["url"], "score": 0.0}
            for it in result.get("similar_images", [])
        ],
        "evidence": [{"source": "lens_page", "score": 0.0, "detail": {"url": p["url"]}} for p in result.get("pages", [])],
    }

# =========================
# Debug endpoints
# =========================
@app.get("/debug/env")
def debug_env():
    return {
        "SERPAPI_KEY_present": bool(os.getenv("6c42895de0b0297d88e2fd2e4a6cbb24cc174db0b1825af37416ad03f80ecdc7")),
        "SERPAPI_KEY_preview": (os.getenv("6c42895de0b0297d88e2fd2e4a6cbb24cc174db0b1825af37416ad03f80ecdc7") or "")[:6] + "..." if os.getenv("6c42895de0b0297d88e2fd2e4a6cbb24cc174db0b1825af37416ad03f80ecdc7") else None,
        "VISION_API_KEY_present": bool(os.getenv("AIzaSyBPt-XZaMyh_bJH7ZuUzCGDZpEeb1ONzKY")),
        "VISION_API_KEY_preview": (os.getenv("AIzaSyBPt-XZaMyh_bJH7ZuUzCGDZpEeb1ONzKY") or "")[:6] + "..." if os.getenv("AIzaSyBPt-XZaMyh_bJH7ZuUzCGDZpEeb1ONzKY") else None,
    }

@app.get("/debug/websearch")
def debug_websearch(q: str = Query(..., description="query")):
    ws = WebSearchAdapter()
    items = ws.search_text(q, num=10)
    return {"count": len(items), "items": items[:5]}  # 先頭5件だけプレビュー

from .adapters.web_search import ReverseImageSearchAdapter

@app.post("/check/image", response_model=CheckResponse)  # 既存スキーマでOKなら流用
async def check_image(file: UploadFile = File(...), prompt: Optional[str] = Form(None)):
    image_bytes = await file.read()

    # 逆検索
    ris = ReverseImageSearchAdapter()
    out = await ris.search(image_bytes)

    # ここでは result/evidences/similar_images を組み立て、既存レスポンスに合わせる
    # 例:
    return {
        "risk_level": "manual_review",
        "risk_score_total": 0.5,
        "threshold_version": "v1",
        "evidences": [{"title":"source","url": p["url"]} for p in out["pages"]],
        "similar_images": [{"url": s["url"], "thumbnail": s["thumbnail"], "score": s["score"]} for s in out["similar_images"]],
        "raw": out,
    }