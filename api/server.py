"""
CortexFlow REST API — FastAPI application with auth, WebSocket, and pipeline endpoints.

Start:
    uvicorn api.server:app --host 0.0.0.0 --port 8000
    cortexflow serve
"""

import logging
import json
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = None

logger = logging.getLogger("cortexflow.api")

# ── Engine singleton ────────────────────────────────────────────
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from core.engine import CortexFlowEngine
        import os

        # Build config from env
        provider_cfg = None
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MIMO_API_KEY")
        if api_key:
            provider_type = os.environ.get("CORTEXFLOW_PROVIDER", "anthropic")
            base_url = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("MIMO_BASE_URL")
            model = os.environ.get("CORTEXFLOW_MODEL", "")
            provider_cfg = {
                "type": provider_type,
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
            }

        _engine = CortexFlowEngine(config={"provider": provider_cfg})
    return _engine


# ── Pydantic models (only if FastAPI available) ─────────────────

if HAS_FASTAPI:

    class AnalysisRequest(BaseModel):
        target: str
        content: Optional[str] = None
        type: Optional[str] = "default"
        pipeline: Optional[str] = "default"
        agents: Optional[list[str]] = None
        session_id: Optional[str] = None

    class AnalysisResponse(BaseModel):
        success: bool
        session_id: str
        pipeline: str
        results: dict = {}
        token_usage: dict = {}

    class AuthRequest(BaseModel):
        user_id: int
        role: str = "analyst"

    class TokenResponse(BaseModel):
        token: str
        expires_in: str = "24h"

    # ── App ─────────────────────────────────────────────────────

    app = FastAPI(
        title="CortexFlow",
        description="Multi-Agent AI Orchestration Platform for Security Analysis",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health / info ───────────────────────────────────────────

    @app.get("/")
    async def root():
        return {
            "name": "CortexFlow",
            "version": "2.0.0",
            "status": "running",
            "docs": "/docs",
        }

    @app.get("/health")
    async def health():
        engine = _get_engine()
        await engine.initialize()
        return {
            "status": "healthy",
            "agents": len(engine.agents),
            "provider": "active" if engine.provider else "none",
            "storage": "active" if engine.db else "none",
        }

    # ── Analysis ────────────────────────────────────────────────

    @app.post("/analyze", response_model=AnalysisResponse)
    async def run_analysis(req: AnalysisRequest):
        engine = _get_engine()
        input_data = {
            "target": req.target,
            "content": req.content or "",
            "type": req.type or "default",
        }
        try:
            result = await engine.analyze(
                input_data=input_data,
                pipeline_name=req.pipeline or "default",
                agent_names=req.agents,
                session_id=req.session_id,
            )
            return AnalysisResponse(**result)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ── Agents ──────────────────────────────────────────────────

    @app.get("/agents")
    async def list_agents():
        engine = _get_engine()
        await engine.initialize()
        return {"agents": engine.get_agent_info()}

    # ── Tokens ──────────────────────────────────────────────────

    @app.get("/tokens/stats")
    async def token_stats():
        engine = _get_engine()
        return engine.get_token_summary()

    # ── Auth ────────────────────────────────────────────────────

    @app.post("/auth/token")
    async def create_token(req: AuthRequest):
        from api.auth import get_auth
        auth = get_auth()
        token = auth.create_token(user_id=req.user_id, role=req.role)
        return TokenResponse(token=token)

    @app.get("/auth/verify")
    async def verify_token(token: str):
        from api.auth import get_auth
        auth = get_auth()
        payload = auth.verify_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return payload

    # ── Queue ───────────────────────────────────────────────────

    @app.get("/queue/stats")
    async def queue_stats():
        engine = _get_engine()
        return engine.get_queue_stats()

    @app.post("/queue/enqueue")
    async def enqueue_job(name: str, pipeline: str = "default", priority: int = 5):
        engine = _get_engine()
        await engine.queue.start()
        job_id = await engine.queue.enqueue(
            name=name,
            pipeline_config={"pipeline": pipeline},
            priority=priority,
        )
        return {"job_id": job_id, "status": "queued"}

    # ── WebSocket ───────────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                data = await ws.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    await ws.send_text(json.dumps({"error": "invalid JSON"}))
                    continue

                action = msg.get("action", "")
                if action == "analyze":
                    engine = _get_engine()
                    result = await engine.analyze(
                        input_data=msg.get("input", {}),
                        pipeline_name=msg.get("pipeline", "default"),
                    )
                    await ws.send_text(json.dumps(result, default=str))
                elif action == "ping":
                    await ws.send_text(json.dumps({"action": "pong"}))
                else:
                    await ws.send_text(
                        json.dumps({"error": f"unknown action: {action}"}))
        except WebSocketDisconnect:
            pass

    # ── Plugins ─────────────────────────────────────────────────

    @app.get("/plugins")
    async def list_plugins():
        engine = _get_engine()
        await engine.initialize()
        if engine.plugins:
            return {"plugins": engine.plugins.list_plugins()}
        return {"plugins": [], "note": "Plugin system not active"}

else:
    app = None
