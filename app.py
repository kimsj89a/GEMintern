import streamlit as st
import ui_input
import ui_output
import ui_audio
import ui_crawler
import ui_ocr
import ui_markdown
import ui_doctemplate

# --- ?˜ì´ì§€ ?¤ì • ---
st.set_page_config(layout="wide", page_title="GEM Intern v6.0", page_icon="?’")

# --- CSS ?¤í????ìš© ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .title-container { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
    .badge { background-color: #f0f2f6; color: #31333F; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; border: 1px solid #d6d6d8; }
    .badge-blue { background-color: #e6f0ff; color: #0068c9; border: 1px solid #b3d1ff; }
    .info-box { background-color: #fff8c5; padding: 10px; border-radius: 5px; border: 1px solid #e3d5a5; font-size: 0.85rem; color: #5c4b12; margin-bottom: 15px; }
    p, li, div { word-break: keep-all; overflow-wrap: break-word; }
    
    /* ?¬ì´?œë°” ?¤ë¹„ê²Œì´??ë²„íŠ¼ ?¤í???(Gemini-like) */
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
    /* ?œì„±?”ëœ ë²„íŠ¼ ?¤í???*/
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #e6f0ff;
        color: #0068c9;
        font-weight: 600;
        border-left: 4px solid #0068c9;
        border-radius: 0 4px 4px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- ?íƒœ ì´ˆê¸°??---
# if "generated_text" not in st.session_state: st.session_state.generated_text = "" # Removed global init

if "app_started" not in st.session_state:
    st.session_state.app_started = False

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "?“‹ ì´ˆê¸°ê²€??

def main():
    if not st.session_state.app_started:
        st.markdown("""
            <div class="title-container">
                <h1>?’ GEM Intern</h1>
                <span class="badge">v6.0</span>
                <span class="badge badge-blue">Cloud-Safe Indexer</span>
            </div>
            <p style='color: gray; margin-top: -10px; margin-bottom: 10px;'>AI-Powered Investment Analysis Assistant</p>
        """, unsafe_allow_html=True)

        # [?”ë©´ 1] ?¤ì • ?˜ì´ì§€ (ë©”ì¸)
        st.markdown("### ?™ï¸ ?˜ê²½ ?¤ì • (Settings)")
        st.info("?…ë¬´ë¥??œì‘?˜ê¸° ?„ì— ?„ìš”???¤ì •???„ë£Œ?´ì£¼?¸ìš”.")
        
        # ?¤ì • ?¨ë„ ?Œë”ë§?(ë©”ì¸ ?ì—­)
        settings = ui_input.render_settings()
        st.session_state['latest_settings'] = settings  # ?¤ì •ê°??€??
        
        st.markdown("---")
        if st.button("???¤ì • ?ìš© ë°??…ë¬´ ?œì‘", type="primary", use_container_width=True):
            st.session_state.app_started = True
            st.session_state.selected_page = "?“‹ ì´ˆê¸°ê²€??
            st.rerun()
                
    else:
        # ?¤ì •ê°?ë¶ˆëŸ¬?¤ê¸° (?†ìœ¼ë©?ê¸°ë³¸ê°?ë³µêµ¬)
        settings = st.session_state.get('latest_settings', {
            "api_key": st.session_state.get("api_key", ""),
            "model_name": st.session_state.get("model_name", "gemini-2.0-flash-thinking-exp-1219"),
            "thinking_level": st.session_state.get("thinking_level", "MINIMAL"),
            "use_diagram": st.session_state.get("use_diagram", False),
            "docai_config": st.session_state.get("docai_config", {})
        })

        # [?”ë©´ 2] ?…ë¬´ ?„ë¡œ?¸ìŠ¤ (?¬ì´?œë°” ?ˆì´?„ì›ƒ)
        with st.sidebar:
            st.markdown("### ?“‚ ?…ë¬´ ?„ë¡œ?¸ìŠ¤")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ?¤ë¹„ê²Œì´????ª© ?•ì˜
            nav_items = [
                "?“‹ ì´ˆê¸°ê²€??, "?“Š ?ˆë¹„?¤ì‚¬", " IM ?‘ì„±", "?” ?•ë??¤ì‚¬", 
                "ï¸?PPT ?ì„±", "?¤ ?¤ë””???„ì‚¬", "?Œ ???¬ë¡¤??, 
                "?‘ï¸?ë¬¸ì„œ OCR", "?“ MD to Word", "?“‹ ë¬¸ì„œ?‘ì‹"
            ]
            
            # ë²„íŠ¼ ê¸°ë°˜ ?¤ë¹„ê²Œì´???Œë”ë§?
            for item in nav_items:
                is_active = (st.session_state.selected_page == item)
                if st.button(item, key=f"nav_{item}", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.selected_page = item
                    st.rerun()

            st.markdown("---")
            
            # ?¤ì • ?˜ì • ë²„íŠ¼
            if st.button("?™ï¸ ?¤ì • ?˜ì •", key="nav_settings", use_container_width=True, type="primary" if st.session_state.selected_page == "SETTINGS" else "secondary"):
                st.session_state.selected_page = "SETTINGS"
                st.rerun()
                
            if st.button("?  ì²˜ìŒ?¼ë¡œ", key="nav_home", use_container_width=True):
                st.session_state.app_started = False
                st.rerun()

        # ë©”ì¸ ì½˜í…ì¸??ì—­
        selected_page = st.session_state.selected_page

        # ë¶„ì„/?ì„± ?˜ì´ì§€ ê·¸ë£¹ (?°ì¸¡ ?¬ì´?œë°” ?ˆì´?„ì›ƒ ?ìš©)
        analysis_pages = ["?“‹ ì´ˆê¸°ê²€??, "?“Š ?ˆë¹„?¤ì‚¬", "?“‘ IM ?‘ì„±", "?” ?•ë??¤ì‚¬", "?–¥ï¸?PPT ?ì„±"]

        # [?ˆì´?„ì›ƒ ë³€ê²? ?°ì´???…ë ¥ ?¨ë„???¬ì´?œë°” ?˜ë‹¨??ë°°ì¹˜
        inputs = {}
        if selected_page in analysis_pages:
            with st.sidebar:
                st.markdown("---")
        if selected_page == "SETTINGS":
            st.markdown("### ?™ï¸ ?˜ê²½ ?¤ì • (Settings)")
            st.info("?¤ì •???˜ì •?????˜ë‹¨??'?ìš©' ë²„íŠ¼???ŒëŸ¬ì£¼ì„¸??")
            updated_settings = ui_input.render_settings()
            st.session_state['latest_settings'] = updated_settings
            
            st.markdown("---")
            if st.button("???¤ì • ?ìš© ë°??…ë¬´ ë³µê?", type="primary"):
                st.session_state.selected_page = "ï¿?ì´ˆê¸°ê²€??
                st.rerun()

        elif selected_page in analysis_pages:
            # [?ˆì´?„ì›ƒ] ì¢Œì¸¡: ë©”ì¸ ì¶œë ¥ (70%) / ?°ì¸¡: ?°ì´???…ë ¥ (30%)
            col_main, col_right = st.columns([7, 3])
            
            # 1. ?°ì¸¡ ?¨ë„ (Data Input) - ë¨¼ì? ?Œë”ë§í•˜??inputs ë³€???•ë³´
            with col_right:
                st.markdown("### ï¿½ğŸ“?Data Input")
                st.caption("ê³µí†µ ?°ì´???…ë ¥")
                
                # ?¬ì´?œë°” ??ì»¨í…Œ?´ë„ˆ???…ë ¥ ???Œë”ë§?
                # ì»¨í…Œ?´ë„ˆë¡?ê°ì‹¸???…ë ¥ ???Œë”ë§?
                input_container = st.container()
                
                inputs = {}
                if selected_page == "?“‹ ì´ˆê¸°ê²€??:
                    inputs = ui_input.render_initial_review_panel(input_container, settings)
                elif selected_page == "?“Š ?ˆë¹„?¤ì‚¬":
                    inputs = ui_input.render_preliminary_dd_panel(input_container, settings)
                elif selected_page == "?“‘ IM ?‘ì„±":
                    if hasattr(ui_input, 'render_im_panel'):
                        inputs = ui_input.render_im_panel(input_container, settings)
                    else:
                        inputs = ui_input.render_preliminary_dd_panel(input_container, settings)
                elif selected_page == "?” ?•ë??¤ì‚¬":
                    inputs = ui_input.render_detailed_dd_panel(input_container, settings)
                elif selected_page == "?–¥ï¸?PPT ?ì„±":
                    inputs = ui_input.render_ppt_panel(input_container, settings)

        if selected_page == "SETTINGS":
            st.markdown("### ?™ï¸ ?˜ê²½ ?¤ì • (Settings)")
            st.info("?¤ì •???˜ì •?????˜ë‹¨??'?ìš©' ë²„íŠ¼???ŒëŸ¬ì£¼ì„¸??")
            updated_settings = ui_input.render_settings()
            st.session_state['latest_settings'] = updated_settings
            
            st.markdown("---")
            if st.button("???¤ì • ?ìš© ë°??…ë¬´ ë³µê?", type="primary"):
                st.session_state.selected_page = "?“‹ ì´ˆê¸°ê²€??
                st.rerun()
            # 2. ì¢Œì¸¡ ë©”ì¸ ?ì—­ (Output)
            with col_main:
                if selected_page == "?“‹ ì´ˆê¸°ê²€??:
                    st.markdown("### ?“‹ ì´ˆê¸°ê²€??(Quick Memo)")
                    st.caption("?½ì‹ ?¬ìê²€? ë³´ê³ ì„œë¥?ë¹ ë¥´ê²??‘ì„±?©ë‹ˆ??")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="init")
                    
                elif selected_page == "?“Š ?ˆë¹„?¤ì‚¬":
                    st.markdown("### ?“Š ?ˆë¹„?¤ì‚¬ (Preliminary DD)")
                    st.caption("?¬ì?¬ì‚¬ë³´ê³ ?? ?¬í›„ê´€ë¦¬ë³´ê³ ì„œ ?±ì„ ?‘ì„±?©ë‹ˆ??")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="prelim")
                    
                elif selected_page == "?“‘ IM ?‘ì„±":
                    st.markdown("### ?“‘ IM ?‘ì„± (Information Memorandum)")
                    st.caption("? ì¬ ?¬ì?ë? ?„í•œ ?¬ì?œì•ˆ??IM)ë¥??‘ì„±?©ë‹ˆ??")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="im")
                    
                elif selected_page == "?” ?•ë??¤ì‚¬":
                    st.markdown("### ?” ?•ë??¤ì‚¬ (Detailed DD)")
                    st.caption("RFI (?ë£Œ?”ì²­ëª©ë¡) ?‘ì„± - FDD/LDD ? í˜•ë³?ì§€??)
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="dd")
                    
                elif selected_page == "?–¥ï¸?PPT ?ì„±":
                    st.markdown("### ?–¥ï¸?PPT ?ì„± (Paper2Slides)")
                    st.caption("ë¬¸ì„œ???¼ë¬¸???…ë¡œ?œí•˜??êµ¬ì¡°?”ëœ ë°œí‘œ?ë£Œ(PPT)ë¡?ë³€?˜í•©?ˆë‹¤.")
                    st.markdown("---")
                    ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="ppt")

        elif selected_page in analysis_pages:
            # [?ˆì´?„ì›ƒ] ë©”ì¸ ?ì—­ (Output Only) - ?…ë ¥?€ ?¬ì´?œë°”?ì„œ ì²˜ë¦¬??
            if selected_page == " ì´ˆê¸°ê²€??:
                st.markdown("### ?“‹ ì´ˆê¸°ê²€??(Quick Memo)")
                st.caption("?½ì‹ ?¬ìê²€? ë³´ê³ ì„œë¥?ë¹ ë¥´ê²??‘ì„±?©ë‹ˆ??")
                st.markdown("---")
                ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="init")
                
            elif selected_page == "?“Š ?ˆë¹„?¤ì‚¬":
                st.markdown("### ?“Š ?ˆë¹„?¤ì‚¬ (Preliminary DD)")
                st.caption("?¬ì?¬ì‚¬ë³´ê³ ?? ?¬í›„ê´€ë¦¬ë³´ê³ ì„œ ?±ì„ ?‘ì„±?©ë‹ˆ??")
                st.markdown("---")
                ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="prelim")
                
            elif selected_page == "?“‘ IM ?‘ì„±":
                st.markdown("### ?“‘ IM ?‘ì„± (Information Memorandum)")
                st.caption("? ì¬ ?¬ì?ë? ?„í•œ ?¬ì?œì•ˆ??IM)ë¥??‘ì„±?©ë‹ˆ??")
                st.markdown("---")
                ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="im")
                
            elif selected_page == "?” ?•ë??¤ì‚¬":
                st.markdown("### ?” ?•ë??¤ì‚¬ (Detailed DD)")
                st.caption("RFI (?ë£Œ?”ì²­ëª©ë¡) ?‘ì„± - FDD/LDD ? í˜•ë³?ì§€??)
                st.markdown("---")
                ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="dd")
                
            elif selected_page == "?–¥ï¸?PPT ?ì„±":
                st.markdown("### ?–¥ï¸?PPT ?ì„± (Paper2Slides)")
                st.caption("ë¬¸ì„œ???¼ë¬¸???…ë¡œ?œí•˜??êµ¬ì¡°?”ëœ ë°œí‘œ?ë£Œ(PPT)ë¡?ë³€?˜í•©?ˆë‹¤.")
                st.markdown("---")
                ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="ppt")

        elif selected_page == "?¤ ?¤ë””???„ì‚¬":
            ui_audio.render_audio_transcription_panel(settings)

        elif selected_page == "?Œ ???¬ë¡¤??:
            ui_crawler.render_crawler_panel(settings)

        elif selected_page == "?‘ï¸?ë¬¸ì„œ OCR":
            ui_ocr.render_ocr_panel(settings)

        elif selected_page == "?“ MD to Word":
            ui_markdown.render_markdown_converter_panel(settings)

        elif selected_page == "?“‹ ë¬¸ì„œ?‘ì‹":
            ui_doctemplate.render_doctemplate_panel(settings)

if __name__ == "__main__":
    main()
