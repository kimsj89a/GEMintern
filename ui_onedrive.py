import streamlit as st
import utils_onedrive
import os

# Session state keys
KEY_ACCESS_TOKEN = "od_access_token"
KEY_USER_INFO = "od_user_info"
KEY_CURRENT_PATH = "od_current_path" # List of (id, name) tuples
KEY_NAV_ID = "od_nav_id" # Current folder ID

def render_onedrive_importer(settings, key_prefix="od"):
    """
    Renders the OneDrive import UI.
    Returns the file content (bytes) and filename if a file is selected and imported.
    """
    
    # 1. Configuration Check
    client_id = settings.get("onedrive_client_id")
    if not client_id:
        st.warning("⚠️ OneDrive 설정을 먼저 해주세요. (Settings > OneDrive Client ID)")
        return None, None

    # Redirect URI adjustment for Streamlit Cloud vs Localhost
    # You might need to make this configurable in settings too.
    redirect_uri = "http://localhost:8501" 
    
    client = utils_onedrive.OneDriveClient(client_id, redirect_uri=redirect_uri)

    # 2. Auth Flow Handling
    # Check if we have an access token
    if KEY_ACCESS_TOKEN not in st.session_state:
        # Check if we are in the callback (URL params)
        query_params = st.query_params
        if "code" in query_params:
            code = query_params["code"]
            with st.spinner("OneDrive 로그인 중..."):
                result = client.acquire_token_from_code(code)
                if "access_token" in result:
                    st.session_state[KEY_ACCESS_TOKEN] = result["access_token"]
                    user_info = client.get_user_info(result["access_token"])
                    st.session_state[KEY_USER_INFO] = user_info
                    st.session_state[KEY_CURRENT_PATH] = [] # Root
                    # Clear query params to clean up URL
                    # st.query_params.clear() # Might reload app, be careful
                    st.success(f"로그인 성공! {user_info.get('displayName')}님 환영합니다.")
                    st.rerun()
                else:
                    st.error(f"로그인 실패: {result.get('error_description')}")
        else:
            # Login Button
            auth_url = client.get_auth_url()
            st.markdown(f'<a href="{auth_url}" target="_self" style="text-decoration:none;"><button style="background-color:#0078D4;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">☁️ OneDrive 로그인</button></a>', unsafe_allow_html=True)
            return None, None
            
    # 3. Logged In View
    access_token = st.session_state[KEY_ACCESS_TOKEN]
    user_info = st.session_state.get(KEY_USER_INFO, {})
    
    st.markdown(f"**👤 {user_info.get('displayName')}**님의 OneDrive")
    if st.button("로그아웃", key=f"{key_prefix}_logout", type="secondary"):
        del st.session_state[KEY_ACCESS_TOKEN]
        del st.session_state[KEY_USER_INFO]
        st.rerun()
        
    st.markdown("---")
    
    # Navigation
    current_path = st.session_state.get(KEY_CURRENT_PATH, []) # Stack of (id, name)
    current_folder_id = current_path[-1][0] if current_path else None
    
    # Breadcrumb
    bc_cols = st.columns([0.1] + [0.2] * len(current_path) + [1])
    if st.button("🏠 Root", key=f"{key_prefix}_nav_root"):
        st.session_state[KEY_CURRENT_PATH] = []
        st.rerun()
        
    # File Listing
    items = client.list_files(access_token, folder_id=current_folder_id)
    
    if not items:
        st.info("폴더가 비어있습니다.")
    
    # Render Items
    for item in items:
        col_icon, col_name, col_action = st.columns([1, 6, 2])
        is_folder = 'folder' in item
        name = item['name']
        item_id = item['id']
        
        with col_icon:
            st.markdown("📁" if is_folder else "📄")
            
        with col_name:
            st.write(name)
            
        with col_action:
            if is_folder:
                if st.button("이동", key=f"{key_prefix}_go_{item_id}"):
                    current_path.append((item_id, name))
                    st.session_state[KEY_CURRENT_PATH] = current_path
                    st.rerun()
            else:
                # File selection/import
                if st.button("📥 가져오기", key=f"{key_prefix}_import_{item_id}", type="primary"):
                    with st.spinner("파일 다운로드 중..."):
                        file_content = client.download_file(access_token, item_id)
                        if file_content:
                            return file_content, name
                        else:
                            st.error("파일 다운로드 실패")
                            
    return None, None
