"""
Vector RAG module for GEMintern.
ChromaDB + Gemini Embedding 기반 문서 검색 시스템.

블로그 참고: "우리 팀 코드 스타일을 아는 AI 만들기 - RAG와 Vector DB 활용기"
- 청킹: 섹션/문단 기반 (투자 문서용)
- 임베딩: Gemini embedding-001 (768차원)
- Vector DB: ChromaDB (1 프로젝트 = 1 컬렉션)
- 배치: 100개 단위 (Gemini API 제한 고려)
"""

import hashlib
import os
import re
import time
from typing import List, Dict, Optional, Tuple

import chromadb

# --- Constants ---
# OneDrive 내 SQLite는 동기화 충돌로 segfault 유발 → 로컬 경로 사용
_LOCAL_DATA = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GEMintern")
VECTOR_DB_DIR = os.path.join(_LOCAL_DATA, "vectordb")
CHUNK_SIZE = 1500       # 약 375 토큰 (한국어 ~4자/토큰)
CHUNK_OVERLAP = 200     # 청크 간 겹침
MIN_CHUNK_LEN = 50      # 이보다 짧은 청크는 무시
BATCH_SIZE = 100        # Gemini embedding API 배치 크기
TOP_K = 15              # 유사도 검색 시 반환할 청크 수
EMBEDDING_MODEL = "gemini-embedding-001"


# --- Singleton ChromaDB client ---
_chroma_client: Optional[chromadb.PersistentClient] = None


