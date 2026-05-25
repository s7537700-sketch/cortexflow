"""
CortexFlow Engine — Central execution runtime for the platform.

Orchestrates agent loading, pipeline execution, job queuing, and event
distribution across all platform components.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .pipeline import Pipeline, PipelineStage
from .queue import JobQueue
from .token_tracker import TokenTracker
from agents.orchestrator import OrchestratorAgent
from agents.code_analyzer import CodeAnalyzerAgent
from agents.vuln_scanner import VulnScannerAgent
from agents.exploit_suggester import ExploitSuggesterAgent
from agents.report_generator import ReportGeneratorAgent
from agents.base_agent import AgentContext

logger = logging.getLogger("cortexflow.engine")


class CortexFlowEngine:
    """Central engine that wires all platform components together."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.agents = {}
        self.pipelines = {}
        self.queue = JobQueue(max_concurrent=10)
        self.tracker = TokenTracker(
            self.config.get("token_tracking", {}))
        self._initialized = False

    async def initialize(self):
        """Load all agents and prepare the engine."""
        if self._initialized:
            return

        agent_config = self.config.get("agents", {})

        self.agents = {
            "orchestrator": OrchestratorAgent(
                agent_config.get("orchestrator", {})),
            "code_analyzer": CodeAnalyzerAgent(
                agent_config.get("code_analyzer", {})),
            "vuln_scanner": VulnScannerAgent(
                agent_config.get("vuln_scanner", {})),
            "exploit_suggester": ExploitSuggesterAgent(
                agent_config.get("exploit_suggester", {})),
            "report_generator": ReportGeneratorAgent(
                agent_config.get("report_generator", {})),
        }

        logger.info(f"Engine initialized with {len(self.agents)} agents")
        self._initialized = True

    def create_pipeline(self, name: str = "default") -> Pipeline:
        """Create and configure a standard analysis pipeline."""
        pipeline = Pipeline()

        stages = [
            PipelineStage(
                name="orchestrator",
                agent=self.agents["orchestrator"],
                timeout=300,
            ),
            PipelineStage(
                name="code_analyzer",
                agent=self.agents["code_analyzer"],
                timeout=180,
                depends_on=["orchestrator"],
            ),
            PipelineStage(
                name="vuln_scanner",
                agent=self.agents["vuln_scanner"],
                timeout=240,
                depends_on=["code_analyzer"],
            ),
            PipelineStage(
                name="exploit_suggester",
                agent=self.agents["exploit_suggester"],
                timeout=300,
                depends_on=["vuln_scanner"],
            ),
            PipelineStage(
                name="report_generator",
                agent=self.agents["report_generator"],
                timeout=120,
                depends_on=["exploit_suggester"],
            ),
        ]

        for stage in stages:
            pipeline.add_stage(stage)

        self.pipelines[name] = pipeline
        return pipeline

    async def analyze(self, input_data: dict,
                      pipeline_name: str = "default",
                      session_id: str = None) -> dict:
        """Run a full analysis pipeline on input data.

        Args:
            input_data: Analysis request with type, target, content.
            pipeline_name: Which pipeline configuration to use.
            session_id: Optional session identifier.

        Returns:
            Complete analysis results from all agents.
        """
        await self.initialize()
        session_id = session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline:
            pipeline = self.create_pipeline(pipeline_name)

        context = AgentContext(
            session_id=session_id,
            input_data=input_data,
            config=self.config,
        )

        results = await pipeline.execute(context.__dict__)

        for stage_name, stage_result in results.get("results", {}).items():
            if isinstance(stage_result, dict):
                self.tracker.log(
                    agent=stage_name,
                    prompt=stage_result.get("prompt_tokens", 0),
                    completion=stage_result.get("completion_tokens", 0),
                    model=self.config.get("agents", {}).get(stage_name, {}).get("model", "default"),
                    session_id=session_id,
                )

        return {
            "success": len(results.get("failed", [])) == 0,
            "session_id": session_id,
            "pipeline": pipeline_name,
            "results": results,
            "token_usage": self.tracker.summary(),
        }

    def get_agent_info(self) -> list:
        return [
            {"name": name, "info": agent.get_info()}
            for name, agent in self.agents.items()
        ]

    def get_token_summary(self) -> dict:
        return self.tracker.summary()

    def get_queue_stats(self) -> dict:
        return self.queue.stats()
