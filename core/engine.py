"""
CortexFlow Engine — Central execution runtime for the platform.

Orchestrates agent loading, pipeline execution, job queuing, and event
distribution across all platform components.

v2.0: wires all 10 agents, multi-provider LLM, storage, auth, plugins.
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .pipeline import Pipeline, PipelineStage
from .queue import JobQueue
from .token_tracker import TokenTracker
from .plugin_manager import PluginManager

from agents.base_agent import AgentContext
from agents.orchestrator import OrchestratorAgent
from agents.code_analyzer import CodeAnalyzerAgent
from agents.vuln_scanner import VulnScannerAgent
from agents.exploit_suggester import ExploitSuggesterAgent
from agents.report_generator import ReportGeneratorAgent
from agents.config_extractor import ConfigExtractorAgent
from agents.memory_forensics import MemoryForensicsAgent
from agents.monitor_agent import MonitorAgent
from agents.network_analyzer import NetworkAnalyzerAgent
from agents.threat_intel import ThreatIntelAgent

from providers.base import ProviderConfig, ProviderType
from providers.factory import ProviderFactory, set_default_provider

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
        self.provider = None
        self.db = None
        self.auth = None
        self.plugins = None
        self._initialized = False

    async def initialize(self):
        """Load all agents, provider, storage, auth, and plugins."""
        if self._initialized:
            return

        agent_config = self.config.get("agents", {})

        # ── 10 specialized agents ──
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
            "config_extractor": ConfigExtractorAgent(
                agent_config.get("config_extractor", {})),
            "memory_forensics": MemoryForensicsAgent(
                agent_config.get("memory_forensics", {})),
            "monitor_agent": MonitorAgent(
                agent_config.get("monitor_agent", {})),
            "network_analyzer": NetworkAnalyzerAgent(
                agent_config.get("network_analyzer", {})),
            "threat_intel": ThreatIntelAgent(
                agent_config.get("threat_intel", {})),
        }

        # ── LLM provider ──
        provider_cfg = self.config.get("provider", None)
        if provider_cfg:
            ptype = ProviderType(provider_cfg["type"])
            pcfg = ProviderConfig(
                provider_type=ptype,
                api_key=provider_cfg["api_key"],
                base_url=provider_cfg.get("base_url"),
                model=provider_cfg.get("model", ""),
                max_tokens=provider_cfg.get("max_tokens", 4096),
                temperature=provider_cfg.get("temperature", 0.7),
            )
            self.provider = ProviderFactory.create(pcfg)
            set_default_provider(self.provider)
            logger.info(f"Provider ready: {self.provider.get_info()}")

        # ── Storage ──
        try:
            from storage.database import init_db
            db_url = self.config.get("db_url", "sqlite:///./data/cortexflow.db")
            self.db = init_db(db_url)
            logger.info("Storage initialized")
        except ImportError:
            logger.warning("sqlalchemy not installed — storage disabled")

        # ── Auth ──
        try:
            from api.auth import get_auth, get_rbac
            self.auth = get_auth()
            self.rbac = get_rbac()
            logger.info("Auth service ready")
        except ImportError:
            logger.warning("Auth dependencies missing — auth disabled")

        # ── Plugins ──
        plugin_dir = Path(self.config.get("plugin_dir", "plugins"))
        if plugin_dir.is_dir():
            self.plugins = PluginManager(str(plugin_dir))
            self.plugins.discover()
            logger.info(f"Plugins loaded: {len(self.plugins.list_plugins())}")

        logger.info(
            f"Engine initialized: {len(self.agents)} agents, "
            f"provider={'yes' if self.provider else 'no'}, "
            f"storage={'yes' if self.db else 'no'}, "
            f"auth={'yes' if self.auth else 'no'}, "
            f"plugins={'yes' if self.plugins else 'no'}"
        )
        self._initialized = True

    def create_pipeline(self, name: str = "default",
                        agent_names: Optional[list[str]] = None) -> Pipeline:
        """Create and configure an analysis pipeline.

        If agent_names is provided, build a custom pipeline from those agents.
        Otherwise builds the default 5-stage sequential pipeline.
        """
        pipeline = Pipeline()

        if agent_names is None:
            agent_names = [
                "orchestrator", "code_analyzer", "vuln_scanner",
                "exploit_suggester", "report_generator",
            ]

        prev_stage = None
        for aname in agent_names:
            if aname not in self.agents:
                logger.warning(f"Agent '{aname}' not found, skipping")
                continue

            depends = [prev_stage] if prev_stage else []
            stage = PipelineStage(
                name=aname,
                agent=self.agents[aname],
                timeout=self.config.get(
                    "agents", {}).get(aname, {}).get("timeout", 300),
                depends_on=depends,
            )
            pipeline.add_stage(stage)
            prev_stage = aname

        self.pipelines[name] = pipeline
        return pipeline

    async def analyze(self, input_data: dict,
                      pipeline_name: str = "default",
                      agent_names: Optional[list[str]] = None,
                      session_id: str = None) -> dict:
        """Run a full analysis pipeline on input data.

        Args:
            input_data: Analysis request with type, target, content.
            pipeline_name: Which pipeline configuration to use.
            agent_names: Optional custom agent list (overrides pipeline).
            session_id: Optional session identifier.

        Returns:
            Complete analysis results from all agents.
        """
        await self.initialize()
        session_id = session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        pipeline = self.pipelines.get(pipeline_name)
        if not pipeline or agent_names:
            pipeline = self.create_pipeline(pipeline_name, agent_names)

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
                    model=self.config.get("agents", {}).get(
                        stage_name, {}).get("model", "default"),
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
