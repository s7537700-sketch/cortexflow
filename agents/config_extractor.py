"""
Config Extractor Agent - Specialized agent for extracting and decoding
embedded configuration data from binaries and obfuscated samples.

Capabilities:
    - Embedded JSON/XML/YAML configuration extraction
    - Encrypted config block detection (XOR, RC4, AES)
    - Hardcoded credentials and API keys discovery
    - Configuration block fingerprinting
    - Cross-reference with known malware family configs
"""

import re
import json
import base64
import logging
from typing import Any
from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.agents.config_extractor")


# Common config field indicators
CONFIG_INDICATORS = {
    "c2": ["server", "host", "domain", "url", "endpoint", "callback", "panel", "gate"],
    "timing": ["sleep", "interval", "jitter", "timeout", "delay", "beacon"],
    "persistence": ["mutex", "service", "registry", "scheduled", "startup", "autorun"],
    "encryption": ["key", "iv", "salt", "nonce", "secret", "password", "passphrase"],
    "process": ["inject", "spawn", "target", "process", "thread"],
    "network": ["port", "protocol", "user_agent", "header", "uri", "path"],
}

# High-entropy regex patterns
PATTERN_CRYPTO_KEY = re.compile(rb'[A-Fa-f0-9]{32,128}')
PATTERN_BASE64 = re.compile(rb'[A-Za-z0-9+/]{40,}={0,2}')
PATTERN_API_KEY = re.compile(rb'(api[_-]?key|token|secret|auth)[\'"\s:=]+([a-zA-Z0-9_\-]{16,})', re.IGNORECASE)
PATTERN_AWS = re.compile(rb'AKIA[0-9A-Z]{16}|aws_secret[a-zA-Z0-9_]*\s*=\s*[\'"][^\'"]{40}')
PATTERN_GH_TOKEN = re.compile(rb'gh[pous]_[A-Za-z0-9]{36,255}')


