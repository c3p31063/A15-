import os
import io
import base64
import json
from typing import List, Dict, Any, Optional
import requests
import httpx
import base64, os, httpx
from google.cloud import vision

# --- Optional deps (類似度計算) ---
try:
    from PIL import Image
    import imagehash
except Exception:
    Image = None
    imagehash = None

try:
    import numpy as np
    import cv2
    from skimage.metrics import structural_similarity as ssim
except Exception:
    np = None
    cv2 = None
    ssim = None



class ReverseImageSearchAdapter:
    def __init__(self):
        self.serp_key = os.environ.get("SERPAPI_KEY")
        if not self.serp_key:
            raise RuntimeError("SERPAPI_KEY is required")
        # Vision (optional)
        self.vision_client = vision.ImageAnnotatorClient()

    async def search(self, image_bytes: bytes) -> dict:
        # --- SerpAPI: Google Lens (image_content base64) ---
        lens_payload = {
            "engine": "google_lens",
            "api_key": self.serp_key,
            "hl": "ja",
            "image_content": base64.b64encode(image_bytes).decode("utf-8"),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post("https://serpapi.com/search.json", data=lens_payload)
            r.raise_for_status()
            lens = r.json()

        sim_items = []
        pages = []

        # 類似画像候補
        for it in (lens.get("visual_matches") or []):
            sim_items.append({
                "url": it.get("link") or "",
                "thumbnail": (it.get("thumbnail") or it.get("image")) or "",
                "score": 0.0,  # 後で補正
            })
        # 出典ページ
        for it in (lens.get("pages") or []):
            if it.get("link"):
                pages.append({"url": it["link"]})

        # --- Vision の WebDetection でURL補強（任意） ---
        img = vision.Image(content=image_bytes)
        wd = self.vision_client.web_detection(image=img).web_detection
        if wd:
            for p in (wd.pages_with_matching_images or []):
                if p.url:
                    pages.append({"url": p.url})
            for vi in (wd.visually_similar_images or []):
                sim_items.append({
                    "url": vi.url,
                    "thumbnail": vi.url,
                    "score": 0.0,
                })

        # 重複排除
        seen = set()
        uniq_sim = []
        for x in sim_items:
            k = x["url"]
            if k and k not in seen:
                seen.add(k)
                uniq_sim.append(x)
        seen = set()
        uniq_pages = []
        for x in pages:
            k = x["url"]
            if k and k not in seen:
                seen.add(k)
                uniq_pages.append(x)

        return {
            "similar_images": uniq_sim[:50],
            "pages": uniq_pages[:50],
            "max_score": 0.0
        }
# =========================================================
# ユーティリティ
# =========================================================
def _open_image(b: bytes) -> "Image.Image":
    if Image is None:
        raise RuntimeError("Pillow not installed. pip install pillow imagehash")
    return Image.open(io.BytesIO(b)).convert("RGB")

def _hash_sim(h1, h2) -> float:
    # 64bit hash の距離→類似度(0..1)
    dist = (h1 - h2)
    return max(0.0, min(1.0, 1.0 - dist / 64.0))

def _ssim_score(a: "Image.Image", b: "Image.Image") -> Optional[float]:
    if ssim is None or cv2 is None or np is None:
        return None
    a = cv2.cvtColor(np.array(a.resize((256, 256))), cv2.COLOR_RGB2GRAY)
    b = cv2.cvtColor(np.array(b.resize((256, 256))), cv2.COLOR_RGB2GRAY)
    score = ssim(a, b, data_range=255)
    return float(max(0.0, min(1.0, score)))

def _score_pair(original_bytes: bytes, candidate_bytes: bytes) -> float:
    """
    0..100 の“似てる度”。軽量（hash主体）。SSIMが使えれば加点。
    """
    im1 = _open_image(original_bytes)
    im2 = _open_image(candidate_bytes)

    ph1 = imagehash.phash(im1) if imagehash else None
    ph2 = imagehash.phash(im2) if imagehash else None
    dh1 = imagehash.dhash(im1) if imagehash else None
    dh2 = imagehash.dhash(im2) if imagehash else None
    ah1 = imagehash.average_hash(im1) if imagehash else None
    ah2 = imagehash.average_hash(im2) if imagehash else None

    sims, ws = [], []
    if ph1 and ph2:
        sims.append(_hash_sim(ph1, ph2)); ws.append(2.0)
    if dh1 and dh2:
        sims.append(_hash_sim(dh1, dh2)); ws.append(1.5)
    if ah1 and ah2:
        sims.append(_hash_sim(ah1, ah2)); ws.append(1.5)

    ssim_val = _ssim_score(im1, im2)
    if ssim_val is not None:
        sims.append(ssim_val); ws.append(2.0)

    if not sims:
        return 0.0

    score01 = sum(s*w for s, w in zip(sims, ws)) / sum(ws)
    return round(score01 * 100.0, 2)

def _fetch_image_bytes(url: str, timeout: float = 15.0) -> Optional[bytes]:
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        ct = (r.headers.get("Content-Type") or "").lower()
        if "image" not in ct and not url.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")):
            return None
        return r.content
    except Exception:
        return None


# =========================================================
# WebSearchAdapter（全部まとめ）
# =========================================================
class WebSearchAdapter:
    """
    一つのアダプタで:
      - search_text:         SerpAPI で Google 検索（テキスト）
      - search_image_by_url: SerpAPI の Google Lens（公開画像URLの逆検索）
      - search_and_score_image_bytes:
            Google Vision Web Detection で候補URL収集→各候補を実ダウンロード→
            Pillow+imagehash(+SSIM)で 0..100 の「似てる度」を付けて返す
    """

    def __init__(self) -> None:
        self.serp_key: Optional[str] = os.getenv("6c42895de0b0297d88e2fd2e4a6cbb24cc174db0b1825af37416ad03f80ecdc7")              # SerpAPI
        self.vision_key: Optional[str] = os.getenv("AIzaSyBPt-XZaMyh_bJH7ZuUzCGDZpEeb1ONzKY")         # Google Cloud Vision
        self.serp_endpoint = "https://serpapi.com/search.json"
        self.vision_endpoint = "https://vision.googleapis.com/v1/images:annotate"

    # -------------------------
    # 1) テキスト検索（SerpAPI）
    # -------------------------
    def search_text(self, query: str, num: int = 20) -> List[Dict[str, Any]]:
        if not self.serp_key:
            return []
        params_base = {
            "engine": "google",
            "q": query,
            "hl": "ja",
            "gl": "jp",
            "num": 10,
            "api_key": self.serp_key,
        }
        results: List[Dict[str, Any]] = []
        start = 0
        with httpx.Client(timeout=20.0) as client:
            while len(results) < num and start <= 50:
                params = dict(params_base)
                if start:
                    params["start"] = start
                r = client.get(self.serp_endpoint, params=params)
                r.raise_for_status()
                data = r.json()
                for item in data.get("organic_results", []) or []:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("link") or item.get("url"),
                        "snippet": item.get("snippet", ""),
                        "position": item.get("position"),
                    })
                if not (data.get("serpapi_pagination") or {}).get("next"):
                    break
                start += 10

        # 重複除去
        dedup: List[Dict[str, Any]] = []
        seen = set()
        for it in results:
            u = it.get("url")
            if not u or u in seen:
                continue
            seen.add(u)
            dedup.append(it)
            if len(dedup) >= num:
                break
        return dedup

    # --------------------------------------------------------
    # 2) 画像URLの逆検索（SerpAPI: Google Lens）※公開URL必須
    # --------------------------------------------------------
    def search_image_by_url(self, image_url: str, max_results: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        if not self.serp_key:
            return {"similar_images": [], "pages": []}
        params = {
            "engine": "google_lens",
            "url": image_url,   # 公開URL
            "hl": "ja",
            "gl": "jp",
            "api_key": self.serp_key,
        }
        with httpx.Client(timeout=30.0) as client:
            r = client.get(self.serp_endpoint, params=params)
            r.raise_for_status()
            data = r.json()

        similar: List[Dict[str, Any]] = []
        for idx, it in enumerate((data.get("visual_matches") or [])):
            u = it.get("link") or it.get("image") or ""
            thumb = it.get("thumbnail") or it.get("image") or ""
            if not u:
                continue
            similar.append({"url": u, "thumbnail": thumb, "position": idx + 1})
            if len(similar) >= max_results:
                break

        pages: List[Dict[str, Any]] = []
        for item in (data.get("knowledge_graph") or {}).get("source", []) or []:
            pg = item.get("link")
            if pg:
                pages.append({"url": pg})

        return {"similar_images": similar, "pages": pages}

    # ----------------------------------------------------------------
    # 3) 画像バイトから「候補20件＋似てる度(0..100)」を返す（Vision+ローカル計測）
    # ----------------------------------------------------------------
    def search_and_score_image_bytes(self, image_bytes: bytes, max_results: int = 20) -> Dict[str, Any]:
        if not self.vision_key:
            raise RuntimeError("VISION_API_KEY is not set")

        # (A) Vision: 候補URLを収集
        content_b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "requests": [{
                "image": {"content": content_b64},
                "features": [{"type": "WEB_DETECTION", "maxResults": max_results}],
            }]
        }
        r = requests.post(self.vision_endpoint, params={"key": self.vision_key}, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        wd = (((data or {}).get("responses") or [{}])[0]).get("webDetection", {}) or {}

        fulls = [{"url": it.get("url",""), "thumbnail": it.get("url","")} for it in (wd.get("fullMatchingImages") or []) if it.get("url")]
        partials = [{"url": it.get("url",""), "thumbnail": it.get("url","")} for it in (wd.get("partialMatchingImages") or []) if it.get("url")]
        visually = [{"url": it.get("url",""), "thumbnail": it.get("url","")} for it in (wd.get("visuallySimilarImages") or []) if it.get("url")]

        pages = [{"url": it.get("url","")} for it in (wd.get("pagesWithMatchingImages") or []) if it.get("url")]

        # 重複除去して上限まで
        candidates, seen = [], set()
        for grp in (fulls, partials, visually):
            for it in grp:
                u = it["url"]
                if not u or u in seen:
                    continue
                seen.add(u)
                candidates.append(it)
                if len(candidates) >= max_results:
                    break
            if len(candidates) >= max_results:
                break

        # (B) 各候補をダウンロードして類似度スコア算出（0..100）
        items: List[Dict[str, Any]] = []
        for it in candidates:
            url = it["url"]
            cand = _fetch_image_bytes(url)
            if not cand:
                continue
            try:
                sim = _score_pair(image_bytes, cand)
            except Exception:
                sim = 0.0
            items.append({
                "url": url,
                "thumbnail": it.get("thumbnail") or url,
                "score": float(sim)
            })

        # score 降順で並べる
        items.sort(key=lambda x: x["score"], reverse=True)

        return {
            "similar_images": items,         # [{url, thumbnail, score(0..100)}...]
            "pages": pages,                  # [{url}...]
            "max_score": max([x["score"] for x in items], default=0.0),
        }