def _get_chroma() -> chromadb.PersistentClient:
    """Get or create ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(VECTOR_DB_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
    return _chroma_client


def _collection_name(project_name: str) -> str:
    """프로젝트명 → ChromaDB 컬렉션명 (안전한 이름으로 변환)."""
    safe = re.sub(r'[^a-zA-Z0-9가-힣_-]', '_', project_name)
    # ChromaDB 컬렉션명은 3~63자, 영숫자로 시작/끝
    safe = safe.strip('_-') or 'default'
    if len(safe) < 3:
        safe = safe + '_collection'
    return safe[:63]


# ========================================
# Chunking (문서 → 청크 분리)
# ========================================

def chunk_document(text: str, doc_name: str,
                   chunk_size: int = CHUNK_SIZE,
                   overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """문서를 섹션/문단 기반으로 청킹.

    전략:
    1. 마크다운 헤딩(#, ##, ###)으로 섹션 분리
    2. 섹션이 chunk_size 초과 시 문단(\n\n) 단위로 재분리
    3. 문단도 길면 문장 단위로 분리 + overlap 적용
    """
    chunks = []

    # 1단계: 마크다운 헤딩으로 섹션 분리
    sections = _split_by_headings(text)

    for section_title, section_text in sections:
        if len(section_text.strip()) < MIN_CHUNK_LEN:
            continue

        if len(section_text) <= chunk_size:
            chunks.append({
                "text": section_text.strip(),
                "doc_name": doc_name,
                "section": section_title,
            })
        else:
            # 2단계: 긴 섹션은 문단으로 분리
            paragraphs = _split_by_paragraphs(section_text, chunk_size, overlap)
            for i, para in enumerate(paragraphs):
                if len(para.strip()) < MIN_CHUNK_LEN:
                    continue
                chunks.append({
                    "text": para.strip(),
                    "doc_name": doc_name,
                    "section": f"{section_title} (part {i+1})" if len(paragraphs) > 1 else section_title,
                })

    # 빈 결과면 전체를 강제 분할
    if not chunks and len(text.strip()) >= MIN_CHUNK_LEN:
        for i in range(0, len(text), chunk_size - overlap):
            segment = text[i:i + chunk_size]
            if len(segment.strip()) >= MIN_CHUNK_LEN:
                chunks.append({
                    "text": segment.strip(),
                    "doc_name": doc_name,
                    "section": f"전체 (part {i // (chunk_size - overlap) + 1})",
                })

    return chunks


def _split_by_headings(text: str) -> List[Tuple[str, str]]:
    """마크다운 헤딩으로 섹션 분리. (제목, 내용) 튜플 리스트 반환."""
    # 헤딩 패턴: # ~ ######
    pattern = r'^(#{1,6})\s+(.+)$'
    lines = text.split('\n')
    sections = []
    current_title = "서두"
    current_lines = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            # 이전 섹션 저장
            if current_lines:
                sections.append((current_title, '\n'.join(current_lines)))
            current_title = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # 마지막 섹션
    if current_lines:
        sections.append((current_title, '\n'.join(current_lines)))

    # 섹션이 하나뿐이면 그냥 반환
    if len(sections) <= 1:
        return [("전체", text)]

    return sections


def _split_by_paragraphs(text: str, chunk_size: int, overlap: int) -> List[str]:
    """긴 텍스트를 문단(\n\n) 단위로 분리하되, chunk_size 내로 묶기."""
    paragraphs = re.split(r'\n{2,}', text)
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            # 문단 자체가 chunk_size 초과면 강제 분할
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size])
            else:
                current = para
                continue
            current = ""

    if current:
        chunks.append(current)

    return chunks


# ========================================
# Embedding (Gemini embedding-001)
# ========================================

def _get_embeddings(api_key: str, texts: List[str],
                    max_retries: int = 3) -> List[List[float]]:
    """Gemini embedding API로 텍스트 리스트 임베딩. 배치 처리 + 재시도."""
    from google import genai

    client = genai.Client(api_key=api_key)
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]

        for attempt in range(max_retries):
            try:
                result = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                )
                all_embeddings.extend([e.values for e in result.embeddings])
                break
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait = (attempt + 1) * 10  # 10s, 20s, 30s
                    time.sleep(wait)
                else:
                    raise

        # Rate limit 방지: 배치 간 2초 대기
        if i + BATCH_SIZE < len(texts):
            time.sleep(2)

    return all_embeddings


# ========================================
# Index (문서 → 청킹 → 임베딩 → ChromaDB 저장)
# ========================================

def index_document(api_key: str, project_name: str, doc_name: str, content: str) -> int:
    """단일 문서를 벡터 인덱싱.

    Returns: 생성된 청크 수
    """
    if not content or len(content.strip()) < MIN_CHUNK_LEN:
        return 0

    # 1. 청킹
    chunks = chunk_document(content, doc_name)
    if not chunks:
        return 0

    # 2. 기존 문서 청크 삭제 (재인덱싱 지원)
    collection = _get_or_create_collection(project_name)
    _delete_doc_chunks(collection, doc_name)

    # 3. 임베딩 생성
    texts = [c["text"] for c in chunks]
    embeddings = _get_embeddings(api_key, texts)

    # 4. ChromaDB에 저장 (배치)
    ids = []
    documents = []
    metadatas = []
    embs = []

    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = _make_chunk_id(doc_name, idx)
        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "doc_name": chunk["doc_name"],
            "section": chunk["section"],
            "chunk_index": idx,
        })
        embs.append(embedding)

    # 500개 단위로 배치 upsert
    for i in range(0, len(ids), 500):
        collection.upsert(
            ids=ids[i:i+500],
            documents=documents[i:i+500],
            metadatas=metadatas[i:i+500],
            embeddings=embs[i:i+500],
        )

    return len(chunks)


def _get_index_meta_path(project_name: str) -> str:
    """벡터 인덱스 메타데이터 파일 경로."""
    col_name = _collection_name(project_name)
    return os.path.join(VECTOR_DB_DIR, f"_meta_{col_name}.json")


def _load_index_meta(project_name: str) -> Dict:
    """저장된 인덱스 메타데이터 로드. {doc_name: {"hash": ..., "chunks": ...}}"""
    import json as _json
    meta_path = _get_index_meta_path(project_name)
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return _json.load(f)
        except (ValueError, IOError):
            pass
    return {}


def _save_index_meta(project_name: str, meta: Dict):
    """인덱스 메타데이터 저장."""
    import json as _json
    os.makedirs(VECTOR_DB_DIR, exist_ok=True)
    meta_path = _get_index_meta_path(project_name)
    with open(meta_path, "w", encoding="utf-8") as f:
        _json.dump(meta, f, ensure_ascii=False, indent=2)


def _content_hash(content: str) -> str:
    """문서 내용의 SHA-256 해시 (앞 16자)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def index_project_all(api_key: str, project_name: str, force: bool = False) -> Dict:
    """프로젝트 문서 증분 벡터 인덱싱.

    - 변경/추가된 문서만 임베딩 → 인덱싱
    - 삭제된 문서는 벡터 DB에서 제거
    - force=True면 전체 재인덱싱
    """
    import core_rag
    docs_dict = core_rag.load_project_docs_dict(project_name)

    # 현재 문서 {stem: content}
    current_docs: Dict[str, str] = {}
    for doc_name, content in docs_dict.items():
        clean_name = doc_name.replace('.md', '')
        current_docs[clean_name] = content

    # 이전 인덱스 메타데이터
    old_meta = {} if force else _load_index_meta(project_name)
    new_meta: Dict[str, Dict] = {}

    # 분류: added / modified / unchanged / deleted
    added = []
    modified = []
    unchanged = []

    for doc_name, content in current_docs.items():
        h = _content_hash(content)
        if doc_name not in old_meta:
            added.append(doc_name)
        elif old_meta[doc_name].get("hash") != h:
            modified.append(doc_name)
        else:
            unchanged.append(doc_name)
            new_meta[doc_name] = old_meta[doc_name]

    deleted = [d for d in old_meta if d not in current_docs]

    # 1) 삭제된 문서 벡터 제거
    for doc_name in deleted:
        try:
            delete_doc_index(project_name, doc_name)
        except Exception:
            pass

    # 2) 추가/변경된 문서만 인덱싱
    to_index = added + modified
    total_new_chunks = 0
    indexed_docs = []
    errors = []

    for doc_name in to_index:
        content = current_docs[doc_name]
        try:
            n = index_document(api_key, project_name, doc_name, content)
            total_new_chunks += n
            indexed_docs.append(doc_name)
            new_meta[doc_name] = {
                "hash": _content_hash(content),
                "chunks": n,
            }
            # 문서 간 3초 대기 (rate limit 방지)
            if len(to_index) > 1:
                time.sleep(3)
        except Exception as e:
            errors.append({"doc": doc_name, "error": str(e)})

    # unchanged 문서의 기존 청크 수 합산
    kept_chunks = sum(old_meta[d].get("chunks", 0) for d in unchanged)

    # 메타데이터 저장
    _save_index_meta(project_name, new_meta)

    return {
        "success": len(errors) == 0,
        "indexed_docs": len(indexed_docs),
        "total_chunks": total_new_chunks + kept_chunks,
        "added": len(added),
        "modified": len(modified),
        "deleted": len(deleted),
        "unchanged": len(unchanged),
        "errors": errors,
    }


def delete_doc_index(project_name: str, doc_name: str):
    """문서의 벡터 인덱스 삭제."""
    try:
        collection = _get_or_create_collection(project_name)
        _delete_doc_chunks(collection, doc_name)
    except Exception:
        pass


def delete_project_index(project_name: str):
    """프로젝트 전체 벡터 인덱스 삭제."""
    try:
        chroma = _get_chroma()
        col_name = _collection_name(project_name)
        chroma.delete_collection(col_name)
    except Exception:
        pass


# ========================================
# Search (질문 → 임베딩 → 유사도 검색)
# ========================================

def search_similar(api_key: str, project_name: str, query: str,
                   top_k: int = TOP_K,
                   selected_docs: List[str] = None) -> List[Dict]:
    """질문과 유사한 청크 검색.

    Returns: [{"text", "doc_name", "section", "distance"}, ...]
    """
    collection = _get_or_create_collection(project_name)

    # 컬렉션이 비어있으면 빈 결과
    if collection.count() == 0:
        return []

    # 질문 임베딩
    query_embedding = _get_embeddings(api_key, [query])[0]

    # 메타데이터 필터 (선택된 문서만)
    where_filter = None
    if selected_docs:
        # .md 확장자 제거 통일
        clean_docs = [d.replace('.md', '') for d in selected_docs]
        if len(clean_docs) == 1:
            where_filter = {"doc_name": clean_docs[0]}
        else:
            where_filter = {"doc_name": {"$in": clean_docs}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    # 결과 정리
    chunks = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text": doc,
                "doc_name": meta["doc_name"],
                "section": meta.get("section", ""),
                "distance": dist,
            })

    return chunks


