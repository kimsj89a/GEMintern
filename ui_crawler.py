import streamlit as st
import os
import sys
import subprocess

def render_crawler_panel(settings):
    """웹 크롤러 UI 패널"""
    st.markdown("### 🌐 웹 사이트 크롤러 (Web Crawler)")
    
    # 사용자 지정 경로
    crawler_path = r"C:\Users\kimsj\WebSiteCrawler"
    
    st.markdown(f"""
        <div style='background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ff4b4b;'>
        <h4 style='margin-top: 0; color: #ff4b4b;'>🕷️ WebSiteCrawler 연동</h4>
        <b>지정 경로:</b> <code>{crawler_path}</code><br/>
        외부 크롤러 프로젝트를 실행하고 결과를 통합합니다.
        </div>
    """, unsafe_allow_html=True)

    # 탭 구성
    tab_run, tab_view = st.tabs(["🚀 크롤링 실행", "📊 결과 분석"])

    with tab_run:
        st.markdown("#### 크롤링 파라미터 설정")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            target_url = st.text_input("Target URL", placeholder="https://www.example.com")
        with col2:
            depth = st.number_input("Depth", min_value=1, max_value=10, value=1)
            
        if st.button("🕷️ 크롤링 시작", use_container_width=True, type="primary"):
            if not os.path.exists(crawler_path):
                st.error(f"❌ 경로를 찾을 수 없습니다: {crawler_path}")
                st.warning("해당 경로에 크롤러 프로젝트 폴더가 존재하는지 확인해주세요.")
            elif not target_url:
                st.warning("⚠️ URL을 입력해주세요.")
            else:
                st.info(f"📡 '{target_url}' 크롤링을 시작합니다... (경로: {crawler_path})")
                
                # [TODO] 실제 크롤러 실행 로직 연결
                # 예시: subprocess로 main.py 실행 (파일명에 맞게 수정 필요)
                # try:
                #     # 가상환경이나 python 실행 명령어에 맞게 수정하세요
                #     result = subprocess.run(
                #         ["python", os.path.join(crawler_path, "main.py"), "--url", target_url, "--depth", str(depth)],
                #         capture_output=True, text=True, cwd=crawler_path
                #     )
                #     if result.returncode == 0:
                #         st.success("크롤링 완료!")
                #         st.code(result.stdout)
                #     else:
                #         st.error(f"실행 중 오류 발생:\n{result.stderr}")
                # except Exception as e:
                #     st.error(f"실행 오류: {e}")
                
                st.warning("⚠️ 현재는 UI만 연결되었습니다. `ui_crawler.py` 파일의 주석을 해제하여 실제 실행 로직(subprocess 등)을 활성화해주세요.")

    with tab_view:
        st.markdown("#### 수집 데이터 뷰어")
        st.info("크롤링 완료 후 저장된 데이터(CSV/JSON)를 이곳에 표시할 수 있습니다.")