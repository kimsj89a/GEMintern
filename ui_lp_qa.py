import streamlit as st
import pandas as pd
import io
import core_rag
import core_logic
import utils
import utils_markdown

def render_lp_qa_panel(settings):
    st.markdown("### 🙋‍♂️ LP Q&A 대응")
    st.caption("LP(출자자)의 질의사항을 프로젝트 문서 기반으로 답변합니다.")

    # 1. Project Selection
    current_project = st.session_state.get("current_project", "")
    if not current_project:
        st.warning("먼저 사이드바에서 프로젝트를 선택해주세요.")
        return

    st.success(f"현재 프로젝트: **{current_project}** (RAG 활성화됨)")

    # 2. Input Method
    tab1, tab2 = st.tabs(["📝 직접 입력", "📂 엑셀 업로드"])
    
    questions = []
    
    with tab1:
        q_text = st.text_area("질문 입력 (한 줄에 하나씩)", height=150, placeholder="1. 펀드 만기 연장 가능성?\n2. 핵심 운용인력 현황?\n3. 최근 3년 수익률 추이?")
        if q_text:
            questions = [q.strip() for q in q_text.split('\n') if q.strip()]

    with tab2:
        uploaded_file = st.file_uploader("질문 리스트 업로드 (Excel)", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                # Try to find a column that looks like questions
                possible_cols = [c for c in df.columns if "질문" in str(c) or "question" in str(c).lower() or "Q" in str(c)]
                target_col = possible_cols[0] if possible_cols else df.columns[0]
                st.info(f"'{target_col}' 컬럼을 질문으로 인식합니다.")
                questions = df[target_col].dropna().astype(str).tolist()
            except Exception as e:
                st.error(f"엑셀 읽기 오류: {e}")

    # 3. Generate Answers
    if questions:
        st.markdown(f"##### 총 {len(questions)}개의 질문이 식별되었습니다.")
        
        if st.button("🚀 답변 생성 시작", type="primary", use_container_width=True):
            api_key = settings.get("api_key")
            if not api_key:
                st.error("API Key가 설정되지 않았습니다.")
                return

            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Load RAG Context once
            rag_context = core_rag.load_all_project_docs(current_project)
            
            for i, q in enumerate(questions):
                status_text.text(f"답변 생성 중 ({i+1}/{len(questions)}): {q[:30]}...")
                
                try:
                    # Simple RAG-based answer generation
                    answer = core_logic.generate_qa_answer(
                        api_key, 
                        settings.get("model_name"), 
                        rag_context, # Use RAG context as file context
                        q,
                        rag_context="" # Already passed in file_context
                    )
                    results.append({"Question": q, "Answer": answer})
                except Exception as e:
                    results.append({"Question": q, "Answer": f"Error: {str(e)}"})
                
                progress_bar.progress((i + 1) / len(questions))
            
            status_text.text("완료!")
            st.session_state["lp_qa_results"] = results
            
    # 4. Display & Export Results
    if "lp_qa_results" in st.session_state:
        results = st.session_state["lp_qa_results"]

        st.markdown("### ✅ 답변 생성 결과")

        # Display each Q&A with markdown rendering and export options
        for i, result in enumerate(results, 1):
            with st.container():
                st.markdown(f"#### Q{i}: {result['Question']}")

                # Render answer as markdown
                st.markdown(result['Answer'])

                # Action buttons for each Q&A
                col1, col2, col3 = st.columns([1, 1, 4])

                with col1:
                    # Copy button (copies answer to clipboard)
                    if st.button(f"📋 복사", key=f"copy_{i}"):
                        st.code(result['Answer'], language=None)
                        st.success("답변이 표시되었습니다. 복사하세요.")

                with col2:
                    # Individual Word export
                    md_content = f"# Q: {result['Question']}\n\n{result['Answer']}"
                    docx_bytes = utils_markdown.markdown_to_docx(md_content, use_template=True)
                    st.download_button(
                        label="📄 Word",
                        data=docx_bytes,
                        file_name=f"qa_{i}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"word_{i}"
                    )

                st.markdown("---")

        # Batch export options
        st.markdown("### 📥 전체 내보내기")
        col1, col2, col3 = st.columns([1, 1, 4])

        with col1:
            # Excel Export
            df_results = pd.DataFrame(results)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_results.to_excel(writer, index=False, sheet_name='Sheet1')
                worksheet = writer.sheets['Sheet1']
                worksheet.set_column('A:A', 40)
                worksheet.set_column('B:B', 60)

            output.seek(0)
            st.download_button(
                label="📥 Excel 다운로드",
                data=output,
                file_name="LP_QA_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            # Word Export (All Q&A)
            all_md_content = "# LP Q&A 답변 모음\n\n"
            for i, r in enumerate(results, 1):
                all_md_content += f"## Q{i}: {r['Question']}\n\n"
                all_md_content += f"{r['Answer']}\n\n"
                all_md_content += "---\n\n"

            all_docx_bytes = utils_markdown.markdown_to_docx(all_md_content, use_template=True)
            st.download_button(
                label="📄 Word 다운로드 (전체)",
                data=all_docx_bytes,
                file_name="LP_QA_All.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
