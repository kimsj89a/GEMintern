"""
BM25 키워드 검색 모듈.
rank_bm25 라이브러리 기반, 한국어 투자 문서에 최적화된 토크나이저 사용.
ChromaDB와 달리 인프로세스로 동작하여 subprocess 격리 불필요.
"""
import json
import logging
import os
import pickle
import re
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

RAG_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage")

# ── 토크나이저 ──

# 불용어 (한국어 조사/어미 + 영어)
_STOPWORDS = frozenset(
    "의 가 이 은 는 을 를 에 에서 와 과 도 로 으로 부터 까지 만 보다 처럼 "
    "하다 되다 있다 없다 것 수 등 및 또는 그 이 저 그것 이것 그런 "
    "the a an is are was were be been being have has had do does did "
    "and or but in on at to for of with by from".split()
)


def tokenize_korean(text: str) -> List[str]:
    """한국어+영어 혼합 텍스트를 토큰화.
    형태소 분석기 없이 regex 기반으로 처리 (Railway 배포 호환).
    """
    # 한글 2글자 이상, 영숫자 2글자 이상, 숫자 추출
    tokens = re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}|[\d]+(?:\.\d+)?', text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) >= 2]


# ── 인덱스 관리 ──

def _index_path(project_name: str) -> str:
    return os.path.join(RAG_ROOT, project_name, "_bm25_index.pkl")


def _meta_path(project_name: str) -> str:
    return os.path.join(RAG_ROOT, project_name, "_bm25_meta.json")


def is_indexed(project_name: str) -> bool:
    """BM25 인덱스 존재 여부."""
    return os.path.exists(_index_path(project_name))


def build_index(project_name: str, docs_dict: Dict[str, str],
                chunk_size: int = 1500, chunk_overlap: int = 200) -> dict:
    """프로젝트 문서로 BM25 인덱스를 빌드.

    Args:
        project_name: 프로젝트 저장소명 (storage_name)
        docs_dict: {doc_name: full_text} 맵
        chunk_size: 청크 크기 (문자)
        chunk_overlap: 청크 오버랩 (문자)

    Returns:
        {"chunks": int, "docs": int}
    """
    from core_rag_vector import chunk_document

    all_chunks: List[Dict] = []
    tokenized_corpus: List[List[str]] = []

    for doc_name, text in docs_dict.items():
        if not text or not text.strip():
            continue
        chunks = chunk_document(text, doc_name, chunk_size, chunk_overlap)
        for chunk in chunks:
            tokens = tokenize_korean(chunk["text"])
            if len(tokens) < 3:
                continue
            all_chunks.append(chunk)
            tokenized_corpus.append(tokens)

    if not tokenized_corpus:
        logger.warning(f"BM25: No valid chunks for project '{project_name}'")
        return {"chunks": 0, "docs": len(docs_dict)}

    bm25 = BM25Okapi(tokenized_corpus)

    # 저장
    idx_path = _index_path(project_name)
    os.makedirs(os.path.dirname(idx_path), exist_ok=True)

    with open(idx_path, "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": all_chunks}, f)

    # 메타데이터 (문서별 해시 등)
    meta = {
        "doc_count": len(docs_dict),
        "chunk_count": len(all_chunks),
        "doc_names": list(docs_dict.keys()),
    }
    with open(_meta_path(project_name), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    logger.info(f"BM25: Indexed {len(all_chunks)} chunks from {len(docs_dict)} docs for '{project_name}'")
    return {"chunks": len(all_chunks), "docs": len(docs_dict)}


def _load_index(project_name: str) -> Optional[dict]:
    """인덱스 로드. 없으면 None."""
    idx_path = _index_path(project_name)
    if not os.path.exists(idx_path):
        return None
    try:
        with open(idx_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.warning(f"BM25: Failed to load index for '{project_name}': {e}")
        return None


def search(project_name: str, query: str, top_k: int = 20,
           selected_docs: Optional[List[str]] = None) -> List[Dict]:
    """BM25 검색. 스코어 포함 결과 반환.

    Returns:
        [{"text": ..., "doc_name": ..., "section": ..., "bm25_score": ..., "rank": ...}]
    """
    data = _load_index(project_name)
    if data is None:
        return []

    bm25: BM25Okapi = data["bm25"]
    chunks: List[Dict] = data["chunks"]

    query_tokens = tokenize_korean(query)
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)

    # (score, index) 쌍 정렬
    scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    results = []
    for rank, (idx, score) in enumerate(scored):
        if score <= 0:
            break
        if len(results) >= top_k:
            break

        chunk = chunks[idx]

        # selected_docs 필터
        if selected_docs and chunk["doc_name"] not in selected_docs:
            continue

        results.append({
            **chunk,
            "bm25_score": float(score),
            "rank": rank,
        })

    return results


def delete_index(project_name: str):
    """프로젝트 BM25 인덱스 삭제."""
    for path in [_index_path(project_name), _meta_path(project_name)]:
        if os.path.exists(path):
            os.remove(path)
