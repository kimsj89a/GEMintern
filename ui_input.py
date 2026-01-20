import streamlit as st
import utils
import core_logic
import core_rfi
import os
import tkinter as tk
from tkinter import filedialog

# 템플릿 상수 정의
TEMPLATES = {
    'simple_review': '1. 약식 투자검토 (요약)',
    'rfi': '2. RFI 작성 (실사 자료 요청)',
    'investment': '3. 투자심사보고서 (표준)',
    'im': '4. IM (투자제안서)',
    'management': '5. 사후관리보고서',
    'presentation': '6. 투자심의 발표자료 (PPT)',
    'custom': '7. 직접 입력 (서식 복제 가능)' # [수정]
}

def open_folder_dialog():
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        folder_path = filedialog.askdirectory(master=root)
        root.destroy()
        return folder_path
    except Exception as e:
        return None

def render_settings():
    """상단 설정 영역"""
    query_params = st.query_params
    cached_key = query_params.get("api_key", "")
    if isinstance(cached_key, list): cached_key = cached_key[0]

    with st.expander("⚙️ 설정 (SETTINGS)", expanded=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
        with c1:
            api_key = st.text_input("Google API Key", value=cached_key, type="password", placeholder="Enter Key...")
            save_to_url = st.checkbox("🔑 브라우저(URL)에 키 저장", value=bool(cached_key))
            if save_to_url and api_key: st.query_params["api_key"] = api_key
            elif not save_to_url and "api_key" in st.query_params: del st.query_params["api_key"]
            
        with c2:
            model_name = st.selectbox("사용할 모델", ["gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-pro"])
        with c3:
            thinking_level = st.selectbox("사고 수준", ["High (추론 깊이 극대화)", "Low (속도 우선)"])
        with c4:
            st.write(""); st.write("")
            use_diagram = st.checkbox("🎨 도식화 생성", value=False)
            
        st.info("💡 **Custom 모드**: 기존 보고서 파일을 업로드하고 '구조 추출'을 누르면, 해당 양식 그대로 새 내용을 작성합니다.")
    
    return {"api_key": api_key, "model_name": model_name, "thinking_level": "High" if "High" in thinking_level else "Low", "use_diagram": use_diagram}

def render_input_panel(container, settings):
    """왼쪽 입력 패널 UI"""
    with container:
        st.markdown("### 📝 입력 (Input)")

        # 1. 템플릿 선택
        template_option = st.selectbox("1. 문서 구조 / 템플릿 선택", list(TEMPLATES.keys()), format_func=lambda x: TEMPLATES[x])
        is_rfi = (template_option == 'rfi')
        
        rfi_existing = ""
        
        # 2. RFI 모드 전용 UI
        if is_rfi:
            st.markdown("##### 2. 최근 RFI 목록 (Basis)")
            uploaded_rfi_file = st.file_uploader("RFI 엑셀 파일 드래그 & 드롭", type=['xlsx', 'xls', 'csv'], key="rfi_basis")
            
            if uploaded_rfi_file:
                with st.spinner("RFI 파일 파싱 중..."):
                    rfi_existing = utils.parse_uploaded_file(uploaded_rfi_file)
                st.success(f"✅ RFI 로드 완료! ({uploaded_rfi_file.name})")
            else:
                st.info("파일이 없으면 빈 목록에서 시작합니다.")

        # 구조 추출 및 편집
        structure_text = ""
        if not is_rfi:
            # [수정] 라벨을 명확하게 변경
            upload_label = "📂 서식 파일 (양식 복제용)" if template_option == 'custom' else "📂 서식 파일 업로드 (구조 추출용)"
            uploaded_structure_file = st.file_uploader(upload_label, type=['pdf', 'docx', 'txt', 'md'])
            
            btn_label = "구조/양식 추출 실행" if template_option == 'custom' else "구조 추출 실행"
            if uploaded_structure_file and st.button(btn_label):
                if not settings["api_key"]: st.error("API Key 필요")
                else:
                    with st.spinner("서식 분석 중..."):
                        ext = core_logic.extract_structure(settings["api_key"], uploaded_structure_file)
                        if ext: st.session_state['structure_input'] = ext; st.rerun()

            default_structure = core_logic.get_default_structure(template_option)
            if 'structure_input' in st.session_state and template_option == 'custom':
                default_structure = st.session_state['structure_input']
                
            structure_text = st.text_area("문서 구조 (편집 가능)", value=default_structure, height=200)

        # 3. 데이터 입력
        uploaded_files = []
        rfi_file_list_input = ""

        if is_rfi:
            st.markdown("##### 3. 수령 자료 폴더 스캔 (Local Indexing)")
            
            col_path1, col_path2 = st.columns([3, 1])
            with col_path2:
                st.write(""); st.write("") 
                if st.button("📂 폴더 찾기", use_container_width=True):
                    selected_path = open_folder_dialog()
                    if selected_path:
                        st.session_state.local_path_input = selected_path.replace('/', '\\')
                        st.rerun()
            
            with col_path1:
                local_path = st.text_input("폴더 경로 (버튼을 눌러 선택하세요)", value=st.session_state.local_path_input, placeholder="C:\\Users\\...", key="path_input_box")
                st.session_state.local_path_input = local_path
            
            if st.session_state.local_path_input:
                with st.status("🔍 로컬 폴더 스캔 중...", expanded=True) as status:
                    index_result = core_rfi.index_local_directory(st.session_state.local_path_input)
                    if "Error" in index_result:
                        status.update(label="❌ 경로 오류", state="error"); st.error(index_result)
                    elif "없습니다" in index_result:
                        status.update(label="⚠️ 파일 없음", state="running"); st.warning(index_result)
                    else:
                        status.update(label="✅ 인덱싱 완료!", state="complete", expanded=False)
                rfi_file_list_input = st.text_area("스캔된 파일 목록", value=index_result, height=200)
            else:
                st.info("☝️ 오른쪽 '폴더 찾기' 버튼을 눌러 자료가 있는 폴더를 선택해주세요.")
                
        else:
            st.markdown("##### 2. 분석할 데이터 (내용 채우기용)")
            uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True, label_visibility="collapsed")
        
        # 4. 컨텍스트
        context_label = "3. 대상 기업 및 맥락" if not is_rfi else "4. 추가 질문 및 확인 사항"
        st.markdown(f"##### {context_label}")
        context_text = st.text_area("Context Input", height=100, label_visibility="collapsed", 
            placeholder="예: 기업명..." if not is_rfi else "예: 재고 관련 이슈 확인 필요...")

        st.markdown("---")
        generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary")

        return {
            "template_option": template_option,
            "structure_text": structure_text,
            "uploaded_files": uploaded_files,
            "rfi_file_list_input": rfi_file_list_input,
            "context_text": context_text,
            "rfi_existing": rfi_existing,
            "generate_btn": generate_btn
        }