import streamlit as st
import os
import sys
import subprocess
import pandas as pd
import glob

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
            target_urls_input = st.text_area("Target URLs (한 줄에 하나씩 입력)", placeholder="https://www.example.com\nhttps://www.google.com", height=100)
        with col2:
            depth = st.number_input("Depth", min_value=1, max_value=10, value=1)
            
        if st.button("🕷️ 크롤링 시작", use_container_width=True, type="primary"):
            if not os.path.exists(crawler_path):
                st.error(f"❌ 경로를 찾을 수 없습니다: {crawler_path}")
                st.warning("해당 경로에 크롤러 프로젝트 폴더가 존재하는지 확인해주세요.")
            elif not target_urls_input.strip():
                st.warning("⚠️ URL을 입력해주세요.")
            else:
                urls = [url.strip() for url in target_urls_input.split('\n') if url.strip()]
                st.info(f"📡 총 {len(urls)}개의 URL에 대해 크롤링을 시작합니다... (경로: {crawler_path})")
                
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, target_url in enumerate(urls):
                    status_text.text(f"🕷️ ({i+1}/{len(urls)}) '{target_url}' 크롤링 중...")
                    try:
                        # 실제 크롤러 실행 (main.py 가정)
                        result = subprocess.run(
                            ["python", "main.py", "--url", target_url, "--depth", str(depth)],
                            capture_output=True, text=True, cwd=crawler_path, encoding='utf-8', errors='replace'
                        )
                        if result.returncode == 0:
                            st.toast(f"✅ 완료: {target_url}")
                        else:
                            st.error(f"❌ 실패 ({target_url}):\n{result.stderr}")
                    except Exception as e:
                        st.error(f"실행 오류 ({target_url}): {e}")
                    
                    progress_bar.progress((i + 1) / len(urls))
                
                status_text.success("🎉 모든 작업이 완료되었습니다!")

    with tab_view:
        st.markdown("#### 수집 데이터 뷰어")
        
        if os.path.exists(crawler_path):
            # CSV 파일 검색 (루트 및 output 폴더)
            csv_files = glob.glob(os.path.join(crawler_path, "*.csv"))
            csv_files += glob.glob(os.path.join(crawler_path, "output", "*.csv"))
            csv_files.sort(key=os.path.getmtime, reverse=True)

            if csv_files:
                selected_csv = st.selectbox("📂 결과 파일 선택", csv_files, format_func=lambda x: os.path.basename(x))
                if selected_csv:
                    try:
                        df = pd.read_csv(selected_csv)
                        st.dataframe(df, use_container_width=True)
                        st.caption(f"📊 총 {len(df)}행 | 경로: {selected_csv}")
                    except Exception as e:
                        st.error(f"파일 읽기 오류: {e}")
            else:
                st.info("📭 표시할 CSV 파일이 없습니다. 크롤링을 먼저 실행해주세요.")
        else:
            st.error(f"경로를 찾을 수 없습니다: {crawler_path}")