# 기존 문서 업데이트 기능 설계

## 개요

기존 문서를 업로드하고, 추가 자료 + 프롬프트를 반영하여 **원본 파일 포맷을 유지한 채** 업데이트된 문서를 출력하는 기능.

## 요구사항

- 범용 문서 업데이트 (투심보고서, IM, 일반 문서 등)
- 원본 파일 포맷 직접 수정 (서식 보존)
- 업데이트 모드 선택: 전체 재생성 / 부분 수정

## 아키텍처

```
[기존 문서] ─┐
             ├─→ core_doc_updater.py ─→ AI (Gemini) ─→ 원본 파일 직접 수정
[추가 자료] ─┤                           ↑
[프롬프트]  ─┘                      prompts.py
```

### 새 파일
- `core_doc_updater.py` — 비즈니스 로직
- `pages/doc_updater_page.py` — PyQt6 UI 페이지

### 수정 파일
- `prompts.py` — DOC_UPDATER_PROMPTS 추가
- `main_window.py` — NAV_SECTIONS, PAGE_FACTORIES에 등록

## UI 플로우

1. **Step 1:** 기존 문서 업로드 (단일 파일, FilePicker)
2. **Step 2:** 추가 자료 업로드 (복수 파일, FilePicker) + 텍스트 직접 입력 옵션
3. **Step 3:** 업데이트 지시사항 (TextEdit)
4. **옵션:** 업데이트 모드 (전체 재생성 / 부분 수정), 모델 선택
5. **실행:** 문서 업데이트 버튼
6. **결과:** MarkdownViewer로 미리보기 + 원본형식/Word/MD 저장 버튼

## 핵심 로직

### 지원 포맷 & 수정 전략

| 원본 포맷 | 수정 방식 | 라이브러리 |
|-----------|----------|----------|
| .docx | paragraph별 직접 수정 (Run 서식 보존) | python-docx |
| .pptx | slide/shape별 직접 수정 | python-pptx |
| .txt/.md | 전체 텍스트 교체 | 내장 |
| .pdf | 텍스트 추출 → Word로 변환 출력 | PyMuPDF + python-docx |

### AI 응답 형식 (JSON structured output)

```json
{
  "updated_paragraphs": [
    {"index": 3, "new_text": "업데이트된 텍스트..."}
  ],
  "new_paragraphs": [
    {"after_index": 10, "text": "새로 추가할 텍스트..."}
  ],
  "summary": "변경 사항 요약"
}
```

### 전체 재생성 모드
1. 원본 문서에서 구조화된 텍스트 추출 (index → text 매핑)
2. 추가 자료 파싱
3. AI에게 전체 업데이트 지시 → JSON 응답
4. paragraph별 텍스트 교체 (서식 보존)
5. 수정된 파일 저장

### 부분 수정 모드
1. 원본 문서에서 구조화된 텍스트 추출
2. 추가 자료 파싱
3. AI에게 변경 필요 부분만 식별 → JSON 응답 (수정할 paragraph만)
4. 해당 paragraph만 교체
5. 수정된 파일 저장

## 프롬프트 설계

### 시스템 프롬프트
- 문서 업데이트 전문가 역할
- 원본 구조/톤 유지 원칙
- JSON structured output 강제

### 전체 재생성 프롬프트
- 원본 문서 전체 구조 전달
- 추가 자료 + 지시사항 전달
- 모든 paragraph에 대한 업데이트 결과 JSON 반환

### 부분 수정 프롬프트
- 원본 문서 전체 구조 전달
- 추가 자료 + 지시사항 전달
- 변경 필요한 paragraph만 식별하여 JSON 반환

## 네비게이션 위치

`Independent Tools` 섹션에 "📄 문서 업데이트" 추가
