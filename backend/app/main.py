"""PRAMAAN FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db import init_db
from backend.app.api.integrity import router as integrity_router
from backend.app.api.evidence import router as evidence_router
from backend.app.api.events import router as events_router
from backend.app.api.entities import router as entities_router
from backend.app.api.graph import router as graph_router
from backend.app.api.anomalies import router as anomalies_router
from backend.app.api.authenticity import router as authenticity_router
from backend.app.api.analyze import router as analyze_router
from backend.app.api.claims import router as claims_router
from backend.app.api.review import router as review_router
from backend.app.api.system import router as system_router
from backend.app.api.report import router as report_router
from backend.app.api.benchmark import router as benchmark_router
from backend.app.api.sequence import router as sequence_router
from backend.app.api.scene import router as scene_router
from backend.app.api.assistant import router as assistant_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and triggers
    init_db()
    yield


app = FastAPI(
    title="PRAMAAN Digital Forensics Engine",
    description="Offline, AI-Assisted Evidence Correlation & Crime Reconstruction Framework",
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for localhost Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(integrity_router)
app.include_router(evidence_router)
app.include_router(events_router)
app.include_router(entities_router)
app.include_router(graph_router)
app.include_router(anomalies_router)
app.include_router(authenticity_router)
app.include_router(analyze_router)
app.include_router(claims_router)
app.include_router(review_router)
app.include_router(system_router)
app.include_router(report_router)
app.include_router(benchmark_router)
app.include_router(sequence_router)
app.include_router(scene_router)
app.include_router(assistant_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "PRAMAAN",
        "mode": "offline",
        "synthetic_notice": "Synthetic case PRM-2026-0042. All persons and identifiers are fictional.",
    }
