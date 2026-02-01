import streamlit as st
import streamlit.components.v1 as components
import os
from dotenv import load_dotenv
import utils
import core_logic
import core_rfi

# .env 파일 로드
load_dotenv()

# 템플릿 상수 정의
TEMPLATES = {
    'simple_review': '1. 약식 투자검토 (요약)',
    'rfi': '2. RFI 작성 (실사 자료 요청)',
    'investment': '3. 투자심사보고서 (표준)',
    'im': '4. IM (투자제안서)',
    'management': '5. 사후관리보고서',
    'presentation': '6. 투자심의 발표자료 (PPT)',
    'custom': '7. 자유 구조화 (요약보고서)'
}

# [HTML/JS] 브라우저 기반 폴더 스캐너 (서버 업로드 X)
HTML_SCANNER = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { margin: 0; padding: 0; font-family: sans-serif; }
  #drop-zone { 
    border: 2px dashed #cbd5e1; border-radius: 8px; padding: 20px; 
    text-align: center; color: #64748b; cursor: pointer; background: #f8fafc; transition: 0.2s;
  }
  #drop-zone.dragover { border-color: #3b82f6; background: #eff6ff; color: #3b82f6; }
  #file-display {
    width: 96%; height: 100px; margin-top: 10px; padding: 8px; font-size: 11px;
    border: 1px solid #e2e8f0; border-radius: 4px; color: #334155; font-family: monospace;
  }
  button {
    margin-top: 8px; width: 100%; padding: 8px; background: #3b82f6; color: white; border: none;
    border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px;
  }
  button:hover { background: #2563eb; }
</style>
</head>
<body>
<div id="drop-zone">
  <div style="font-size: 20px;">📂</div>
  <div style="font-weight: 600; font-size: 14px;">여기에 자료 폴더를 드래그하세요</div>
  <div style="font-size: 11px; color: #94a3b8; margin-top:2px;">(하위 폴더 포함 전체 스캔 / 업로드 없음)</div>
</div>
<textarea id="file-display" placeholder="스캔 결과가 여기에 나타납니다." readonly></textarea>
<button id="copy-btn" onclick="copyList()">📋 목록 복사 (Click to Copy)</button>

<script>
  const dropZone = document.getElementById('drop-zone');
  const fileDisplay = document.getElementById('file-display');
  const copyBtn = document.getElementById('copy-btn');
  let foundFiles = [];

  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
  
  dropZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    copyBtn.innerText = "🔍 스캔 중...";
    
    foundFiles = [];
    const items = e.dataTransfer.items;
    
    if (items) {
        const promises = [];
        for (let i = 0; i < items.length; i++) {
            const item = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : items[i].getAsEntry();
            if (item) promises.push(scanEntry(item));
        }
        await Promise.all(promises);
    }
    
    foundFiles.sort();
    fileDisplay.value = foundFiles.join('\\n');
    copyBtn.innerText = `📋 ${foundFiles.length}개 파일 목록 복사하기`;
    copyBtn.style.background = "#3b82f6";
  });

  function scanEntry(entry) {
    return new Promise((resolve) => {
        if (entry.isFile) {
            const path = entry.fullPath.startsWith('/') ? entry.fullPath.slice(1) : entry.fullPath;
            foundFiles.push("- " + path);
            resolve();
        } else if (entry.isDirectory) {
            const dirReader = entry.createReader();
            const readAll = async () => {
                let allEntries = [];
                let keepReading = true;
                while (keepReading) {
                    const batch = await new Promise(r => dirReader.readEntries(r));
                    if (batch.length === 0) keepReading = false;
                    else allEntries = allEntries.concat(batch);
                }
                await Promise.all(allEntries.map(scanEntry));
                resolve();
            };
            readAll();
        } else resolve();
    });
  }

  function copyList() {
    if (!fileDisplay.value) return;
    fileDisplay.select();
    document.execCommand('copy');
    copyBtn.innerText = "✅ 복사 완료! 아래 빈칸에 붙여넣으세요.";
    copyBtn.style.background = "#22c55e";
  }
