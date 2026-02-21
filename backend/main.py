"""
GEMintern Web Backend - FastAPI + pywebview dual mode.

Usage:
    python -m backend.main          # Desktop (pywebview window)
    python -m backend.main --web    # Browser mode
    python -m backend.main --dev    # API-only for frontend dev
"""
import sys
import os
import argparse
import threading

# Add parent dir to path so core_*.py modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.api_routes import router as api_router
from backend.api_ws import websocket_endpoint

app = FastAPI(title="GEMintern API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    await websocket_endpoint(websocket)


# Serve built frontend (production mode)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


DEFAULT_PORT = 8741


def start_server(port: int = DEFAULT_PORT):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main():
    parser = argparse.ArgumentParser(description="GEMintern Web Backend")
    parser.add_argument("--web", action="store_true", help="Open in browser")
    parser.add_argument("--dev", action="store_true", help="API-only mode for frontend dev")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    args = parser.parse_args()

    port = args.port

    if args.dev:
        print(f"GEMintern API server running on http://localhost:{port}")
        print("Frontend dev server: cd frontend && npm run dev")
        uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)
    elif args.web:
        import webbrowser
        print(f"GEMintern running at http://localhost:{port}")
        print("Press Ctrl+C to stop.")
        webbrowser.open(f"http://localhost:{port}")
        uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)
    else:
        try:
            import webview
            server_thread = threading.Thread(target=start_server, args=(port,), daemon=True)
            server_thread.start()
            webview.create_window(
                "GEM Intern v7.0",
                f"http://localhost:{port}",
                width=1400, height=900, min_size=(1000, 700),
            )
            webview.start()
        except ImportError:
            print("pywebview not installed. Falling back to browser mode.")
            import webbrowser
            print(f"GEMintern running at http://localhost:{port}")
            print("Press Ctrl+C to stop.")
            webbrowser.open(f"http://localhost:{port}")
            uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
