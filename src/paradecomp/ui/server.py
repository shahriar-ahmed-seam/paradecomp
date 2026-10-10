"""FastAPI developer console server and Anti-AI-slop telemetry workbench."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from paradecomp import __version__
from paradecomp.analyzer.independence import SubtaskIndependenceAnalyzer
from paradecomp.benchmarks.runner import BenchmarkRunner
from paradecomp.core.models import SubtaskContract
from paradecomp.workloads.deep_research import DeepResearchEngine, ResearchFacet

app = FastAPI(
    title="ParaDecomp Telemetry Workbench",
    description="Anti-AI-slop developer telemetry console and scatter-gather visualizer.",
    version=__version__,
)

_runner = BenchmarkRunner()
_engine = DeepResearchEngine()
_HTML_PATH = Path(__file__).parent / "dashboard.html"


class AnalyzeRequest(BaseModel):
    subtasks: List[str] = Field(
        default=[
            "High-NA EUV: Optics numerical aperture scaling",
            "GAA Nanosheet: Inner spacer etch selectivity",
            "Backside Power: Buried power rail routing",
            "Advanced Packaging: Direct Cu-Cu hybrid bonding",
        ]
    )
    threshold: float = Field(default=0.70, ge=0.0, le=1.0)


class ResearchRequest(BaseModel):
    topic: str = "High-Breadth Sub-2nm Lithography Scaling"
    num_facets: int = Field(default=10, ge=1, le=20)
    sources_per_facet: int = Field(default=30, ge=5, le=50)


@app.get("/", response_class=HTMLResponse)
async def get_dashboard() -> str:
    """Serve developer telemetry workbench."""
    if _HTML_PATH.exists():
        content = _HTML_PATH.read_text(encoding="utf-8")
        return content.replace("v0.1.0", f"v{__version__}")
    return "<h1>ParaDecomp Telemetry Workbench</h1>"


@app.post("/api/analyze")
async def analyze_endpoint(req: AnalyzeRequest) -> Dict[str, Any]:
    """Execute mathematical independence analysis."""
    analyzer = SubtaskIndependenceAnalyzer(threshold=req.threshold)
    contracts = [
        SubtaskContract(
            subtask_id=f"st_{i}",
            parent_task_id="task_api",
            title=st.split(":")[0].strip() if ":" in st else f"Task {i}",
            query_or_instruction=st.split(":")[1].strip() if ":" in st else st,
        )
        for i, st in enumerate(req.subtasks)
    ]
    matrix = analyzer.analyze_matrix(contracts)
    return matrix.model_dump()


@app.get("/api/benchmark")
async def benchmark_endpoint() -> Dict[str, Any]:
    """Execute comparative benchmark."""
    report = await _runner.run(num_facets=10, sources_per_facet=30, simulated_io_ms=10.0)
    return report.model_dump()


@app.post("/api/research")
async def research_endpoint(req: ResearchRequest) -> Dict[str, Any]:
    """Run high-breadth deep research workload."""
    facets = [
        ResearchFacet(
            facet_id=f"f_{i:02d}",
            title=f"{req.topic} Facet {i:02d}",
            query=f"Query {i:02d} on {req.topic}",
            expected_sources=req.sources_per_facet,
        )
        for i in range(req.num_facets)
    ]
    try:
        output = await _engine.run(req.topic, facets)
        return output.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