def build_context_from_search(api_key: str, project_name: str, query: str,
                              top_k: int = TOP_K,
                              selected_docs: List[str] = None,
                              max_chars: int = 800_000) -> str:
    """질문 기반으로 관련 청크를 검색하여 컨텍스트 문자열 생성.

    문서별로 그룹핑하여 읽기 쉬운 형태로 반환.
    """
    chunks = search_similar(api_key, project_name, query, top_k, selected_docs)

    if not chunks:
        return ""

    # 문서별 그룹핑
    doc_chunks: Dict[str, List[Dict]] = {}
    for c in chunks:
        doc_name = c["doc_name"]
        if doc_name not in doc_chunks:
            doc_chunks[doc_name] = []
        doc_chunks[doc_name].append(c)

    # 컨텍스트 조립
    parts = []
    total_len = 0
    for doc_name, doc_chunk_list in doc_chunks.items():
        header = f"===== 문서: {doc_name} ====="
        section_texts = []
        for c in doc_chunk_list:
            section_label = f"[{c['section']}]" if c['section'] else ""
            section_texts.append(f"{section_label}\n{c['text']}")

        doc_text = header + "\n" + "\n---\n".join(section_texts)

        if total_len + len(doc_text) > max_chars:
            remaining = max_chars - total_len
            if remaining > 200:
                parts.append(doc_text[:remaining] + "\n[... 컨텍스트 길이 제한]")
            break

        parts.append(doc_text)
        total_len += len(doc_text)

    return "\n\n".join(parts)


