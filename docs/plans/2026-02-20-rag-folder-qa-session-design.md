# RAG DB 폴더 구조 + 자료기반 Q&A 세션 설계

## 개요

1. **RAG DB 인터페이스**: ProjectPage의 문서 리스트를 폴더/트리 구조로 개선
2. **자료기반 Q&A 페이지**: 별도 NAV 페이지로 추가, 폴더 단위 source 선택 가능

## 구현 단계

### Phase 1: core_rag.py 폴더 지원 확장

- `_indexed_docs.json` 구조 변경: `{folders: {folder_name: [doc_names]}, root: [doc_names]}`
- 폴더 CRUD: `create_folder()`, `rename_folder()`, `delete_folder()`, `move_doc_to_folder()`
- 기존 flat 문서는 자동으로 root 폴더에 배치 (하위호환)
- `get_folder_tree()`: 폴더-문서 트리 구조 반환

### Phase 2: ProjectPage 트리뷰 전환

- `QListWidget` → `QTreeWidget`로 변경
- 폴더 노드 + 문서 노드 (아이콘 구분)
- 우클릭 컨텍스트 메뉴: 폴더 생성, 이름변경, 삭제, 문서 이동, 미리보기
- 드래그&드롭으로 문서를 폴더 간 이동
- 업로드 시 현재 선택 폴더에 저장

### Phase 3: FolderTreeSelector 위젯

- `widgets/folder_tree_selector.py`: 체크박스 달린 폴더 트리 위젯
- 폴더 체크 → 하위 문서 전체 선택/해제
- 전체선택/해제 버튼
- 선택 문서 수 표시
- `selection_changed` 시그널로 선택된 문서 목록 반환

### Phase 4: 자료기반 Q&A 페이지

- `pages/qa_session_page.py`: 새 페이지
- 좌측: FolderTreeSelector
- 우측: ChatWidget 기반 대화형 Q&A
- `main_window.py` NAV에 등록

## 파일 변경 목록

- `core_rag.py` - 폴더 API 추가
- `pages/project_page.py` - 트리뷰로 리팩토링
- `widgets/folder_tree_selector.py` - 새 위젯
- `pages/qa_session_page.py` - 새 페이지
- `main_window.py` - NAV 등록
- `widgets/__init__.py` - export 추가
