import fitz  # PyMuPDF
import io
import concurrent.futures

# 이미지 전처리를 위한 PIL (Pillow) import
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Gemini 지원을 위한 선택적 import
try:
    from google import genai
    from google.genai import types
    OCR_AVAILABLE = True
    OCR_ERROR_MSG = ""
except ImportError:
    OCR_AVAILABLE = False
    OCR_ERROR_MSG = "google-genai 패키지가 설치되지 않았습니다."

def get_ocr_status():
    """OCR 상태 확인"""
    if OCR_AVAILABLE:
        return True, "Gemini Vision OCR 사용 가능 (API 키 필요)"
    return False, OCR_ERROR_MSG

def _process_single_page_ocr(client, page_num, img_bytes, original_text):
    """개별 페이지 OCR 처리 (병렬 실행용)"""
    try:
        # 표 인식률 향상을 위한 프롬프트 개선
        prompt = """
        이 이미지의 내용을 텍스트로 추출해줘.
        
        [핵심 요구사항]
        1. **표(Table) 변환**: 이미지 내의 표는 반드시 **Markdown 표 문법**(| 헤더 | 헤더 |\n|---|---|)을 사용하여 구조를 정확히 유지해야 해.
        2. **레이아웃 유지**: 제목, 단락, 리스트 구조를 원본과 유사하게 유지해줘.
        3. **불필요한 말 생략**: "이미지에서 추출한 텍스트입니다" 같은 서론 없이, **결과 텍스트만** 출력해.
        """
        
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=0.0  # 정확도 우선
            )
        )

        ocr_text = response.text.strip() if response.text else ""

        if ocr_text:
            return page_num, f"[Page {page_num + 1} - Vision OCR]\n{ocr_text}\n\n", True
        else:
            return page_num, f"[Page {page_num + 1}]\n{original_text}\n\n", False

    except Exception as e:
        return page_num, f"[Page {page_num + 1} - OCR Error: {str(e)}]\n{original_text}\n\n", False

def extract_pdf_with_gemini_ocr(doc, api_key, ocr_threshold=50):
    """
    PDF에서 텍스트 추출 (Gemini Vision OCR 병렬 처리)
    """
    page_results = {}  # 페이지 번호별 결과 저장 (순서 보장용)
    ocr_used = False
    ocr_tasks = []

    # 1단계: 일반 텍스트 추출 및 OCR 필요 페이지 수집
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()

        if len(page_text) < ocr_threshold:
            # OCR이 필요한 페이지 - 이미지로 변환
            # Matrix(2.0, 2.0)으로 해상도 2배 확대 (인식률 향상)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            
            img_bytes = None
            
            # [이미지 전처리] 인식률 향상을 위한 흑백 변환 및 대비/선명도 강조
            if PIL_AVAILABLE:
                try:
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    img = img.convert("L")  # 흑백 변환 (Grayscale)
                    img = ImageEnhance.Contrast(img).enhance(1.5)   # 대비 증가 (1.5배)
                    img = ImageEnhance.Sharpness(img).enhance(1.5)  # 선명도 증가 (1.5배)
                    
                    with io.BytesIO() as output:
                        img.save(output, format="PNG")
                        img_bytes = output.getvalue()
                except Exception:
                    pass  # 전처리 실패 시 원본 사용
            
            if img_bytes is None:
                img_bytes = pix.tobytes("png")
                
            ocr_tasks.append((page_num, img_bytes, page_text))
        else:
            page_results[page_num] = f"[Page {page_num + 1}]\n{page_text}\n\n"

    # 2단계: OCR 병렬 처리
    if ocr_tasks and api_key and OCR_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)

            # ThreadPoolExecutor로 병렬 처리 (최대 5개 동시 요청)
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_page = {
                    executor.submit(_process_single_page_ocr, client, p[0], p[1], p[2]): p[0]
                    for p in ocr_tasks
                }
                
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num, text, used = future.result()
                    page_results[page_num] = text
                    if used:
                        ocr_used = True

        except Exception as e:
            # 시스템 에러 시 남은 페이지들 원본 텍스트로 채우기
            for p_num, _, p_text in ocr_tasks:
                if p_num not in page_results:
                    page_results[p_num] = f"[Page {p_num + 1} - System Error]\n{p_text}\n\n"
    else:
        # OCR 불가능하거나 키가 없는 경우 원본 텍스트 사용
        for p_num, _, p_text in ocr_tasks:
            page_results[p_num] = f"[Page {p_num + 1}]\n{p_text}\n\n"
    
    # 3단계: 페이지 순서대로 텍스트 조립
    final_text = ""
    if ocr_used:
        final_text += "[Gemini Vision OCR 적용됨]\n\n"
        
    for i in range(len(doc)):
        if i in page_results:
            final_text += page_results[i]
            
    return final_text

def extract_pdf_with_ocr(doc):
    """레거시 호환 - API 키 없이 호출 시 일반 텍스트만 추출"""
    text_content = ""
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()
        text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"
    return text_content