def get_index_stats(project_name: str) -> Dict:
    """프로젝트 벡터 인덱스 통계."""
    try:
        collection = _get_or_create_collection(project_name)
        count = collection.count()

        # 문서별 청크 수 집계
        if count > 0:
            all_meta = collection.get(include=["metadatas"])
            doc_counts = {}
            for meta in all_meta["metadatas"]:
                dn = meta.get("doc_name", "unknown")
                doc_counts[dn] = doc_counts.get(dn, 0) + 1
            return {
                "total_chunks": count,
                "documents": len(doc_counts),
                "per_doc": doc_counts,
                "indexed": True,
            }
        return {"total_chunks": 0, "documents": 0, "per_doc": {}, "indexed": False}
    except Exception:
        return {"total_chunks": 0, "documents": 0, "per_doc": {}, "indexed": False}


# ========================================
# Internal helpers
# ========================================

def _get_or_create_collection(project_name: str):
    """프로젝트의 ChromaDB 컬렉션 가져오기/생성."""
    chroma = _get_chroma()
    col_name = _collection_name(project_name)
    return chroma.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},  # 코사인 유사도
    )


def _delete_doc_chunks(collection, doc_name: str):
    """컬렉션에서 특정 문서의 모든 청크 삭제."""
    try:
        results = collection.get(
            where={"doc_name": doc_name},
            include=[],
        )
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass


def _make_chunk_id(doc_name: str, chunk_index: int) -> str:
    """청크 고유 ID 생성."""
    raw = f"{doc_name}::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]
