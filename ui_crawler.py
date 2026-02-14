import streamlit as st
import pandas as pd
import requests
import time
from urllib.parse import urljoin
import core_logic

# BeautifulSoup 라이브러리 확인
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# lxml 라이브러리 확인 (XPath용)
try:
    from lxml import html
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

def render_crawler_panel(settings):
    """웹 크롤러 UI 패널 (Internal)"""
    st.markdown("### 🌐 웹 사이트 크롤러 (Web Crawler)")
    
    if not BS4_AVAILABLE:
        st.error("❌ `beautifulsoup4` 라이브러리가 설치되지 않았습니다.")
        st.code("pip install beautifulsoup4 requests", language="bash")
        return
    
    st.markdown(f"""
        <div style='background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0068c9;'>
        <h4 style='margin-top: 0; color: #0068c9;'>🕷️ 내장 크롤러 (Built-in)</h4>
        외부 스크립트 경로 의존성 없이, URL을 입력하면 즉시 크롤링하여 결과를 보여줍니다.
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
            depth = st.number_input("Depth (링크 추적 깊이)", min_value=1, max_value=3, value=1, help="너무 깊게 설정하면 시간이 오래 걸립니다.")
            max_pages = st.number_input("Max Pages (URL당 최대)", min_value=1, max_value=50, value=5)
        
        col3, col4 = st.columns([3, 1])
        with col3:
            xpath_input = st.text_input("XPath (선택사항 - 특정 영역 추출)", placeholder="//div[@id='content']", help="입력 시 해당 XPath 경로의 텍스트만 추출합니다. (lxml 필요)")
        with col4:
            clean_mode = st.checkbox("🧹 불필요 요소 제거", value=True, help="Script, Style, Nav, Footer 등을 자동으로 제거합니다.")
            
        if st.button("🕷️ 크롤링 시작", use_container_width=True, type="primary"):
            if not target_urls_input.strip():
                st.warning("⚠️ URL을 입력해주세요.")
            else:
                urls = [url.strip() for url in target_urls_input.split('\n') if url.strip()]
                st.info(f"📡 총 {len(urls)}개의 시작 URL에 대해 크롤링을 시작합니다...")
                
                all_results = []
                progress_bar = st.progress(0)
                
                for i, start_url in enumerate(urls):
                    # 내부 크롤링 로직 실행
                    df_res = _crawl_internal(start_url, depth, max_pages, xpath_input, clean_mode)
                    all_results.append(df_res)
                    progress_bar.progress((i + 1) / len(urls))
                
                if all_results:
                    final_df = pd.concat(all_results, ignore_index=True)
                    st.session_state['crawled_data'] = final_df
                    st.success(f"🎉 완료! 총 {len(final_df)}개의 페이지를 수집했습니다.")
                    st.rerun() # 결과 탭 갱신을 위해 리런

    with tab_view:
        st.markdown("#### 수집 데이터 뷰어")
        
        if 'crawled_data' in st.session_state and not st.session_state['crawled_data'].empty:
            df = st.session_state['crawled_data']
            st.dataframe(df, use_container_width=True)
            st.caption(f"📊 총 {len(df)}행")
            
            col1, col2 = st.columns(2)
            with col1:
                # CSV 다운로드
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📥 CSV 다운로드",
                    csv,
                    "crawled_results.csv",
                    "text/csv",
                    key='download-csv',
                    use_container_width=True
                )
            with col2:
                # TXT 다운로드 (전체 내용 보존)
                txt_output = ""
                for _, row in df.iterrows():
                    txt_output += f"Title: {row.get('title', 'No Title')}\n"
                    txt_output += f"URL: {row.get('url', 'No URL')}\n"
                    txt_output += f"Content:\n{row.get('content', '')}\n"
                    txt_output += "="*80 + "\n\n"
                
                st.download_button(
                    "📥 TXT 다운로드 (전체 내용)",
                    txt_output,
                    "crawled_results.txt",
                    "text/plain",
                    key='download-txt',
                    use_container_width=True
                )

            # Gemini 요약 리포트 생성
            st.markdown("---")
            st.markdown("#### 🤖 AI 요약 보고서 작성")
            
            api_key = settings.get("api_key")
            if not api_key:
                st.warning("⚠️ 상단 설정에서 Google API Key를 입력하면 요약 기능을 사용할 수 있습니다.")
            else:
                if st.button("📝 수집 데이터 요약하기", type="primary", use_container_width=True):
                    with st.spinner("🤖 수집된 데이터를 AI로 분석하는 중..."):
                        try:
                            # 텍스트 통합
                            combined_text = ""
                            for _, row in df.iterrows():
                                combined_text += f"Title: {row.get('title', '')}\nURL: {row.get('url', '')}\nContent:\n{row.get('content', '')}\n\n"
                            
                            # Gemini 호출
                            client = core_logic.get_client(api_key)
                            model_name = settings.get("model_name", "gemini-3-pro-preview")
                            
                            prompt = f"""
                            당신은 정보 분석 전문가입니다. 다음은 웹 크롤링을 통해 수집된 데이터입니다.
                            이 내용을 바탕으로 핵심 내용을 요약하고, 주요 인사이트를 도출하는 보고서를 작성해주세요.
                            
                            [작성 형식]
                            1. Executive Summary (요약)
                            2. 주요 수집 내용 및 팩트 정리
                            3. 인사이트 및 시사점
                            
                            [수집 데이터]
                            {combined_text[:500000]}
                            """
                            
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt
                            )
                            
                            st.markdown("### 📄 요약 보고서")
                            st.container(border=True).markdown(response.text)
                            
                        except Exception as e:
                            st.error(f"요약 생성 중 오류 발생: {e}")
        else:
            st.info("📭 수집된 데이터가 없습니다. '크롤링 실행' 탭에서 작업을 시작해주세요.")

def _crawl_internal(start_url, max_depth, max_pages, xpath=None, clean=True):
    """실제 크롤링 수행 함수"""
    visited = set()
    queue = [(start_url, 0)]
    results = []
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    with st.status(f"Processing: {start_url}") as status:
        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)
            if url in visited: continue
            visited.add(url)
            
            status.update(label=f"Fetching ({len(visited)}/{max_pages}): {url}")
            
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    text_content = ""
                    title = ""
                    found_links = []

                    # 1. XPath Mode (lxml)
                    if xpath and LXML_AVAILABLE:
                        try:
                            tree = html.fromstring(resp.content)
                            t_nodes = tree.xpath('//title/text()')
                            title = t_nodes[0].strip() if t_nodes else url
                            
                            if depth < max_depth:
                                found_links = tree.xpath('//a/@href')

                            if clean:
                                for bad in tree.xpath('//script|//style|//nav|//footer|//header|//aside|//iframe|//noscript'):
                                    bad.drop_tree()
                            
                            elements = tree.xpath(xpath)
                            extracted = []
                            for e in elements:
                                if isinstance(e, str): extracted.append(e.strip())
                                elif hasattr(e, 'text_content'): extracted.append(e.text_content().strip())
                            text_content = "\n".join([t for t in extracted if t])
                        except Exception as e:
                            text_content = f"XPath Error: {e}"

                    # 2. BS4 Mode
                    elif BS4_AVAILABLE:
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        title = soup.title.string.strip() if soup.title else url
                        
                        if depth < max_depth:
                            found_links = [a['href'] for a in soup.find_all('a', href=True)]

                        if clean:
                            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript", "form"]):
                                tag.decompose()
                        
                        if xpath and not LXML_AVAILABLE:
                            text_content = "[Error] XPath를 사용하려면 'lxml' 라이브러리가 필요합니다."
                        else:
                            text_content = soup.get_text(separator=' ', strip=True)
                    
                    results.append({
                        "url": url,
                        "title": title,
                        "depth": depth,
                        "content": text_content
                    })
                    
                    if depth < max_depth:
                        for link in found_links:
                            next_url = urljoin(url, link)
                            if next_url.startswith("http") and next_url not in visited:
                                queue.append((next_url, depth + 1))
                else:
                    results.append({"url": url, "title": f"Error {resp.status_code}", "depth": depth, "content": ""})
            except Exception as e:
                results.append({"url": url, "title": "Error", "depth": depth, "content": str(e)})
                
            time.sleep(0.2)
            
    return pd.DataFrame(results)