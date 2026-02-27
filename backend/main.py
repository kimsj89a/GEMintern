"""
GEMintern Web Backend - FastAPI localhost server.

Usage:
    python -m backend.main          # Browser mode (default)
    python -m backend.main --dev    # API-only for frontend dev
"""
import sys
import os
import argparse
import webbrowser

# Add parent dir to path so core_*.py modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.api_routes import router as api_router
from backend.auth_routes import router as auth_router
from backend.api_ws import websocket_endpoint
from backend.database import init_db

app = FastAPI(title="GEMintern API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    init_db()


@app.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    await websocket_endpoint(websocket)


# Serve built frontend (production mode)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


DEFAULT_PORT = 8741


def main():
    parser = argparse.ArgumentParser(description="GEMintern Web Backend")
    parser.add_argument("--dev", action="store_true", help="API-only mode for frontend dev")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--web", action="store_true", help="(deprecated, now default)")
    args = parser.parse_args()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", args.port))
    is_railway = os.environ.get("RAILWAY_ENVIRONMENT")

    if args.dev:
        print(f"GEMintern API server running on http://localhost:{port}")
        print("Frontend dev server: cd frontend && npm run dev")
        uvicorn.run("backend.main:app", host=host, port=port, reload=False)
    else:
        print(f"GEMintern running at http://{host}:{port}")
        print("Press Ctrl+C to stop.")
        if not is_railway:
            webbrowser.open(f"http://localhost:{port}")
        uvicorn.run("backend.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
