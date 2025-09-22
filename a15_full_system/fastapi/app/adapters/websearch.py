import os
from typing import List, Dict
import httpx


class WebSearchAdapter:
    """
    SerpAPI を使って Google 検索を行い、類似URLを最大 num 件返す。
    返却形式: List[{"title": str, "url": str, "snippet": str, "position": int}]
    """
    def __init__(self) -> None:
        self.api_key = os.getenv("SERPAPI_KEY")
        self.endpoint = "https://serpapi.com/search.json"

    def search(self, query: str, num: int = 20) -> List[Dict]:
        # APIキーが見えないときは空で返す（FastAPIの /debug/env で先に確認）
        if not self.api_key:
            return []

        params_base = {
            "engine": "google",
            "q": query,
            "hl": "ja",
            "gl": "jp",
            "num": 10,  # Google 検索は1ページ最大10件。ページングで20件まで取得
        }

        results: List[Dict] = []
        start = 0

        # 必要ならプロキシ設定（学内ネット等でブロック時）
        # proxies = {"http": "http://proxy:8080", "https": "http://proxy:8080"}
        # verify=False  # 社内CAなどで証明書検証が通らない場合
        # with httpx.Client(timeout=15.0, proxies=proxies, verify=False) as client:
        with httpx.Client(timeout=15.0) as client:
            while len(results) < num and start <= 50:  # 3〜4ページ分まで
                params = dict(params_base)
                params["api_key"] = self.api_key
                if start:
                    params["start"] = start

                r = client.get(self.endpoint, params=params)
                r.raise_for_status()
                data = r.json()

                organic = data.get("organic_results", []) or []
                for item in organic:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("link") or item.get("url"),
                        "snippet": item.get("snippet", ""),
                        "position": item.get("position"),
                    })

                # 次ページの有無をチェック
                next_url = (data.get("serpapi_pagination") or {}).get("next")
                if not next_url:
                    break

                start += 10  # 次ページへ

        # URLで重複除去しつつ num 件に丸める
        dedup: List[Dict] = []
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
