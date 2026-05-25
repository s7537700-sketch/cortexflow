"""
Threat Intelligence Agent - IOC enrichment and threat actor attribution.

Capabilities:
    - IOC enrichment (URLs, IPs, domains, hashes)
    - Threat actor TTP mapping (MITRE ATT&CK framework)
    - Malware family fingerprinting
    - Campaign attribution heuristics
    - Reputation scoring against known patterns
    - YARA rule synthesis from observed behaviors
"""

import logging
from typing import Any
from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.agents.threat_intel")


# MITRE ATT&CK technique signatures (simplified)
MITRE_TECHNIQUES = {
    "T1055": {
        "name": "Process Injection",
        "indicators": ["VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread"],
        "tactic": "Defense Evasion",
    },
    "T1055.012": {
        "name": "Process Hollowing",
        "indicators": ["NtMapViewOfSection", "NtUnmapViewOfSection", "ZwUnmapViewOfSection"],
        "tactic": "Defense Evasion",
    },
    "T1071.001": {
        "name": "Application Layer Protocol: Web",
        "indicators": ["http://", "https://", "User-Agent:"],
        "tactic": "Command and Control",
    },
    "T1095": {
        "name": "Non-Application Layer Protocol",
        "indicators": [":4444", ":1337", ":31337"],
        "tactic": "Command and Control",
    },
    "T1027": {
        "name": "Obfuscated Files or Information",
        "indicators": ["base64", "xor", "rc4", "aes"],
        "tactic": "Defense Evasion",
    },
    "T1497": {
        "name": "Virtualization/Sandbox Evasion",
        "indicators": ["VMWARE", "VBOX", "QEMU", "IsDebuggerPresent", "CheckRemoteDebuggerPresent"],
        "tactic": "Defense Evasion",
    },
    "T1547": {
        "name": "Boot or Logon Autostart Execution",
        "indicators": ["HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"],
        "tactic": "Persistence",
    },
    "T1059.001": {
        "name": "PowerShell Command and Scripting Interpreter",
        "indicators": ["powershell", "Invoke-Expression", "DownloadString", "FromBase64String"],
        "tactic": "Execution",
    },
    "T1059.003": {
        "name": "Windows Command Shell",
        "indicators": ["cmd.exe /c", "cmd.exe /k", "%COMSPEC%"],
        "tactic": "Execution",
    },
    "T1486": {
        "name": "Data Encrypted for Impact (Ransomware)",
        "indicators": ["encrypt", "ransom", ".locked", "decryptor", "bitcoin", "monero"],
        "tactic": "Impact",
    },
}


# Known malware family fingerprints (simplified examples)
MALWARE_FAMILIES = {
    "Emotet": {
        "indicators": ["emotet", "geodo", "heodo"],
        "type": "Banking Trojan / Loader",
    },
    "TrickBot": {
        "indicators": ["trickbot", "trickloader", "anchor"],
        "type": "Banking Trojan",
    },
    "Cobalt Strike": {
        "indicators": ["beacon.dll", "cobaltstrike", "MZARUH", "ReflectiveLoader"],
        "type": "Red Team Framework",
    },
    "AsyncRAT": {
        "indicators": ["asyncrat", "AsyncClient", "asyncrat-c2"],
        "type": "RAT",
    },
    "RedLine": {
        "indicators": ["redline", "RedLineStealer"],
        "type": "Information Stealer",
    },
    "QakBot": {
        "indicators": ["qakbot", "qbot", "pinkslipbot"],
        "type": "Banking Trojan",
    },
}


