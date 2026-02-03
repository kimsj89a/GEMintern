"""
문서양식 복사기 모듈
기존 문서 양식 업로드 -> 구조 추출 -> 사용자 입력 -> 새 문서 생성
"""
import streamlit as st
import io
import os
import json
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 기본 템플릿 경로
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template", "Normal.dotm")


def extract_document_structure(doc: Document) -> list:
    """Word 문서에서 구조 추출"""
    structure = []

    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue

        # 스타일 분석
        style_name = para.style.name if para.style else "Normal"

        # 헤더 레벨 판별
        if "Heading" in style_name:
            level = int(style_name.replace("Heading ", "")) if style_name != "Heading" else 1
            element_type = f"heading_{level}"
        elif para.runs and para.runs[0].bold:
            element_type = "bold_text"
        else:
            element_type = "paragraph"

        # 플레이스홀더 감지 ({{변수명}} 또는 [변수명] 패턴)
        import re
        placeholders = re.findall(r'\{\{(.+?)\}\}|\[(.+?)\]', text)
        placeholder_names = [p[0] or p[1] for p in placeholders]

        structure.append({
            "index": i,
            "type": element_type,
            "style": style_name,
            "original_text": text,
            "placeholders": placeholder_names,
            "editable": True,
            "include": True
        })

    # 테이블 추출
    for i, table in enumerate(doc.tables):
        table_data = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            table_data.append(row_data)

        structure.append({
            "index": f"table_{i}",
            "type": "table",
            "style": "Table",
            "original_text": f"[테이블 {i+1}] {len(table.rows)}행 x {len(table.columns)}열",
            "table_data": table_data,
            "placeholders": [],
            "editable": True,
            "include": True
        })

    return structure


def generate_document_from_structure(structure: list, inputs: dict, use_template: bool = True) -> bytes:
    """구조와 입력값을 바탕으로 새 문서 생성"""
    # 템플릿 사용 여부에 따라 Document 생성
    if use_template and os.path.exists(TEMPLATE_PATH):
        doc = Document(TEMPLATE_PATH)
        # 템플릿의 기존 내용 삭제 (스타일은 유지)
        for element in doc.element.body[:]:
            doc.element.body.remove(element)
    else:
        doc = Document()

    for item in structure:
        if not item.get("include", True):
            continue

        item_type = item["type"]

        if item_type == "table":
            # 테이블 생성
            table_data = item.get("table_data", [])
            if table_data:
                rows = len(table_data)
                cols = len(table_data[0]) if table_data else 1
                table = doc.add_table(rows=rows, cols=cols)
                table.style = 'Table Grid'

                for r_idx, row_data in enumerate(table_data):
                    for c_idx, cell_text in enumerate(row_data):
                        if c_idx < len(table.rows[r_idx].cells):
                            # 플레이스홀더 치환
                            final_text = replace_placeholders(cell_text, inputs)
                            table.rows[r_idx].cells[c_idx].text = final_text
                doc.add_paragraph()  # 테이블 후 빈 줄

        elif item_type.startswith("heading_"):
            level = int(item_type.split("_")[1])
            text = item.get("edited_text", item["original_text"])
            text = replace_placeholders(text, inputs)

            style_name = f"Heading {level}"
            try:
                p = doc.add_paragraph(text, style=style_name)
            except:
                p = doc.add_paragraph(text)
                if p.runs:
                    p.runs[0].bold = True

        elif item_type == "bold_text":
            text = item.get("edited_text", item["original_text"])
            text = replace_placeholders(text, inputs)
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True

        else:  # paragraph
            text = item.get("edited_text", item["original_text"])
            text = replace_placeholders(text, inputs)
            doc.add_paragraph(text)

    # BytesIO로 저장
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def replace_placeholders(text: str, inputs: dict) -> str:
    """플레이스홀더를 입력값으로 치환"""
    import re

    # {{변수명}} 패턴 치환
    for key, value in inputs.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
        text = text.replace(f"[{key}]", str(value))

    return text


