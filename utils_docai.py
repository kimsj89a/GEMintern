"""
Google Document AI OCR 유틸리티
- 기본 OCR 처리
- Searchable PDF 생성 (PyMuPDF 사용)
"""
import io
import os
import fitz  # PyMuPDF
from google.cloud import documentai_v1 as documentai
from google.oauth2 import service_account


def get_client(credentials_json=None):
    """Document AI 클라이언트 생성"""
    if credentials_json:
        import json
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        return documentai.DocumentProcessorServiceClient(credentials=credentials)
    else:
        return documentai.DocumentProcessorServiceClient()


def get_mime_type(file_name):
    """파일 확장자로 MIME 타입 반환"""
    ext = file_name.split('.')[-1].lower()
    mime_map = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
        'webp': 'image/webp'
    }
    return mime_map.get(ext, 'application/octet-stream')


def get_supported_extensions():
    """지원하는 파일 확장자 목록"""
    return ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp']


def process_document(file_bytes, mime_type, project_id, location, processor_id, credentials_json=None):
    """
    Document AI로 문서 처리 (OCR)

    Returns:
        dict: {
            'text': 추출된 전체 텍스트,
            'pages': 페이지별 정보 (텍스트, 블록, 좌표),
            'raw_document': 원본 Document 객체
        }
    """
    client = get_client(credentials_json)
    processor_name = client.processor_path(project_id, location, processor_id)

    # PDF 페이지 수 확인 및 분할 처리 (API 제한 회피)
    if mime_type == 'application/pdf':
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                num_pages = len(doc)
                BATCH_SIZE = 15  # Document AI 온라인 처리 제한(보통 15~30페이지)

                if num_pages > BATCH_SIZE:
                    merged_text = ""
                    merged_pages_info = []

                    for start_page in range(0, num_pages, BATCH_SIZE):
                        end_page = min(start_page + BATCH_SIZE, num_pages)
                        
                        # 부분 PDF 생성
                        sub_doc = fitz.open()
                        sub_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
                        sub_bytes = sub_doc.tobytes()
                        sub_doc.close()

                        # API 호출 (부분)
                        raw_document = documentai.RawDocument(
                            content=sub_bytes,
                            mime_type=mime_type
                        )
                        request = documentai.ProcessRequest(
                            name=processor_name,
                            raw_document=raw_document
                        )
                        result = client.process_document(request=request)
                        chunk_document = result.document

                        # 텍스트 병합
                        if chunk_document.text:
                            merged_text += chunk_document.text + "\n"

                        # 페이지 정보 추출
                        if chunk_document.pages:
                            for i, page in enumerate(chunk_document.pages):
                                page_data = {
                                    'page_num': start_page + i + 1,
                                    'text': extract_page_text(page, chunk_document.text),
                                    'width': page.dimension.width if page.dimension else 0,
                                    'height': page.dimension.height if page.dimension else 0,
                                    'blocks': []
                                }
                                _extract_blocks(page, chunk_document.text, page_data)
                                merged_pages_info.append(page_data)

                    return {
                        'text': merged_text,
                        'pages': merged_pages_info,
                        'raw_document': None  # 분할 처리 시 원본 객체 없음
                    }
        except Exception as e:
            # 분할 처리 실패 시 기본 로직으로 진행 (로그 출력 등 필요 시 추가)
            pass

    raw_document = documentai.RawDocument(
        content=file_bytes,
        mime_type=mime_type
    )

    request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=raw_document
    )

    result = client.process_document(request=request)
    document = result.document

    # 페이지별 정보 추출 (텍스트 + 좌표)
    pages_info = []
    if document.pages:
        for page_num, page in enumerate(document.pages):
            page_data = {
                'page_num': page_num + 1,
                'text': extract_page_text(page, document.text),
                'width': page.dimension.width if page.dimension else 0,
                'height': page.dimension.height if page.dimension else 0,
                'blocks': []
            }

            _extract_blocks(page, document.text, page_data)

            pages_info.append(page_data)

    return {
        'text': document.text,
        'pages': pages_info,
        'raw_document': document
    }


def _extract_blocks(page, full_text, page_data):
    """페이지에서 블록/라인 정보 추출하여 page_data에 추가"""
    # 블록별 텍스트와 좌표 저장 (Searchable PDF 품질을 위해 lines 우선 사용)
    items = page.lines if page.lines else page.blocks
    for item in items:
        block_text = get_text_from_layout(item.layout, full_text)
        if block_text.strip() and item.layout.bounding_poly:
            vertices = item.layout.bounding_poly.normalized_vertices
            if vertices:
                page_data['blocks'].append({
                    'text': block_text,
                    'bbox': {
                        'x0': vertices[0].x if len(vertices) > 0 else 0,
                        'y0': vertices[0].y if len(vertices) > 0 else 0,
                        'x1': vertices[2].x if len(vertices) > 2 else 1,
                        'y1': vertices[2].y if len(vertices) > 2 else 1,
                    }
                })

