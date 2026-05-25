"""
Pipeline — Multi-stage workflow builder and executor.

Defines the analysis pipeline as a directed acyclic graph (DAG) of
agent stages, each with configurable inputs, outputs, and execution
policy (sequential, parallel, conditional).
"""

import asyncio
import logging
from enum import Enum
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("cortexflow.pipeline")


class StagePolicy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FALLBACK = "fallback"


@dataclass
class PipelineStage:
    name: str
    agent: Any
    policy: StagePolicy = StagePolicy.SEQUENTIAL
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    timeout: int = 300
    retry_count: int = 2
    depends_on: list[str] = field(default_factory=list)
    condition: Optional[Callable] = None
    fallback_agent: Optional[Any] = None


class Pipeline:
    """DAG-based pipeline executor for multi-stage agent workflows."""

    def __init__(self):
        self.stages: dict[str, PipelineStage] = {}
        self._results: dict[str, Any] = {}
        self._errors: dict[str, str] = {}

    def add_stage(self, stage: PipelineStage) -> "Pipeline":
        self.stages[stage.name] = stage
        return self

    def remove_stage(self, name: str) -> "Pipeline":
        self.stages.pop(name, None)
        return self

    def get_execution_order(self) -> list[str]:
        """Topological sort of stages based on dependencies."""
        visited = set()
        order = []

        def dfs(name):
            if name in visited:
                return
            visited.add(name)
            stage = self.stages.get(name)
            if stage:
                for dep in stage.depends_on:
                    dfs(dep)
                order.append(name)

        for name in self.stages:
            if name not in visited:
                dfs(name)
        return order

    async def execute(self, context: dict) -> dict:
        """Execute all pipeline stages in dependency order."""
        order = self.get_execution_order()
        logger.info(f"Pipeline execution order: {order}")

        for stage_name in order:
            stage = self.stages[stage_name]
            if self._should_skip(stage):
                logger.info(f"Skipping stage: {stage_name}")
                continue

            logger.info(f"Executing stage: {stage_name} (policy={stage.policy.value})")
            try:
                result = await asyncio.wait_for(
                    stage.agent.run(context, self._results),
                    timeout=stage.timeout,
                )
                self._results[stage_name] = result
                logger.info(f"Stage {stage_name} completed")
            except asyncio.TimeoutError:
                logger.error(f"Stage {stage_name} timed out after {stage.timeout}s")
                self._errors[stage_name] = "timeout"
                if stage.fallback_agent:
                    logger.info(f"Running fallback for {stage_name}")
                    self._results[stage_name] = await stage.fallback_agent.run(
                        context, self._results)
            except Exception as e:
                logger.error(f"Stage {stage_name} failed: {e}")
                self._errors[stage_name] = str(e)

        return {
            "results": self._results,
            "errors": self._errors,
            "completed": [s for s in order if s not in self._errors],
            "failed": list(self._errors.keys()),
        }

    def _should_skip(self, stage: PipelineStage) -> bool:
        """Check if stage should be skipped based on condition."""
        if stage.condition and not stage.condition(self._results):
            return True
        for dep in stage.depends_on:
            if dep in self._errors:
                return True
        return False

    def parallel_group(self, group_name: str,
                       stages: list[PipelineStage]) -> Pipeline:
        """Group stages for parallel execution."""
        group_dep = list(set(
            d for s in stages for d in s.depends_on if d not in [g.name for g in stages]
        ))
        wrapper = PipelineStage(
            name=group_name,
            agent=None,
            policy=StagePolicy.PARALLEL,
            depends_on=group_dep,
        )
        self.stages[group_name] = wrapper
        for stage in stages:
            stage.depends_on.append(group_name)
            self.stages[stage.name] = stage
        return self
