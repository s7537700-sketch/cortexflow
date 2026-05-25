"""
CortexFlow API Server — FastAPI-based REST interface for the platform.

Provides:
- POST /api/v1/analyze — Submit analysis jobs
- GET  /api/v1/jobs/{id} — Check job status
- GET  /api/v1/agents  — List available agents
- GET  /api/v1/tokens  — Token usage dashboard
- WS  /api/v1/ws      — Real-time job updates
"""

import logging
from typing import Optional
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.engine import CortexFlowEngine

logger = logging.getLogger("cortexflow.api")

engine = CortexFlowEngine()


class AnalyzeRequest(BaseModel):
    type: str = "codebase"
    target: str = ""
    content: str = ""
    pipeline: str = "default"
    priority: int = 5
    complexity: str = "medium"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CortexFlow API server")
    await engine.initialize()
    engine.create_pipeline("default")
    await engine.queue.start()
    yield
    await engine.queue.stop()
    logger.info("CortexFlow API server stopped")


app = FastAPI(
    title="CortexFlow API",
    version="1.0.0",
    description="Multi-Agent AI Orchestration Platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "CortexFlow",
        "version": "1.0.0",
        "status": "running",
        "agents": len(engine.agents),
    }


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "agents_loaded": len(engine.agents),
        "pipelines": list(engine.pipelines.keys()),
        "queue": engine.get_queue_stats(),
    }


@app.post("/api/v1/analyze")
async def analyze(request: AnalyzeRequest):
    job_id = await engine.queue.enqueue(
        name=request.target or "analysis",
        pipeline_config=request.model_dump(),
        priority=request.priority,
    )
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Analysis job {job_id} queued",
        "estimated_tokens": 100000,
    }


@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    job = engine.queue.get_status(job_id)
    if not job:
        return {"error": "Job not found"}, 404
    return {
        "id": job.id,
        "name": job.name,
        "status": job.status.value,
        "progress": job.progress,
        "created_at": job.created_at,
        "tokens_used": job.tokens_used,
    }


@app.get("/api/v1/agents")
async def list_agents():
    return {
        "agents": engine.get_agent_info(),
        "total": len(engine.agents),
    }


@app.get("/api/v1/tokens")
async def get_tokens():
    return engine.get_token_summary()


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")

    async def send_updates(event: str, job):
        await websocket.send_json({
            "event": event,
            "job_id": job.id,
            "status": job.status.value,
            "progress": job.progress,
        })

    engine.queue.subscribe(send_updates)

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"echo": data})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


@app.post("/api/v1/analyze/sync")
async def analyze_sync(request: AnalyzeRequest):
    """Run analysis synchronously and return results."""
    result = await engine.analyze(
        input_data=request.model_dump(),
        pipeline_name=request.pipeline,
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
