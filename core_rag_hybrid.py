"""
하이브리드 RAG 검색 모듈.
BM25 키워드 검색 + 벡터 검색을 RRF(Reciprocal Rank Fusion)로 결합.
선택적 LLM 리랭킹으로 검색 품질 극대화.
"""
import json
import logging
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── RRF 퓨전 ──

def reciprocal_rank_fusion(
    *ranked_lists: List[Dict],
    k: int = 60,
    top_k: int = 15,
) -> List[Dict]:
    """여러 랭킹 리스트를 RRF로 퓨전.

    score(d) = sum(1 / (k + rank_i(d))) for each ranking i
    """
    # chunk를 text 해시로 식별
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked):
            key = _chunk_key(chunk)
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
            if key not in chunk_map:
                chunk_map[key] = chunk

    # 스코어 기준 정렬
    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for key in sorted_keys[:top_k]:
        chunk = chunk_map[key].copy()
        chunk["rrf_score"] = scores[key]
        results.append(chunk)

    return results


def _chunk_key(chunk: Dict) -> str:
    """청크의 고유 키 생성 (doc_name + 텍스트 앞 200자)."""
    text_prefix = chunk.get("text", "")[:200]
    return f"{chunk.get('doc_name', '')}::{text_prefix}"


# ── 벡터 검색 (서브프로세스 래퍼) ──

def _vector_search(api_key: str, project_name: str, query: str,
                   top_k: int = 20) -> List[Dict]:
    """기존 ChromaDB 벡터 검색을 서브프로세스로 호출."""
    script = f"""
import sys, json
sys.path.insert(0, r'{os.path.dirname(os.path.abspath(__file__))}')
import core_rag_vector as v
results = v.search_similar('{api_key}', '{project_name}', '''{query.replace("'", "\\'")}''', top_k={top_k})
print(json.dumps(results, ensure_ascii=False))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Vector search failed: {e}")
    return []


# ── 하이브리드 검색 ──

def hybrid_search(
    api_key: str,
    project_name: str,
    query: str,
    top_k: int = 15,
    selected_docs: Optional[List[str]] = None,
    use_vector: bool = True,
    use_bm25: bool = True,
) -> List[Dict]:
    """BM25 + 벡터 하이브리드 검색.

    둘 다 실패하면 빈 리스트 반환 (호출부에서 폴백 처리).
    """
    import core_rag_bm25

    bm25_results: List[Dict] = []
    vector_results: List[Dict] = []

    # 병렬 실행
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        if use_bm25 and core_rag_bm25.is_indexed(project_name):
            futures["bm25"] = executor.submit(
                core_rag_bm25.search, project_name, query, top_k * 2, selected_docs
            )
        if use_vector:
            futures["vector"] = executor.submit(
                _vector_search, api_key, project_name, query, top_k * 2
            )

        for name, future in futures.items():
            try:
                result = future.result(timeout=20)
                if name == "bm25":
                    bm25_results = result
                else:
                    vector_results = result
            except Exception as e:
                logger.warning(f"Hybrid search - {name} failed: {e}")

    # selected_docs 필터 (벡터 결과에도 적용)
    if selected_docs and vector_results:
        vector_results = [c for c in vector_results if c.get("doc_name") in selected_docs]

    # 결과가 하나만 있으면 그대로 반환
    if bm25_results and not vector_results:
        return bm25_results[:top_k]
    if vector_results and not bm25_results:
        return vector_results[:top_k]
    if not bm25_results and not vector_results:
        return []

    # RRF 퓨전
    return reciprocal_rank_fusion(bm25_results, vector_results, top_k=top_k)


# ── LLM 리랭킹 ──

def rerank_chunks(
    api_key: str,
    query: str,
    chunks: List[Dict],
    model: str = "gemini-2.5-flash",
    top_k: int = 8,
) -> List[Dict]:
    """Gemini로 청크를 쿼리 관련성 기준으로 리랭킹.

    5개 미만이면 리랭킹 생략.
    """
    if len(chunks) <= top_k:
        return chunks

    from ai_client import AIClient
    from google.genai import types

    # 청크 요약 (각 200자로 제한)
    chunk_summaries = []
    for i, c in enumerate(chunks[:20]):  # 최대 20개만
        preview = c["text"][:200].replace("\n", " ")
        chunk_summaries.append(f"[{i}] ({c.get('doc_name', '?')}) {preview}")

    prompt = (
        f"질문: {query}\n\n"
        f"아래 문서 청크들을 질문과의 관련성 순으로 정렬하세요.\n"
        f"가장 관련 높은 {top_k}개의 인덱스를 JSON 배열로만 반환하세요.\n"
        f"예: [3, 0, 7, 1, 5, 2, 4, 6]\n\n"
        + "\n".join(chunk_summaries)
    )

    try:
        client = AIClient(api_key=api_key)
        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            max_output_tokens=128,
        )
        response = client.models.generate_content(
            model=model, contents=prompt, config=config,
        )
        indices = json.loads(response.text.strip())
        if isinstance(indices, list):
            reranked = []
            for idx in indices[:top_k]:
                if isinstance(idx, int) and 0 <= idx < len(chunks):
                    reranked.append(chunks[idx])
            if reranked:
                return reranked
    except Exception as e:
        logger.warning(f"Reranking failed, returning original order: {e}")

    return chunks[:top_k]


# ── 컨텍스트 빌드 ──

def search_and_build_context(
    api_key: str,
    project_name: str,
    query: str,
    top_k: int = 15,
    max_chars: int = 800_000,
    selected_docs: Optional[List[str]] = None,
    enable_rerank: bool = True,
) -> str:
    """하이브리드 검색 → 리랭킹 → 컨텍스트 문자열 조립."""
    chunks = hybrid_search(
        api_key, project_name, query,
        top_k=top_k * 2 if enable_rerank else top_k,
        selected_docs=selected_docs,
    )

    if not chunks:
        return ""

    # 리랭킹
    if enable_rerank and len(chunks) > 5:
        chunks = rerank_chunks(api_key, query, chunks, top_k=top_k)

    # 컨텍스트 조립 (문서별 그룹핑)
    by_doc: Dict[str, List[Dict]] = {}
    for c in chunks:
        doc = c.get("doc_name", "unknown")
        by_doc.setdefault(doc, []).append(c)

    parts = []
    total = 0
    for doc_name, doc_chunks in by_doc.items():
        section = f"===== 문서: {doc_name} =====\n"
        for c in doc_chunks:
            section_name = c.get("section", "")
            text = c["text"]
            entry = f"[{section_name}]\n{text}\n---\n"
            if total + len(entry) > max_chars:
                break
            section += entry
            total += len(entry)
        parts.append(section)
        if total >= max_chars:
            break

    return "\n".join(parts)
