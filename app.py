import streamlit as st
import ui_input
import ui_output
import ui_audio
import ui_crawler
import ui_ocr
import ui_markdown
import ui_doctemplate

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v6.0", page_icon="💎")

# --- CSS 스타일 적용 ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .title-container { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
    .badge { background-color: #f0f2f6; color: #31333F; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; border: 1px solid #d6d6d8; }
    .badge-blue { background-color: #e6f0ff; color: #0068c9; border: 1px solid #b3d1ff; }
    .info-box { background-color: #fff8c5; padding: 10px; border-radius: 5px; border: 1px solid #e3d5a5; font-size: 0.85rem; color: #5c4b12; margin-bottom: 15px; }
    p, li, div { word-break: keep-all; overflow-wrap: break-word; }
    
    /* 사이드바 네비게이션 버튼 스타일 (Gemini-like) */
    section[data-testid="stSidebar"] .stButton button {
        text-align: left;
        padding-left: 20px;
        border: none;
        background-color: transparent;
        font-size: 1.05rem;
        justify-content: flex-start;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: #f0f2f6;
        color: #0068c9;
    }
    /* 활성화된 버튼 스타일 */
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #e6f0ff;
        color: #0068c9;
        font-weight: 600;
        border-left: 4px solid #0068c9;
        border-radius: 0 4px 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 상태 초기화 ---
# if "generated_text" not in st.session_state: st.session_state.generated_text = "" # Removed global init

if "app_started" not in st.session_state:
    st.session_state.app_started = False

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "📋 초기검토"

def main():
    if not st.session_state.app_started:
        st.markdown("""
            <div class="title-container">
                <h1>💎 GEM Intern</h1>
                <span class="badge">v6.0</span>
                <span class="badge badge-blue">Cloud-Safe Indexer</span>
            </div>
            <p style='color: gray; margin-top: -10px; margin-bottom: 10px;'>AI-Powered Investment Analysis Assistant</p>
        """, unsafe_allow_html=True)

        # [화면 1] 설정 페이지 (메인)
        st.markdown("### ⚙️ 환경 설정 (Settings)")
        st.info("업무를 시작하기 전에 필요한 설정을 완료해주세요.")
        
        # 설정 패널 렌더링 (메인 영역)
        settings = ui_input.render_settings()
        st.session_state['latest_settings'] = settings  # 설정값 저장
        
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ 설정 적용 및 업무 시작", type="primary", use_container_width=True):
                st.session_state.app_started = True
                st.session_state.selected_page = "📋 초기검토"
                st.rerun()
                
    else:
        # 설정값 불러오기 (없으면 기본값 복구)
        settings = st.session_state.get('latest_settings', {
            "api_key": st.session_state.get("api_key", ""),
            "model_name": st.session_state.get("model_name", "gemini-2.0-flash-thinking-exp-1219"),
            "thinking_level": st.session_state.get("thinking_level", "MINIMAL"),
            "use_diagram": st.session_state.get("use_diagram", False),
            "docai_config": st.session_state.get("docai_config", {})
        })

        # [화면 2] 업무 프로세스 (사이드바 레이아웃)
        with st.sidebar:
            st.markdown("### 📂 업무 프로세스")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 네비게이션 항목 정의
            nav_items = [
                "📋 초기검토", "📊 예비실사", "📑 IM 작성", "🔍 정밀실사",
                "🖥️ PPT 생성", "🎤 오디오 전사", "🌐 웹 크롤러",
                "👁️ 문서 OCR", "📝 MD to Word", "📋 문서양식"
            ]
            
            # 버튼 기반 네비게이션 렌더링
            for item in nav_items:
                is_active = (st.session_state.selected_page == item)
                if st.button(item, key=f"nav_{item}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.selected_page = item
                    st.rerun()

            st.markdown("---")
            
            # 설정 수정 버튼
            if st.button("⚙️ 설정 수정", key="nav_settings", use_container_width=True, type="primary" if st.session_state.selected_page == "SETTINGS" else "secondary"):
                st.session_state.selected_page = "SETTINGS"
                st.rerun()
                
            if st.button("🏠 처음으로", key="nav_home", use_container_width=True):
                st.session_state.app_started = False
                st.rerun()

        # 메인 콘텐츠 영역
        selected_page = st.session_state.selected_page

        # 분석/생성 페이지 그룹 (우측 사이드바 레이아웃 적용)
        analysis_pages = ["📋 초기검토", "📊 예비실사", "📑 IM 작성", "🔍 정밀실사", "🖥️ PPT 생성"]

        # [레이아웃 변경] 데이터 입력 패널을 사이드바 하단에 배치
        inputs = {}
        if selected_page in analysis_pages:
            with st.sidebar:
                st.markdown("---")
        if selected_page == "SETTINGS":
            st.markdown("### ⚙️ 환경 설정 (Settings)")
            st.info("설정을 수정한 후 하단의 '적용' 버튼을 눌러주세요.")
            updated_settings = ui_input.render_settings()
            st.session_state['latest_settings'] = updated_settings
            
            st.markdown("---")
            if st.button("✅ 설정 적용 및 업무 복귀", type="primary"):
                st.session_state.selected_page = "📋 초기검토"
                st.rerun()

        elif selected_page in analysis_pages:
            # [레이아웃] 좌측: 메인 출력 (70%) / 우측: 데이터 입력 (30%)
            col_main, col_right = st.columns([7, 3])

            # 1. 우측 패널 (Data Input) - 먼저 렌더링하여 inputs 변수 확보
            with col_right:
                st.markdown("### 📥 Data Input")
                st.caption("공통 데이터 입력")

                # 컨테이너로 감싸서 입력 폼 렌더링
                input_container = st.container()

                inputs = {}
                if selected_page == "📋 초기검토":
                    inputs = ui_input.render_initial_review_panel(input_container, settings)
                elif selected_page == "📊 예비실사":
                    inputs = ui_input.render_preliminary_dd_panel(input_container, settings)
                elif selected_page == "📑 IM 작성":
                    if hasattr(ui_input, 'render_im_panel'):
                        inputs = ui_input.render_im_panel(input_container, settings)
                    else:
                        inputs = ui_input.render_preliminary_dd_panel(input_container, settings)
                elif selected_page == "🔍 정밀실사":
                    inputs = ui_input.render_detailed_dd_panel(input_container, settings)
                elif selected_page == "🖥️ PPT 생성":
                    inputs = ui_input.render_ppt_panel(input_container, settings)

            # 2. 좌측 메인 영역 (Output)
            with col_main:
                if selected_page == "📋 초기검토":
                    st.markdown("### 📋 초기검토 (Quick Memo)")
                    st.caption("약식 투자검토보고서를 빠르게 작성합니다.")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="init")

                elif selected_page == "📊 예비실사":
                    st.markdown("### 📊 예비실사 (Preliminary DD)")
                    st.caption("투자심사보고서, 사후관리보고서 등을 작성합니다.")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="prelim")

                elif selected_page == "📑 IM 작성":
                    st.markdown("### 📑 IM 작성 (Information Memorandum)")
                    st.caption("잠재 투자자를 위한 투자제안서(IM)를 작성합니다.")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="im")

                elif selected_page == "🔍 정밀실사":
                    st.markdown("### 🔍 정밀실사 (Detailed DD)")
                    st.caption("RFI (자료요청목록) 작성 - FDD/LDD 유형별 지원")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="dd")

                elif selected_page == "🖥️ PPT 생성":
                    st.markdown("### 🖥️ PPT 생성 (Paper2Slides)")
                    st.caption("문서나 논문을 업로드하여 구조화된 발표자료(PPT)로 변환합니다.")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="ppt")

        elif selected_page == "🎤 오디오 전사":
            ui_audio.render_audio_transcription_panel(settings)

        elif selected_page == "🌐 웹 크롤러":
            ui_crawler.render_crawler_panel(settings)

        elif selected_page == "👁️ 문서 OCR":
            ui_ocr.render_ocr_panel(settings)

        elif selected_page == "📝 MD to Word":
            ui_markdown.render_markdown_converter_panel(settings)

        elif selected_page == "📋 문서양식":
            ui_doctemplate.render_doctemplate_panel(settings)

if __name__ == "__main__":
    main()