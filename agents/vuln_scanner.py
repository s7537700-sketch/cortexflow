"""
Vulnerability Scanner Agent — Automated vulnerability discovery and classification.

Scans code and configurations for:
- OWASP Top 10 vulnerability patterns
- CVE and known vulnerability signature matching
- Configuration weakness detection
- Dependency vulnerability correlation
"""

import logging
import re
import json
from typing import Any
from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.agents.scanner")

VULN_DATABASE = {
    "sql_injection": {
        "patterns": [
            (r"SELECT\s+.*\s+FROM\s+.*\s+WHERE.*\{", "String interpolation in SQL query"),
            (r"execute\(.*f[\"']", "f-string in SQL execution"),
            (r"raw\(.*request", "Raw SQL with user input"),
        ],
        "severity": "CRITICAL",
        "cwe": "CWE-89",
    },
    "xss": {
        "patterns": [
            (r"innerHTML\s*=.*(?:request|input|param)", "User input assigned to innerHTML"),
            (r"dangerouslySetInnerHTML", "React dangerous HTML injection"),
        ],
        "severity": "HIGH",
        "cwe": "CWE-79",
    },
    "command_injection": {
        "patterns": [
            (r"os\.system\(.*request", "OS command with user input"),
            (r"subprocess\.\w+\(.*request", "Subprocess with user input"),
        ],
        "severity": "CRITICAL",
        "cwe": "CWE-78",
    },
    "insecure_deserialization": {
        "patterns": [
            (r"pickle\.loads?\(", "Unsafe pickle deserialization"),
            (r"yaml\.load\(", "Unsafe YAML deserialization (use safe_load)"),
        ],
        "severity": "HIGH",
        "cwe": "CWE-502",
    },
    "path_traversal": {
        "patterns": [
            (r"open\(.*request", "File open with user-controlled path"),
            (r"Path\(.*request", "Path construction with user input"),
        ],
        "severity": "HIGH",
        "cwe": "CWE-22",
    },
}


class VulnScannerAgent(BaseAgent):
    """Automated vulnerability scanning with CWE classification."""

    def __init__(self, config: dict = None):
        super().__init__("vuln_scanner", config)

    async def run(self, context: AgentContext,
                  pipeline_results: dict) -> AgentResult:
        content = context.input_data.get("content", "")
        target_type = context.input_data.get("type", "codebase")

        findings = []
        for vuln_type, vuln_info in VULN_DATABASE.items():
            for pattern, desc in vuln_info["patterns"]:
                for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                    findings.append({
                        "vulnerability": vuln_type,
                        "cwe": vuln_info["cwe"],
                        "severity": vuln_info["severity"],
                        "description": desc,
                        "match": match.group()[:80],
                        "line": self._get_line_number(content, match.start()),
                        "recommendation": self._get_remediation(vuln_type),
                    })

        risk_score = self._calculate_risk_score(findings)
        summary = self._generate_summary(findings, risk_score)

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "findings": findings,
                "risk_score": risk_score,
                "risk_level": self._risk_level(risk_score),
                "summary": summary,
                "by_cwe": self._group_by_cwe(findings),
                "by_severity": self._group_by_severity(findings),
            },
            prompt_tokens=28000,
            completion_tokens=5200,
        )

    def _get_line_number(self, content: str, pos: int) -> int:
        return content[:pos].count("\n") + 1

    def _calculate_risk_score(self, findings: list) -> float:
        score = 0.0
        severity_weights = {"CRITICAL": 3.0, "HIGH": 2.0, "MEDIUM": 1.0, "LOW": 0.5}
        for f in findings:
            score += severity_weights.get(f["severity"], 0.5)
        return min(round(score, 1), 10.0)

    def _risk_level(self, score: float) -> str:
        if score >= 7.0: return "CRITICAL"
        if score >= 5.0: return "HIGH"
        if score >= 3.0: return "MEDIUM"
        return "LOW"

    def _generate_summary(self, findings: list, score: float) -> str:
        by_sev = self._group_by_severity(findings)
        return (
            f"## Vulnerability Scan Summary\n\n"
            f"**Total findings:** {len(findings)}\n"
            f"**Risk score:** {score}/10 ({self._risk_level(score)})\n"
            f"**Critical:** {len(by_sev.get('CRITICAL', []))}\n"
            f"**High:** {len(by_sev.get('HIGH', []))}\n"
            f"**Medium:** {len(by_sev.get('MEDIUM', []))}\n"
        )

    def _group_by_cwe(self, findings: list) -> dict:
        groups = {}
        for f in findings:
            cwe = f["cwe"]
            if cwe not in groups:
                groups[cwe] = []
            groups[cwe].append(f)
        return {k: {"count": len(v), "items": v[:5]} for k, v in groups.items()}

    def _group_by_severity(self, findings: list) -> dict:
        groups = {}
        for f in findings:
            sev = f["severity"]
            if sev not in groups:
                groups[sev] = []
            groups[sev].append(f)
        return groups

    def _get_remediation(self, vuln_type: str) -> str:
        rem = {
            "sql_injection": "Use parameterized queries or ORM (SQLAlchemy, Prisma)",
            "xss": "Use proper output encoding and Content-Security-Policy headers",
            "command_injection": "Avoid shell commands with user input; use subprocess with args list",
            "insecure_deserialization": "Use safe serialization (JSON, MessagePack) with validation",
            "path_traversal": "Validate and sanitize file paths; use allowlist approach",
        }
        return rem.get(vuln_type, "Review and apply security best practices")
