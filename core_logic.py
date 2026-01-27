from google import genai
from google.genai import types
import utils
import core_rfi
import core_chained
import prompts

def get_client(api_key):
    return genai.Client(api_key=api_key)

def extract_structure(api_key, structure_file):
    try:
        client = get_client(api_key)
        file_text = utils.parse_uploaded_file(structure_file, api_key=api_key)
        prompt = f"{prompts.LOGIC_PROMPTS['structure_extraction']}\n[?뚯씪 ?댁슜]\n{file_text[:15000]}"
        resp = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return resp.text
    except Exception as e:
        return f"援ъ“ 異붿텧 ?ㅻ쪟: {str(e)}"

def parse_all_files(uploaded_files, read_content=True, api_key=None, docai_config=None, template_option=None):
    """?뚯씪 紐⑸줉 ?뚯떛 (OCR 吏??

    Args:
        uploaded_files: ?낅줈?쒕맂 ?뚯씪 紐⑸줉
        read_content: ?뚯씪 ?댁슜 ?쎄린 ?щ?
        api_key: Google API ??(Gemini OCR??
        docai_config: Document AI ?ㅼ젙 (?좏깮?ы빆)
    """
    all_text = ""
    file_list_str = ""
    if uploaded_files:
        for file in uploaded_files:
            file_list_str += f"- {file.name}\n"
            if read_content:
                parsed = utils.parse_uploaded_file(
                    file,
                    api_key=api_key,
                    docai_config=docai_config,
                    template_option=template_option,
                )
                all_text += parsed

    if not read_content:
        all_text = "(RFI 紐⑤뱶: ?댁슜???쎌? ?딆쓬)"

    return all_text, file_list_str

def get_default_structure(template_key):
    return prompts.TEMPLATE_STRUCTURES.get(template_key, "")

def _get_system_prompt(template_opt):
    """?쒗뵆由용퀎 ?쒖뒪???꾨＼?꾪듃 諛섑솚"""
    prompt_map = {
        'simple_review': 'simple_review_system',
        'investment': 'investment_system',
        'im': 'im_system',
        'management': 'management_system',
        'presentation': 'ppt_system',
        'custom': 'custom_system'
    }
    prompt_key = prompt_map.get(template_opt, 'custom_system')
    return prompts.LOGIC_PROMPTS.get(prompt_key, prompts.LOGIC_PROMPTS['custom_system'])

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    """Single-pass generation mode for all templates."""
    client = get_client(api_key)
    template_opt = inputs['template_option']
    structure_text = inputs['structure_text']

    # [RFI Mode] - 蹂꾨룄 泥섎━
    if template_opt == 'rfi':
        stream = core_rfi.generate_rfi_stream(api_key, model_name, inputs, thinking_level)
        for chunk in stream:
            yield chunk
        return

    # ?쒗뵆由용퀎 ?쒖뒪???꾨＼?꾪듃 媛?몄삤湲?
    system_instruction = _get_system_prompt(template_opt)

    # ?꾩떇???듭뀡 異붽?
    if inputs.get('use_diagram'):
        system_instruction += "\n**?꾩떇??*: ?꾩슂??{{DIAGRAM: ?ㅻ챸}} ?쒓렇 ?쎌엯."

    # Main prompt composition
    thinking_label = thinking_level.upper() if isinstance(thinking_level, str) else "HIGH"
    main_prompt = f"""
[System: Thinking Level {thinking_label}]
[Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.

[Document Structure]
{structure_text}

[User Context]
{inputs['context_text']}

[Source Data]
{file_context[:50000]}
"""

    # ?쒗뵆由용퀎 config ?ㅼ젙
    if template_opt == 'presentation':
        temperature = 0.7
    elif template_opt == 'custom':
        temperature = 0.7  # ?먯쑀 援ъ“??紐⑤뱶 - 李쎌쓽??援ъ“?붾? ?꾪빐 ?믪? temperature
    else:
        temperature = 0.3

    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=temperature,
        system_instruction=system_instruction
    )

    # Generate Stream
    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=main_prompt,
        config=config
    )

    for chunk in response_stream:
        yield chunk

def generate_report_stream_chained(api_key, model_name, inputs, thinking_level, file_context):
    """Chained prompting via core_chained."""
    template_option = inputs.get('template_option', 'investment')

    # core_chained 紐⑤뱢???쇰컲?붾맂 ?⑥닔 ?ъ슜
    for chunk in core_chained.generate_chained_stream(
        api_key=api_key,
        model_name=model_name,
        inputs=inputs,
        thinking_level=thinking_level,
        file_context=file_context,
        template_option=template_option
    ):
        yield chunk


def refine_report(api_key, model_name, current_text, refine_query):
    client = get_client(api_key)
    refine_prompt = (
        f"You are a document refinement assistant.\n"
        f"Apply the user's request to the existing document without losing structure.\n"
        f"User request: \"{refine_query}\"\n"
        f"Write the updates under the heading: ## Additional Request Applied\n"
        f"Existing document (truncated): {current_text[:20000]}...\n"
    )
    resp = client.models.generate_content(model=model_name, contents=refine_prompt)
    return resp.text


