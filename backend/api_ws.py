"""WebSocket handler for streaming AI generation."""
import asyncio
import json
import uuid
import threading
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict


# Active tasks: task_id -> { "status", "chunks", "result", "error" }
_tasks: Dict[str, dict] = {}


def _save_task_history(task: dict, result_text: str):
    """완료된 task의 결과를 generation_history에 저장한다."""
    user_id = task.get("_user_id")
    if not user_id:
        return
    try:
        from backend.database import save_generation
        save_generation(
            user_id=user_id,
            endpoint=task.get("_endpoint", ""),
            title=task.get("_title", ""),
            model=task.get("_model"),
            inputs=task.get("_inputs"),
            result_text=result_text,
        )
    except Exception as e:
        print(f"[history] save error: {e}")


def get_task(task_id: str) -> dict:
    return _tasks.get(task_id, {})


def create_task(user_id: int | None = None, endpoint: str = "",
                model: str = "", title: str = "",
                inputs: dict | None = None) -> str:
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "status": "pending", "chunks": [], "result": None, "error": None,
        "_user_id": user_id, "_endpoint": endpoint,
        "_model": model, "_title": title, "_inputs": inputs,
    }
    return task_id


def run_generate_task(task_id: str, api_key: str, model_name: str,
                      inputs: dict, thinking_level: str, file_context: str,
                      mode: str = "single"):
    """Run AI generation in a background thread, storing chunks."""
    import core_logic

    task = _tasks[task_id]
    task["status"] = "generating"

    def _run():
        try:
            if mode == "chained":
                stream = core_logic.generate_report_stream_chained(
                    api_key, model_name, inputs, thinking_level, file_context
                )
            else:
                stream = core_logic.generate_report_stream(
                    api_key, model_name, inputs, thinking_level, file_context
                )
            full_text = ""
            for chunk in stream:
                text = ""
                if hasattr(chunk, "text"):
                    text = chunk.text or ""
                elif isinstance(chunk, str):
                    text = chunk
                if text:
                    full_text += text
                    task["chunks"].append(text)
            task["result"] = full_text
            task["status"] = "complete"
            _save_task_history(task, full_text)
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "error"

    threading.Thread(target=_run, daemon=True).start()


def run_analysis_task(task_id: str, task_type: str, api_key: str,
                      model_name: str, **kwargs):
    """Run analysis in background thread."""
    import core_logic

    task = _tasks[task_id]
    task["status"] = "generating"
    task["partial_slides"] = []  # For slide streaming

    def _run():
        try:
            fn_map = {
                "material_summary": core_logic.generate_material_summary,
                "qa_answer": core_logic.generate_qa_answer,
                "followup_questions": core_logic.generate_followup_questions,
                "additional_questions": core_logic.generate_additional_questions,
                "followup_analysis": core_logic.generate_followup_analysis,
                "checklist_eval": core_logic.evaluate_checklist_item,
                "dd_issues": core_logic.analyze_dd_issues,
                "slide_json": core_logic.generate_slide_json,
                "slide_regenerate": core_logic.regenerate_single_slide,
                "refine": core_logic.refine_report_with_context,
            }
            fn = fn_map.get(task_type)
            if not fn:
                raise ValueError(f"Unknown task type: {task_type}")

            # Slide streaming mode
            if task_type == "slide_json":
                def on_slide(slide_obj, index):
                    task["partial_slides"].append(slide_obj)
                    # Push via chunks list (WebSocket picks these up)
                    task["chunks"].append(json.dumps(
                        {"type": "slide", "slide": slide_obj, "index": index},
                        ensure_ascii=False
                    ))
                result = fn(api_key, model_name, on_slide=on_slide, **kwargs)
            else:
                result = fn(api_key, model_name, **kwargs)

            task["result"] = result
            task["status"] = "complete"
            result_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
            _save_task_history(task, result_text)
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "error"

    threading.Thread(target=_run, daemon=True).start()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming task results."""
    # Authenticate via ?token= query parameter
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    try:
        from backend.auth import decode_token
        decode_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    subscribed_tasks: set = set()

    try:
        while True:
            # Check for client messages (non-blocking)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                msg_type = data.get("type")
                if msg_type == "subscribe":
                    subscribed_tasks.add(data["task_id"])
                elif msg_type == "unsubscribe":
                    subscribed_tasks.discard(data["task_id"])
            except asyncio.TimeoutError:
                pass

            # Push updates for subscribed tasks
            for task_id in list(subscribed_tasks):
                task = _tasks.get(task_id)
                if not task:
                    continue

                # Send pending chunks
                while task["chunks"]:
                    chunk = task["chunks"].pop(0)
                    await websocket.send_json({
                        "type": "chunk", "task_id": task_id, "data": chunk
                    })

                # Send completion/error
                if task["status"] == "complete":
                    await websocket.send_json({
                        "type": "complete", "task_id": task_id,
                        "result": task["result"]
                    })
                    subscribed_tasks.discard(task_id)
                elif task["status"] == "error":
                    await websocket.send_json({
                        "type": "error", "task_id": task_id,
                        "error": task["error"]
                    })
                    subscribed_tasks.discard(task_id)

            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        pass