</script>
</body>
</html>
"""

def render_settings():
    """상단 설정 영역"""
    query_params = st.query_params
    # .env 또는 URL 파라미터에서 API 키 로드
    env_key = os.getenv("GOOGLE_API_KEY", "")
    cached_key = query_params.get("api_key", "") or env_key
    if isinstance(cached_key, list): cached_key = cached_key[0]

    with st.expander("⚙️ 설정 (SETTINGS)", expanded=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
        with c1:
            api_key = st.text_input("Google API Key", value=cached_key, type="password", placeholder="Enter Key...")
            save_to_url = st.checkbox("🔐 브라우저(URL)에 키 저장", value=bool(cached_key))
            if save_to_url and api_key: st.query_params["api_key"] = api_key
            elif not save_to_url and "api_key" in st.query_params: del st.query_params["api_key"]

        with c2:
            model_name = st.selectbox("사용할 모델", ["gemini-3-pro-preview", "gemini-3-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-pro"])
        with c3:
            thinking_level = st.selectbox("사고 수준", ["High (추론 깊이 극대화)", "Low (속도 우선)"])
        with c4:
            st.write(""); st.write("")
            use_diagram = st.checkbox("🎨 도식화 생성", value=False)

        # OCR 상태 표시
        ocr_available, ocr_msg = utils.get_ocr_status()
        if ocr_available:
            st.info("🔍 PDF OCR: Gemini Vision 사용 (스캔 PDF 자동 인식)")
        else:
            st.warning(f"🔍 PDF OCR: 비활성화 - {ocr_msg}")

        # Document AI 설정 (고급)
        st.markdown("---")

        # .env에서 Document AI 기본값 로드
        env_docai_project = os.getenv("GCP_PROJECT_ID", "")
        env_docai_location = os.getenv("DOCAI_LOCATION", "us")
        env_docai_processor = os.getenv("DOCAI_PROCESSOR_ID", "")
        env_docai_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

        # .env 설정이 있으면 기본 활성화
        has_env_docai = bool(env_docai_project and env_docai_processor and env_docai_creds_path)
        use_docai = st.checkbox("🔬 Document AI OCR 사용 (고품질 PDF/이미지 OCR)", value=has_env_docai)

        docai_config = None
        if use_docai:
            # .env에서 credentials JSON 자동 로드
            env_creds_json = None
            if env_docai_creds_path:
                creds_full_path = env_docai_creds_path
                if not os.path.isabs(creds_full_path):
                    creds_full_path = os.path.join(os.path.dirname(__file__), creds_full_path)
                if os.path.exists(creds_full_path):
                    with open(creds_full_path, 'r') as f:
                        env_creds_json = f.read()

            if has_env_docai and env_creds_json:
                st.success(f"✅ .env에서 Document AI 설정 로드됨 (프로젝트: {env_docai_project})")
                docai_config = {
                    'project_id': env_docai_project,
                    'location': env_docai_location,
                    'processor_id': env_docai_processor,
                    'credentials_json': env_creds_json
                }
            else:
                dc1, dc2 = st.columns(2)
                with dc1:
                    docai_project_id = st.text_input("GCP 프로젝트 ID", value=env_docai_project, key="docai_project")
                    loc_idx = 0 if env_docai_location == "us" else 1
                    docai_location = st.selectbox("위치", ["us", "eu"], index=loc_idx, key="docai_location")
                with dc2:
                    docai_processor_id = st.text_input("프로세서 ID", value=env_docai_processor, key="docai_processor")
                    docai_creds_file = st.file_uploader("서비스 계정 JSON", type=['json'], key="docai_creds")

                docai_creds_json = env_creds_json
                if docai_creds_file:
                    docai_creds_json = docai_creds_file.read().decode('utf-8')
                    docai_creds_file.seek(0)

                if docai_project_id and docai_processor_id and docai_creds_json:
                    docai_config = {
                        'project_id': docai_project_id,
                        'location': docai_location,
                        'processor_id': docai_processor_id,
                        'credentials_json': docai_creds_json
                    }
                    st.success("✅ Document AI 설정 완료")
                else:
                    st.warning("⚠️ Document AI 사용을 위해 모든 필드를 입력해주세요")

    return {
        "api_key": api_key,
        "model_name": model_name,
        "thinking_level": "High" if "High" in thinking_level else "Low",
        "use_diagram": use_diagram,
        "docai_config": docai_config
    }

def _on_template_change(template_key, struct_key, custom_input_key=None):
    """템플릿 변경 시 구조 텍스트 강제 업데이트 콜백"""
    if template_key not in st.session_state: return
    
    selected_template = st.session_state[template_key]
    new_text = core_logic.get_default_structure(selected_template)
    
    if selected_template == 'custom' and custom_input_key and custom_input_key in st.session_state:
        new_text = st.session_state[custom_input_key]
        
    st.session_state[struct_key] = new_text

def render_investment_report_panel(container, settings):
    """투자분석 보고서 입력 패널 (약식, 투자심사, 직접입력)"""
    with container:
        # 1. 템플릿 선택
        template_options = {
            'simple_review': '1. 약식 투자검토 (요약)',
            'investment': '2. 투자심사보고서 (표준)',
            'custom': '3. 자유 구조화 (요약보고서)'
        }
        template_option = st.selectbox(
            "1. 문서 구조 / 템플릿 선택",
            list(template_options.keys()),
            format_func=lambda x: template_options[x],
            key="report_template",
            on_change=_on_template_change,
            args=("report_template", "report_struct_text", "report_structure_input")
        )

        # 2. 구조 추출 및 편집
        upload_label = "📂 서식 파일 (양식 복제용)" if template_option == 'custom' else "📂 서식 파일 업로드 (구조 추출용)"
        uploaded_structure_file = st.file_uploader(upload_label, type=['pdf', 'docx', 'txt', 'md'], key="report_structure")

        btn_label = "구조/양식 추출 실행" if template_option == 'custom' else "구조 추출 실행"
        if uploaded_structure_file and st.button(btn_label, key="report_extract"):
            if not settings["api_key"]:
                st.error("API Key 필요")
            else:
                with st.spinner("서식 분석 중..."):
                    ext = core_logic.extract_structure(settings["api_key"], uploaded_structure_file)
                    if ext:
                        st.session_state['report_structure_input'] = ext
                        st.rerun()

        default_structure = core_logic.get_default_structure(template_option)
        if 'report_structure_input' in st.session_state and template_option == 'custom':
            default_structure = st.session_state['report_structure_input']

        structure_text = st.text_area("문서 구조 (편집 가능)", value=default_structure, height=200, key="report_struct_text")

        # 3. 데이터 입력
        st.markdown("##### 2. 분석할 데이터 (내용 채우기용)")
        uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True, label_visibility="collapsed", key="report_files")

        # [NEW] Saved Documents (RAG)
        saved_docs = utils.list_saved_docs()
        selected_saved_files = []
        if saved_docs:
            with st.expander("📚 저장된 문서 불러오기 (Local Library)", expanded=False):
                selected_saved_files = st.multiselect(
                    "이전에 변환된 문서 선택", 
                    saved_docs,
                    key="report_saved_files",
                    placeholder="저장된 문서 선택..."
                )

        # 4. 컨텍스트
        st.markdown("##### 3. 대상 기업 및 맥락")
        context_text = st.text_area("Context Input", height=100, label_visibility="collapsed", placeholder="예: 기업명, 투자 배경 등...", key="report_context")

        # 5. 생성 모드 선택 (chained 지원 템플릿)
        generation_mode = "single"
        if template_option in ['investment', 'simple_review']:
            part_count = 5 if template_option == 'investment' else 3
            st.markdown("##### 4. 생성 방식")
            generation_mode = st.radio(
                "생성 방식 선택",
                ["chained", "single"],
                format_func=lambda x: f"📊 {part_count}단계 분할 생성 (품질 우선)" if x == "chained" else "🚀 한 번에 생성 (빠름)",
                index=0,
                horizontal=True,
                help="분할 생성 시 각 섹션이 더 상세하게 작성됩니다.",
                label_visibility="collapsed",
                key="report_gen_mode"
            )

        st.markdown("---")
        generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary", key="report_generate")

        return {
            "template_option": template_option,
            "structure_text": structure_text,
            "uploaded_files": uploaded_files,
            "rfi_file_list_input": "",
            "context_text": context_text,
            "rfi_existing": "",
            "generate_btn": generate_btn,
            "generation_mode": generation_mode,
            "selected_saved_files": selected_saved_files
        }

def render_rfi_panel(container, settings):
    """RFI 작성 입력 패널"""
    with container:
        template_option = 'rfi'

        # 1. 최근 RFI 목록 (Basis)
        st.markdown("##### 1. 최근 RFI 목록 (Basis)")
        uploaded_rfi_file = st.file_uploader("RFI 엑셀 파일 드래그 & 드롭", type=['xlsx', 'xls', 'csv'], key="rfi_basis")

        rfi_existing = ""
        if uploaded_rfi_file:
            with st.spinner("RFI 파일 파싱 중..."):
                rfi_existing = utils.parse_uploaded_file(uploaded_rfi_file)
            st.success(f"✅ RFI 로드 완료! ({uploaded_rfi_file.name})")
        else:
            st.info("파일이 없으면 빈 목록에서 시작합니다.")

        # 2. 수령 자료 폴더 스캔
        st.markdown("##### 2. 수령 자료 폴더 스캔")
        st.markdown("""
        <div class="info-box">
        <b>☁️ 클라우드/웹 환경 안내</b><br/>
        웹 서버는 사용자의 PC(C:드라이브)를 직접 볼 수 없습니다. <br/>
        아래 <b>드롭존에 폴더를 드래그</b>하면 브라우저가 파일명을 스캔해줍니다. <b>[복사]</b> 후 아래 칸에 <b>[붙여넣기]</b> 해주세요.
        </div>
        """, unsafe_allow_html=True)

        # HTML 스캐너
        components.html(HTML_SCANNER, height=280)

        # 결과 입력창
        rfi_file_list_input = st.text_area("⬇️ 파일 목록 붙여넣기 (Ctrl+V)", height=150, placeholder="- 폴더명/파일명.pdf...", key="rfi_filelist")

        # 3. 자료 내용 분석 (선택사항)
        st.markdown("##### 3. 자료 내용 분석 (선택사항)")
        uploaded_files = st.file_uploader("내용을 분석할 파일 업로드 (PDF, Word 등)", accept_multiple_files=True, key="rfi_content_files")

        # 4. 추가 질문 및 확인 사항
        st.markdown("##### 4. 추가 질문 및 확인 사항")
        context_text = st.text_area("Context Input", height=100, label_visibility="collapsed", placeholder="예: 재고 관련 이슈 확인 필요...", key="rfi_context")

        st.markdown("---")
        generate_btn = st.button("🚀 RFI 생성 시작", use_container_width=True, type="primary", key="rfi_generate")

        return {
            "template_option": template_option,
            "structure_text": "",
            "uploaded_files": uploaded_files,
            "rfi_file_list_input": rfi_file_list_input,
            "context_text": context_text,
            "rfi_existing": rfi_existing,
            "generate_btn": generate_btn,
            "generation_mode": "single",
            "selected_saved_files": selected_saved_files
        }

def render_im_ppt_panel(container, settings):
    """IM/PPT 생성 입력 패널"""
    with container:
        # 1. 템플릿 선택
        template_options = {
            'im': '1. IM (투자제안서)',
            'presentation': '2. 투자심의 발표자료 (PPT)',
            'free_summary': '3. 자유 구조화 (요약)'
        }
        template_option = st.selectbox(
            "1. 문서 구조 / 템플릿 선택",
            list(template_options.keys()),
            format_func=lambda x: template_options[x],
            key="im_template",
            on_change=_on_template_change,
            args=("im_template", "im_struct_text", "im_structure_input")
        )

        # 2. 구조 추출 및 편집 (선택)
        uploaded_structure_file = st.file_uploader("📂 서식 파일 업로드 (구조 추출용)", type=['pdf', 'docx', 'txt', 'md'], key="im_structure")

        if uploaded_structure_file and st.button("구조 추출 실행", key="im_extract"):
            if not settings["api_key"]:
                st.error("API Key 필요")
            else:
                with st.spinner("서식 분석 중..."):
                    ext = core_logic.extract_structure(settings["api_key"], uploaded_structure_file)
                    if ext:
                        st.session_state['im_structure_input'] = ext
                        st.rerun()

        default_structure = core_logic.get_default_structure(template_option)
        if 'im_structure_input' in st.session_state:
            default_structure = st.session_state['im_structure_input']

        structure_text = st.text_area("문서 구조 (편집 가능)", value=default_structure, height=200, key="im_struct_text")

        # 3. 데이터 입력
        st.markdown("##### 2. 분석할 데이터 (내용 채우기용)")
        uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True, label_visibility="collapsed", key="im_files")

        # [NEW] Saved Documents (RAG)
        saved_docs = utils.list_saved_docs()
        selected_saved_files = []
        if saved_docs:
            with st.expander("📚 저장된 문서 불러오기 (Local Library)", expanded=False):
                selected_saved_files = st.multiselect(
                    "이전에 변환된 문서 선택", 
                    saved_docs,
                    key="im_saved_files",
                    placeholder="저장된 문서 선택..."
                )

        # 4. 컨텍스트
        st.markdown("##### 3. 대상 기업 및 맥락")
        context_text = st.text_area("Context Input", height=100, label_visibility="collapsed", placeholder="예: 기업명, 투자 배경 등...", key="im_context")

        st.markdown("---")
        generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary", key="im_generate")

        return {
            "template_option": template_option,
            "structure_text": structure_text,
            "uploaded_files": uploaded_files,
            "rfi_file_list_input": "",
            "context_text": context_text,
            "rfi_existing": "",
            "generate_btn": generate_btn,
            "generation_mode": "single",
            "selected_saved_files": selected_saved_files
        }

def render_input_panel(container, settings):
    """레거시 호환용 - 기본적으로 투자분석 보고서 패널 호출"""
    return render_investment_report_panel(container, settings)

# 아래는 기존 코드 (삭제하지 말 것)
def _legacy_render_input_panel(container, settings):
    """왼쪽 입력 패널 UI (레거시)"""
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
            st.markdown("##### 3. 수령 자료 폴더 스캔")
            # 안내 문구
            st.markdown("""
            <div class="info-box">
            <b>☁️ 클라우드/웹 환경 안내</b><br/>
            웹 서버는 사용자의 PC(C:드라이브)를 직접 볼 수 없습니다. <br/>
            아래 <b>드롭존에 폴더를 드래그</b>하면 브라우저가 파일명을 스캔해줍니다. <b>[복사]</b> 후 아래 칸에 <b>[붙여넣기]</b> 해주세요.
            </div>
            """, unsafe_allow_html=True)
            
            # HTML 스캐너
            components.html(HTML_SCANNER, height=280)
            
            # 결과 입력창
            rfi_file_list_input = st.text_area("⬇️ 파일 목록 붙여넣기 (Ctrl+V)", height=150, placeholder="- 폴더명/파일명.pdf...")
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
            "generate_btn": generate_btn,
            "generation_mode": "single"
        }