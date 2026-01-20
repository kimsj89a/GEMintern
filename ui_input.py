import streamlit as st
import streamlit.components.v1 as components
import utils
import core_logic

# 템플릿 상수 정의
TEMPLATES = {
    'simple_review': '1. 약식 투자검토 (요약)',
    'rfi': '2. RFI 작성 (실사 자료 요청)',
    'investment': '3. 투자심사보고서 (표준)',
    'im': '4. IM (투자제안서)',
    'management': '5. 사후관리보고서',
    'presentation': '6. 투자심의 발표자료 (PPT)',
    'custom': '7. 직접 입력 (자동 구조화)'
}

# [HTML/JS] 로컬 파일명 추출기 (서버 업로드 X)
HTML_DROPZONE = """
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; }
  #drop-zone { 
    border: 2px dashed #cbd5e1; border-radius: 8px; padding: 30px 20px; 
    text-align: center; color: #64748b; cursor: pointer; transition: all 0.2s; background: #f8fafc; 
  }
  #drop-zone.dragover { border-color: #3b82f6; background: #eff6ff; color: #3b82f6; }
  #file-list { 
    width: 95%; height: 120px; margin-top: 15px; padding: 10px; 
    border: 1px solid #e2e8f0; border-radius: 4px; font-family: monospace; font-size: 12px; resize: none; 
    background-color: #ffffff; color: #334155;
  }
  button { 
    margin-top: 10px; background: #3b82f6; color: white; border: none; padding: 10px 20px; 
    border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%; font-size: 14px;
    transition: background 0.2s;
  }
  button:hover { background: #2563eb; }
  .icon { font-size: 24px; margin-bottom: 10px; display: block; }
</style>
</head>
<body>
<div id="drop-zone">
  <span class="icon">📂</span>
  <div style="font-weight:600; font-size:15px; margin-bottom:4px;">자료 폴더/파일을 이곳에 드래그하세요</div>
  <div style="font-size:12px; color:#94a3b8;">(서버 업로드 없이 브라우저에서 파일명만 즉시 추출합니다)</div>
</div>
<textarea id="file-list" placeholder="여기에 추출된 파일 목록이 표시됩니다." readonly></textarea>
<button id="copy-btn" onclick="copyToClipboard()">📋 목록 복사하기 (Copy List)</button>

<script>
  const dropZone = document.getElementById('drop-zone');
  const fileList = document.getElementById('file-list');
  const copyBtn = document.getElementById('copy-btn');

  // 드래그 이벤트 처리
  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    let names = [];
    
    if (files.length > 0) {
        for(let i=0; i<files.length; i++) {
          names.push("- " + files[i].name);
        }
        fileList.value = names.join('\\n');
        copyBtn.innerText = `📋 ${files.length}개 파일명 복사하기`;
        copyBtn.style.background = "#3b82f6";
    }
  });

  // 복사 기능
  function copyToClipboard() {
    if (!fileList.value) return;
    fileList.select();
    document.execCommand('copy');
    copyBtn.innerText = "✅ 복사 완료! 아래 '파일명 붙여넣기'란에 붙여넣으세요.";
    copyBtn.style.background = "#22c55e";
  }
</script>
</body>
</html>
"""

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
            
        st.info("💡 **RFI 모드**: 대용량 파일도 'HTML 드롭존'을 통해 즉시 인덱싱할 수 있습니다. (업로드 시간 0초)")
    
    return {"api_key": api_key, "model_name": model_name, "thinking_level": "High" if "High" in thinking_level else "Low", "use_diagram": use_diagram}

def render_input_panel(container, settings):
    """왼쪽 입력 패널 UI"""
    with container:
        st.markdown("### 📝 입력 (Input)")
        
        # 1. 템플릿 선택
        template_option = st.selectbox("문서 구조 / 템플릿 선택", list(TEMPLATES.keys()), format_func=lambda x: TEMPLATES[x], label_visibility="collapsed")
        
        # RFI 모드 여부
        is_rfi = (template_option == 'rfi')

        # 구조 추출 (RFI 아닐 때만)
        if not is_rfi:
            uploaded_structure_file = st.file_uploader("📂 서식 파일 업로드 (구조 추출용)", type=['pdf', 'docx', 'txt', 'md'])
            if uploaded_structure_file and st.button("구조 추출 실행"):
                if not settings["api_key"]: st.error("API Key 필요")
                else:
                    with st.spinner("구조 분석 중..."):
                        ext = core_logic.extract_structure(settings["api_key"], uploaded_structure_file)
                        if ext: st.session_state['structure_input'] = ext; st.rerun()

        default_structure = core_logic.get_default_structure(template_option)
        if 'structure_input' in st.session_state and template_option == 'custom':
            default_structure = st.session_state['structure_input']
            
        structure_text = st.text_area(
            "문서 구조 편집" if not is_rfi else "문서 구조 (자동 설정)", 
            value=default_structure, height=200 if not is_rfi else 50, disabled=is_rfi
        )

        # 2. 데이터 업로드 (RFI vs 일반 모드 분기)
        uploaded_files = []
        rfi_file_list_input = ""

        if is_rfi:
            st.markdown("##### 2. 수령한 전체 자료 (HTML Fast Scan)")
            # [HTML 드롭존]
            components.html(HTML_DROPZONE, height=320)
            
            # [파일명 붙여넣기 영역]
            st.markdown("⬇️ **위에서 복사한 목록을 아래에 붙여넣으세요:**")
            rfi_file_list_input = st.text_area("파일명 목록 붙여넣기", height=150, placeholder="- 2024_재무제표.xlsx\n- 2025_사업계획서.pdf\n...")
        else:
            st.markdown("##### 2. 분석할 데이터 (Raw Data)")
            uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True, label_visibility="collapsed")
        
        # 3. 컨텍스트
        context_label = "3. 대상 기업 및 맥락" if not is_rfi else "3. 추가 질문 및 확인 사항"
        st.markdown(f"##### {context_label}")
        context_text = st.text_area("Context Input", height=100, label_visibility="collapsed", 
            placeholder="예: 기업명, 핵심 제품..." if not is_rfi else "예: 재고가 너무 많은 것 같은데 확인 필요...")

        # RFI 전용
        rfi_existing = ""
        if is_rfi:
            st.markdown("##### 5. 기존 RFI 목록 (선택)")
            rfi_existing = st.text_area("기존 목록 붙여넣기", height=100)

        st.markdown("---")
        generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary")

        return {
            "template_option": template_option,
            "structure_text": structure_text,
            "uploaded_files": uploaded_files, # 일반 모드용
            "rfi_file_list_input": rfi_file_list_input, # RFI 모드용 (텍스트)
            "context_text": context_text,
            "rfi_existing": rfi_existing,
            "generate_btn": generate_btn
        }