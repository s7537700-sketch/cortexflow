"""
Token Tracker — Per-agent and aggregate token accounting system.

Provides real-time monitoring of token consumption across all agents
with historical logging, budget alerts, and cost projection.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

logger = logging.getLogger("cortexflow.token_tracker")


@dataclass
class TokenRecord:
    agent: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    session_id: str
    timestamp: str
    cost_estimate: float = 0.0


class TokenTracker:
    """Tracks, analyzes and alerts on token consumption."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.log_dir = Path(self.config.get("log_dir", "./data/tokens"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[TokenRecord] = []
        self.session_totals: Dict[str, Dict] = defaultdict(
            lambda: {"prompt": 0, "completion": 0, "cost": 0.0}
        )
        self.alert_threshold = self.config.get("alert_threshold", 1_000_000)
        self.monthly_budget = self.config.get("monthly_budget", 50_000_000)

        self.RATES = {
            "claude-opus-4.5": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
            "claude-haiku-4.5": {"input": 0.25, "output": 1.25},
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "default": {"input": 3.0, "output": 15.0},
        }

    def log(self, agent: str, prompt: int, completion: int,
            model: str = "default", session_id: str = "default") -> TokenRecord:
        """Record token usage for an agent call."""
        rates = self.RATES.get(model, self.RATES["default"])
        cost = (prompt / 1_000_000 * rates["input"] +
                completion / 1_000_000 * rates["output"])

        record = TokenRecord(
            agent=agent,
            prompt_tokens=prompt,
            completion_tokens=completion,
            model=model,
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat(),
            cost_estimate=round(cost, 6),
        )
        self.records.append(record)

        self.session_totals[session_id]["prompt"] += prompt
        self.session_totals[session_id]["completion"] += completion
        self.session_totals[session_id]["cost"] += cost

        total = self.get_total_tokens()
        if total > self.alert_threshold:
            logger.warning(
                f"Token threshold exceeded: {total:,} > {self.alert_threshold:,}")

        return record

    def get_agent_summary(self, agent: str) -> Dict:
        """Get token usage summary for a specific agent."""
        agent_records = [r for r in self.records if r.agent == agent]
        if not agent_records:
            return {"total": 0, "calls": 0, "avg_per_call": 0}

        total = sum(r.prompt_tokens + r.completion_tokens for r in agent_records)
        return {
            "total": total,
            "calls": len(agent_records),
            "avg_per_call": total // max(len(agent_records), 1),
            "total_cost": sum(r.cost_estimate for r in agent_records),
        }

    def get_session_summary(self, session_id: str) -> Dict:
        """Get token summary for a specific session."""
        data = self.session_totals.get(session_id, {})
        return {
            "session_id": session_id,
            "total": data.get("prompt", 0) + data.get("completion", 0),
            "prompt": data.get("prompt", 0),
            "completion": data.get("completion", 0),
            "cost_estimate": round(data.get("cost", 0.0), 4),
        }

    def get_total_tokens(self) -> int:
        """Get total tokens consumed across all agents and sessions."""
        return sum(
            r.prompt_tokens + r.completion_tokens for r in self.records
        )

    def get_monthly_usage(self) -> Dict:
        """Get token usage for the current month."""
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly = [
            r for r in self.records
            if datetime.fromisoformat(r.timestamp) >= month_start
        ]
        total = sum(r.prompt_tokens + r.completion_tokens for r in monthly)
        budget_remaining = self.monthly_budget - total
        return {
            "total": total,
            "budget": self.monthly_budget,
            "remaining": budget_remaining,
            "percent_used": round(total / self.monthly_budget * 100, 1),
            "estimated_cost": round(sum(r.cost_estimate for r in monthly), 2),
        }

    def summary(self) -> Dict:
        """Full platform token summary."""
        return {
            "total_all_time": self.get_total_tokens(),
            "monthly": self.get_monthly_usage(),
            "by_agent": {
                a: self.get_agent_summary(a)
                for a in set(r.agent for r in self.records)
            },
            "total_sessions": len(self.session_totals),
            "total_api_calls": len(self.records),
        }

    def export(self, path: Optional[str] = None) -> str:
        """Export token records to JSON file."""
        path = path or str(self.log_dir / "token_export.json")
        data = {
            "exported_at": datetime.utcnow().isoformat(),
            "records": [asdict(r) for r in self.records],
            "summary": self.summary(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path
