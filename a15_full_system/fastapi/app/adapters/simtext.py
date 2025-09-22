# fastapi/app/adapters/simtext.py
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class SimilarTextFinder:
    """
    与えられた候補文の中から、クエリに似ているものをスコア順に返す簡易ランカー
    """
    def __init__(self):
        self.vec = TfidfVectorizer(analyzer="char", ngram_range=(3,5), min_df=1)

    def rank(self, query: str, candidates: List[str], top_k: int = 10) -> List[Tuple[str,float]]:
        if not candidates:
            return []
        X = self.vec.fit_transform(candidates + [query])
        cand_mat = X[:-1]
        q_vec    = X[-1]
        sims = cosine_similarity(cand_mat, q_vec)
        scored = [(candidates[i], float(sims[i,0])) for i in range(len(candidates))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