def render_doctemplate_panel(settings):
    """문서양식 복사기 UI 패널"""
    st.markdown("### 📋 문서양식 복사기")

    st.markdown("""
        <div style='background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0068c9;'>
        <h4 style='margin-top: 0; color: #0068c9;'>📋 기능 안내</h4>
        <b>기존 문서 양식을 기반으로 새 문서를 생성합니다.</b><br/><br/>
        <b>사용 방법:</b><br/>
        1️⃣ 양식 문서(.docx) 업로드<br/>
        2️⃣ 추출된 구조 확인 및 편집<br/>
        3️⃣ 플레이스홀더에 내용 입력<br/>
        4️⃣ 새 문서 생성 및 다운로드<br/><br/>
        <b>플레이스홀더 사용법:</b> <code>{{변수명}}</code> 또는 <code>[변수명]</code> 형식으로 양식 문서에 작성
        </div>
    """, unsafe_allow_html=True)

    # 1단계: 양식 문서 업로드
    st.markdown("---")
    st.markdown("## 1️⃣ 양식 문서 업로드")

    uploaded_file = st.file_uploader(
        "Word 문서 업로드 (.docx)",
        type=['docx'],
        key="doctemplate_upload"
    )

    if uploaded_file:
        try:
            # 문서 로드
            doc = Document(io.BytesIO(uploaded_file.read()))
            st.success(f"✅ 파일 로드 완료: {uploaded_file.name}")

            # 구조 추출
            if 'doc_structure' not in st.session_state or st.session_state.get('doc_filename') != uploaded_file.name:
                structure = extract_document_structure(doc)
                st.session_state['doc_structure'] = structure
                st.session_state['doc_filename'] = uploaded_file.name

                # 플레이스홀더 수집
                all_placeholders = set()
                for item in structure:
                    all_placeholders.update(item.get("placeholders", []))
                st.session_state['doc_placeholders'] = list(all_placeholders)

            structure = st.session_state['doc_structure']
            placeholders = st.session_state.get('doc_placeholders', [])

            # 2단계: 구조 확인 및 편집
            st.markdown("---")
            st.markdown("## 2️⃣ 문서 구조 확인 및 편집")

            st.info(f"📊 추출된 요소: {len(structure)}개 | 플레이스홀더: {len(placeholders)}개")

            with st.expander("📄 문서 구조 편집", expanded=True):
                edited_structure = []

                for idx, item in enumerate(structure):
                    col1, col2, col3 = st.columns([0.5, 3, 1])

                    with col1:
                        include = st.checkbox(
                            "포함",
                            value=item.get("include", True),
                            key=f"include_{idx}",
                            label_visibility="collapsed"
                        )

                    with col2:
                        type_label = {
                            "heading_1": "📌 제목1",
                            "heading_2": "📎 제목2",
                            "heading_3": "📍 제목3",
                            "bold_text": "🔹 강조",
                            "paragraph": "📝 본문",
                            "table": "📊 테이블"
                        }.get(item["type"], "📝 기타")

                        if item["type"] == "table":
                            st.text(f"{type_label}: {item['original_text']}")
                            edited_text = item["original_text"]
                        else:
                            edited_text = st.text_input(
                                type_label,
                                value=item.get("edited_text", item["original_text"]),
                                key=f"edit_{idx}",
                                label_visibility="collapsed"
                            )

                    with col3:
                        st.caption(item["type"])

                    edited_item = item.copy()
                    edited_item["include"] = include
                    edited_item["edited_text"] = edited_text
                    edited_structure.append(edited_item)

                st.session_state['doc_structure'] = edited_structure

            # 3단계: 플레이스홀더 입력
            if placeholders:
                st.markdown("---")
                st.markdown("## 3️⃣ 플레이스홀더 입력")

                st.markdown("문서에서 감지된 플레이스홀더에 값을 입력하세요.")

                inputs = {}
                cols = st.columns(2)
                for i, ph in enumerate(placeholders):
                    with cols[i % 2]:
                        inputs[ph] = st.text_area(
                            f"📝 {ph}",
                            height=100,
                            key=f"placeholder_{ph}",
                            placeholder=f"{ph}에 들어갈 내용을 입력하세요..."
                        )

                st.session_state['doc_inputs'] = inputs
            else:
                st.session_state['doc_inputs'] = {}

            # 4단계: 문서 생성
            st.markdown("---")
            st.markdown("## 4️⃣ 새 문서 생성")

            col1, col2 = st.columns(2)
            with col1:
                output_filename = st.text_input(
                    "출력 파일명",
                    value=f"new_{uploaded_file.name.replace('.docx', '')}",
                    key="doctemplate_output_filename"
                )
            with col2:
                template_exists = os.path.exists(TEMPLATE_PATH)
                use_template = st.checkbox(
                    "기본 템플릿 스타일 적용",
                    value=template_exists,
                    disabled=not template_exists,
                    key="doctemplate_use_template"
                )

            if st.button("🚀 문서 생성", type="primary", use_container_width=True, key="btn_generate_doc"):
                with st.spinner("문서 생성 중..."):
                    try:
                        final_structure = st.session_state.get('doc_structure', [])
                        final_inputs = st.session_state.get('doc_inputs', {})

                        docx_bytes = generate_document_from_structure(
                            final_structure,
                            final_inputs,
                            use_template=use_template
                        )

                        st.session_state['doctemplate_result'] = docx_bytes
                        st.session_state['doctemplate_filename'] = output_filename
                        st.success("✅ 문서 생성 완료!")
                    except Exception as e:
                        st.error(f"문서 생성 중 오류: {e}")

            # 다운로드 버튼
            if st.session_state.get('doctemplate_result'):
                filename = st.session_state.get('doctemplate_filename', 'output')
                st.download_button(
                    "📥 문서 다운로드",
                    st.session_state['doctemplate_result'],
                    f"{filename}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary",
                    key="btn_download_doctemplate"
                )

        except Exception as e:
            st.error(f"파일 처리 중 오류: {e}")
    else:
        st.info("양식 문서(.docx)를 업로드하면 구조가 추출됩니다.")

        # 예시 설명
        with st.expander("💡 양식 문서 작성 팁"):
            st.markdown("""
            **플레이스홀더 작성 방법:**
            ```
            보고서 제목: {{제목}}
            작성자: {{작성자}}
            작성일: {{날짜}}

            1. 개요
            {{개요_내용}}

            2. 본문
            {{본문_내용}}
            ```

            **지원되는 요소:**
            - 제목 스타일 (Heading 1~6)
            - 본문 텍스트
            - 굵은 텍스트
            - 테이블
            """)
