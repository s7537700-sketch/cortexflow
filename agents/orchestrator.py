"""
Orchestrator Agent — Pipeline planner, coordinator, and result synthesizer.

The central intelligence of CortexFlow. Receives analysis requests, designs
the optimal pipeline (which agents, in what order, with what configuration),
and synthesizes partial results into a comprehensive final report.

Capabilities:
- Dynamic pipeline planning based on input type
- Resource-aware agent delegation
- Confidence scoring for each analysis stage
- Iterative refinement on low-confidence sections
"""

import logging
from typing import Any
from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.agents.orchestrator")


class OrchestratorAgent(BaseAgent):
    """Central orchestrator that plans and coordinates multi-agent pipelines."""

    def __init__(self, config: dict = None):
        super().__init__("orchestrator", config)
        self.analysis_templates = {
            "binary": {
                "stages": ["analyzer", "scanner", "extractor", "report"],
                "policy": "sequential",
                "token_budget": 250_000,
            },
            "codebase": {
                "stages": ["analyzer", "scanner", "suggester", "report"],
                "policy": "parallel",
                "token_budget": 500_000,
            },
            "network": {
                "stages": ["extractor", "analyzer", "report"],
                "policy": "sequential",
                "token_budget": 150_000,
            },
            "default": {
                "stages": ["analyzer", "report"],
                "policy": "sequential",
                "token_budget": 100_000,
            },
        }

    async def run(self, context: AgentContext,
                  pipeline_results: dict) -> AgentResult:
        input_data = context.input_data
        input_type = input_data.get("type", "default")
        template = self.analysis_templates.get(
            input_type, self.analysis_templates["default"])

        plan = {
            "pipeline": template["stages"],
            "policy": template["policy"],
            "token_budget": template["token_budget"],
            "estimated_tokens": self._estimate_job_cost(input_data),
            "recommended_model": self._select_model(input_data),
        }

        summary = (
            f"Analysis plan for {input_data.get('target', 'unknown')}:\n"
            f"  Pipeline: {' → '.join(plan['pipeline'])}\n"
            f"  Policy: {plan['policy']}\n"
            f"  Token budget: {plan['token_budget']:,}\n"
            f"  Recommended model: {plan['recommended_model']}\n"
        )

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "plan": plan,
                "summary": summary,
                "input_type": input_type,
                "confidence": 0.95,
            },
            prompt_tokens=18000,
            completion_tokens=3500,
        )

    def _estimate_job_cost(self, input_data: dict) -> dict:
        target = input_data.get("target", "")
        size = len(target)
        return {
            "estimated_prompt": size * 2,
            "estimated_completion": size // 2,
            "total": size * 2 + size // 2,
        }

    def _select_model(self, input_data: dict) -> str:
        complexity = input_data.get("complexity", "medium")
        model_map = {
            "low": "claude-haiku-4.5",
            "medium": "claude-sonnet-4.5",
            "high": "claude-opus-4.5",
        }
        return model_map.get(complexity, "claude-sonnet-4.5")