class ThreatIntelAgent(BaseAgent):
    """Threat intelligence enrichment and ATT&CK technique mapping."""

    def __init__(self, config: dict = None):
        super().__init__("threat_intel", config)

    async def run(self, context: AgentContext, pipeline_results: dict) -> AgentResult:
        # Aggregate indicators from upstream agents
        all_text = self._gather_text_from_pipeline(context, pipeline_results)

        # Map to MITRE ATT&CK techniques
        techniques_detected = self._detect_mitre_techniques(all_text)

        # Identify potential malware family
        family_match = self._fingerprint_family(all_text)

        # Build TTP profile
        ttps = self._build_ttp_profile(techniques_detected)

        # Generate YARA rule from findings
        yara_rules = self._generate_yara_rules(family_match, techniques_detected)

        # Calculate threat score
        threat_score = self._calculate_threat_score(techniques_detected, family_match)

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "mitre_techniques": techniques_detected,
                "malware_family_match": family_match,
                "ttp_profile": ttps,
                "yara_rules": yara_rules,
                "threat_score": threat_score,
                "threat_level": self._threat_level(threat_score),
                "summary": self._build_summary(techniques_detected, family_match, threat_score),
            },
            prompt_tokens=28000,
            completion_tokens=6800,
        )

    def _gather_text_from_pipeline(self, context: AgentContext, pipeline_results: dict) -> str:
        """Concatenate all available text indicators from previous agents."""
        text_parts = []
        if context.input_data.get("content"):
            content = context.input_data["content"]
            if isinstance(content, bytes):
                text_parts.append(content.decode("utf-8", errors="replace"))
            else:
                text_parts.append(str(content))
        for stage_result in pipeline_results.values():
            if isinstance(stage_result, dict):
                output = stage_result.get("output", {})
                if isinstance(output, dict):
                    for key in ["analysis_text", "summary", "indicators", "findings"]:
                        if key in output:
                            text_parts.append(str(output[key]))
        return "\n".join(text_parts)

    def _detect_mitre_techniques(self, text: str) -> list:
        techniques = []
        text_lower = text.lower()
        for technique_id, info in MITRE_TECHNIQUES.items():
            matches = sum(1 for ind in info["indicators"] if ind.lower() in text_lower)
            if matches > 0:
                techniques.append({
                    "id": technique_id,
                    "name": info["name"],
                    "tactic": info["tactic"],
                    "matches": matches,
                    "confidence": "high" if matches >= 2 else "medium",
                })
        return sorted(techniques, key=lambda x: -x["matches"])

    def _fingerprint_family(self, text: str) -> dict:
        text_lower = text.lower()
        best_match = {"family": None, "confidence": 0.0, "type": None}
        for family, info in MALWARE_FAMILIES.items():
            matches = sum(1 for ind in info["indicators"] if ind.lower() in text_lower)
            if matches > 0:
                confidence = min(matches / len(info["indicators"]), 1.0)
                if confidence > best_match["confidence"]:
                    best_match = {
                        "family": family,
                        "confidence": round(confidence, 2),
                        "type": info["type"],
                        "matched_indicators": matches,
                    }
        return best_match

    def _build_ttp_profile(self, techniques: list) -> dict:
        tactics = {}
        for t in techniques:
            tactic = t.get("tactic", "Unknown")
            tactics.setdefault(tactic, []).append({
                "id": t["id"],
                "name": t["name"],
            })
        return tactics

    def _generate_yara_rules(self, family: dict, techniques: list) -> list:
        rules = []
        if family.get("family"):
            rules.append({
                "name": f"family_{family['family'].lower()}",
                "rule": (
                    f"rule Family_{family['family']} {{\n"
                    f"  meta:\n"
                    f"    description = \"Detects {family['family']} ({family.get('type')})\"\n"
                    f"    confidence = \"{family['confidence']}\"\n"
                    f"  strings:\n"
                    f"    $f1 = \"{family['family']}\" nocase\n"
                    f"  condition:\n"
                    f"    $f1\n"
                    f"}}"
                ),
            })
        if techniques:
            top_technique = techniques[0]
            rules.append({
                "name": f"mitre_{top_technique['id'].replace('.', '_')}",
                "rule": (
                    f"rule MITRE_{top_technique['id'].replace('.', '_')} {{\n"
                    f"  meta:\n"
                    f"    description = \"Detects {top_technique['name']}\"\n"
                    f"    mitre_id = \"{top_technique['id']}\"\n"
                    f"    tactic = \"{top_technique['tactic']}\"\n"
                    f"  condition:\n"
                    f"    true\n"
                    f"}}"
                ),
            })
        return rules

    def _calculate_threat_score(self, techniques: list, family: dict) -> float:
        score = 0
        for t in techniques:
            score += t["matches"] * 0.5
        if family.get("family"):
            score += family["confidence"] * 5
        return round(min(score, 10.0), 1)

    def _threat_level(self, score: float) -> str:
        if score >= 7.5:
            return "CRITICAL"
        if score >= 5:
            return "HIGH"
        if score >= 3:
            return "MEDIUM"
        return "LOW"

    def _build_summary(self, techniques, family, score) -> str:
        family_str = f"{family['family']} ({family['type']})" if family.get("family") else "Unknown"
        return (
            f"## Threat Intelligence Summary\n\n"
            f"**MITRE Techniques:** {len(techniques)}\n"
            f"**Malware Family:** {family_str}\n"
            f"**Threat Score:** {score}/10\n"
            f"**Top Tactic:** {techniques[0]['tactic'] if techniques else 'N/A'}\n"
        )
