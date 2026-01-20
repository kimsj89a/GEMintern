import streamlit as st
import streamlit.components.v1 as components
import utils
import core_logic
import core_rfi

# 템플릿 상수 정의
TEMPLATES = {
    'simple_review': '1. 약식 투자검토 (요약)',
    'rfi': '2. RFI 작성 (실사 자료 요청)',
    'investment': '3. 투자심사보고서 (표준)',
    'im': '4. IM (투자제안서)',
    'management': '5. 사후관리보고서',
    'presentation': '6. 투자심의 발표자료 (PPT)',
    'custom': '7. 직접 입력 (서식 복제 가능)'
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
            "generate_btn": generate_btn
        }