def extract_page_text(page, full_text):
    """페이지에서 텍스트 추출"""
    text_parts = []
    for block in page.blocks:
        block_text = get_text_from_layout(block.layout, full_text)
        if block_text.strip():
            text_parts.append(block_text)
    return '\n'.join(text_parts)


def get_text_from_layout(layout, full_text):
    """레이아웃에서 텍스트 추출"""
    if not layout.text_anchor or not layout.text_anchor.text_segments:
        return ""

    text = ""
    for segment in layout.text_anchor.text_segments:
        start_index = int(segment.start_index) if segment.start_index else 0
        end_index = int(segment.end_index) if segment.end_index else 0
        text += full_text[start_index:end_index]

    return text


def create_searchable_pdf(original_bytes, ocr_result, original_mime_type='application/pdf'):
    """
    OCR 결과를 사용하여 Searchable PDF 생성

    원본 이미지/PDF 위에 투명한 텍스트 레이어를 덮어씌워서
    텍스트 선택 및 검색이 가능한 PDF를 만듭니다.

    Args:
        original_bytes: 원본 파일 바이트
        ocr_result: process_document() 결과
        original_mime_type: 원본 파일 MIME 타입

    Returns:
        bytes: Searchable PDF 바이트 데이터
    """
    # 원본 파일 열기
    if 'image' in original_mime_type:
        # 이미지인 경우 PDF로 변환
        img_doc = fitz.open(stream=original_bytes, filetype=original_mime_type.split('/')[-1])
        doc = fitz.open()
        for img_page in img_doc:
            # 이미지를 PDF 페이지로 변환
            rect = img_page.rect
            pdf_page = doc.new_page(width=rect.width, height=rect.height)
            pdf_page.insert_image(rect, stream=original_bytes)
        img_doc.close()
    else:
        # PDF인 경우 직접 열기
        doc = fitz.open(stream=original_bytes, filetype="pdf")

    # 각 페이지에 투명 텍스트 오버레이
    for page_num, page in enumerate(doc):
        if page_num < len(ocr_result['pages']):
            page_ocr = ocr_result['pages'][page_num]
            page_width = page.rect.width
            page_height = page.rect.height

            # 블록별로 텍스트 삽입
            for block in page_ocr.get('blocks', []):
                text = block['text'].strip()
                if not text:
                    continue

                bbox = block['bbox']

                # 정규화된 좌표를 실제 좌표로 변환
                x0 = bbox['x0'] * page_width
                y0 = bbox['y0'] * page_height
                x1 = bbox['x1'] * page_width
                y1 = bbox['y1'] * page_height

                # 텍스트 영역 생성
                text_rect = fitz.Rect(x0, y0, x1, y1)

                # 폰트 크기 계산 (영역에 맞게)
                rect_height = y1 - y0
                fontsize = rect_height * 0.8

                try:
                    # 투명 텍스트 삽입 (render_mode=3 = invisible)
                    rc = page.insert_textbox(
                        text_rect,
                        text,
                        fontsize=fontsize,
                        fontname="korea",
                        color=(0, 0, 0),
                        render_mode=3,  # invisible text
                        align=fitz.TEXT_ALIGN_LEFT
                    )
                    
                    # 텍스트가 박스에 다 들어가지 못한 경우(rc 반환값 있음), 폰트를 줄여서 재시도
                    if rc:
                        page.insert_textbox(
                            text_rect,
                            text,
                            fontsize=fontsize * 0.5,
                            fontname="korea",
                            color=(0, 0, 0),
                            render_mode=3,
                            align=fitz.TEXT_ALIGN_LEFT
                        )
                except Exception:
                    # 개별 블록 실패 시 무시
                    pass

    # PDF 저장
    output = io.BytesIO()
    doc.save(output, garbage=4, deflate=True)
    doc.close()

    return output.getvalue()


def format_result_plain(result):
    """결과를 플레인 텍스트로 포맷"""
    if result['pages']:
        output = ""
        for page in result['pages']:
            output += f"[Page {page['page_num']}]\n"
            output += f"{page['text']}\n\n"
        return output
    return result['text']