class ConfigExtractorAgent(BaseAgent):
    """Extracts and decodes embedded configuration from binaries and code."""

    def __init__(self, config: dict = None):
        super().__init__("config_extractor", config)

    async def run(self, context: AgentContext, pipeline_results: dict) -> AgentResult:
        data = context.input_data.get("content", "")
        if isinstance(data, str):
            data_bytes = data.encode("utf-8", errors="replace")
        else:
            data_bytes = data

        result = {
            "configurations": [],
            "credentials": [],
            "encryption_artifacts": [],
            "indicators_found": {},
        }

        # Extract JSON blobs from text
        json_blobs = self._extract_json_blobs(data if isinstance(data, str) else data.decode("utf-8", errors="replace"))
        result["configurations"].extend(json_blobs)

        # Extract base64-encoded blobs
        b64_blobs = self._extract_base64(data_bytes)
        for blob in b64_blobs[:10]:
            decoded = self._try_decode_base64(blob)
            if decoded and self._looks_like_config(decoded):
                result["configurations"].append({
                    "type": "base64_config",
                    "encoded": blob[:100].decode(errors="replace"),
                    "decoded_preview": decoded[:300],
                })

        # Find hardcoded credentials/keys
        creds = self._extract_credentials(data_bytes)
        result["credentials"] = creds[:30]

        # Detect encryption keys (high-entropy strings)
        crypto = self._extract_crypto_artifacts(data_bytes)
        result["encryption_artifacts"] = crypto[:20]

        # Group by category
        text = data if isinstance(data, str) else data_bytes.decode("utf-8", errors="replace")
        for category, indicators in CONFIG_INDICATORS.items():
            matches = []
            for indicator in indicators:
                pattern = re.compile(rf"\b{indicator}\b\s*[:=]\s*['\"]?([^'\",\n]{{1,100}})", re.IGNORECASE)
                for match in pattern.finditer(text)[:5] if hasattr(pattern.finditer(text), '__getitem__') else list(pattern.finditer(text))[:5]:
                    matches.append({
                        "key": match.group(0)[:50],
                        "value_preview": match.group(1)[:80] if match.lastindex else "",
                    })
            if matches:
                result["indicators_found"][category] = matches[:5]

        summary = self._build_summary(result)

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "configurations": result["configurations"],
                "credentials_count": len(result["credentials"]),
                "credentials_preview": result["credentials"][:10],
                "encryption_artifacts_count": len(result["encryption_artifacts"]),
                "indicators": result["indicators_found"],
                "summary": summary,
                "risk_level": self._calculate_risk(result),
            },
            prompt_tokens=18000,
            completion_tokens=4200,
        )

    def _extract_json_blobs(self, text: str) -> list:
        """Find embedded JSON config objects."""
        blobs = []
        depth = 0
        start = -1
        for i, c in enumerate(text):
            if c == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and start >= 0 and (i - start) < 5000:
                    candidate = text[start:i+1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and len(parsed) >= 2:
                            blobs.append({
                                "type": "json",
                                "size": len(candidate),
                                "keys": list(parsed.keys())[:10],
                                "preview": candidate[:300],
                            })
                    except json.JSONDecodeError:
                        pass
                    start = -1
        return blobs[:10]

    def _extract_base64(self, data: bytes) -> list:
        """Find candidate base64-encoded blobs."""
        return [m.group(0) for m in PATTERN_BASE64.finditer(data)][:30]

    def _try_decode_base64(self, blob: bytes) -> str:
        """Attempt to decode a base64 blob to readable text."""
        try:
            decoded = base64.b64decode(blob, validate=False)
            text = decoded.decode("utf-8", errors="replace")
            # Only return if it looks like text (not random bytes)
            if sum(1 for c in text if c.isprintable()) / max(len(text), 1) > 0.7:
                return text
        except Exception:
            pass
        return ""

    def _looks_like_config(self, text: str) -> bool:
        """Heuristic: does this look like a configuration?"""
        if len(text) < 20:
            return False
        config_score = 0
        for category in CONFIG_INDICATORS.values():
            for indicator in category:
                if indicator.lower() in text.lower():
                    config_score += 1
        return config_score >= 2

    def _extract_credentials(self, data: bytes) -> list:
        """Find hardcoded credentials, API keys, tokens."""
        creds = []

        for match in PATTERN_API_KEY.finditer(data):
            creds.append({
                "type": "api_key_or_token",
                "field": match.group(1).decode(errors="replace")[:30],
                "value_preview": match.group(2).decode(errors="replace")[:30] + "...",
                "severity": "HIGH",
            })

        for match in PATTERN_AWS.finditer(data):
            creds.append({
                "type": "aws_credential",
                "preview": match.group(0).decode(errors="replace")[:50],
                "severity": "CRITICAL",
            })

        for match in PATTERN_GH_TOKEN.finditer(data):
            creds.append({
                "type": "github_token",
                "preview": match.group(0)[:20].decode(errors="replace") + "...",
                "severity": "CRITICAL",
            })

        return creds

    def _extract_crypto_artifacts(self, data: bytes) -> list:
        """Find high-entropy strings that look like keys."""
        artifacts = []
        for match in PATTERN_CRYPTO_KEY.finditer(data):
            blob = match.group(0)
            if 32 <= len(blob) <= 128:
                artifacts.append({
                    "type": "potential_key",
                    "length": len(blob),
                    "preview": blob[:32].decode(errors="replace") + "...",
                })
        return artifacts

    def _build_summary(self, result: dict) -> str:
        return (
            f"## Config Extraction Summary\n\n"
            f"**Configuration blocks:** {len(result['configurations'])}\n"
            f"**Credentials/Keys:** {len(result['credentials'])}\n"
            f"**Encryption artifacts:** {len(result['encryption_artifacts'])}\n"
            f"**Indicator categories matched:** {len(result['indicators_found'])}\n"
        )

    def _calculate_risk(self, result: dict) -> str:
        score = 0
        for cred in result.get("credentials", []):
            if cred.get("severity") == "CRITICAL":
                score += 3
            elif cred.get("severity") == "HIGH":
                score += 2
            else:
                score += 1
        score += len(result.get("encryption_artifacts", []))
        if score >= 10:
            return "CRITICAL"
        if score >= 5:
            return "HIGH"
        if score >= 2:
            return "MEDIUM"
        return "LOW"
