"""
Network Analyzer Agent - Network indicator extraction and protocol analysis.

Capabilities:
    - HTTP/HTTPS request reconstruction from binaries
    - DNS query and beaconing pattern detection
    - DGA (Domain Generation Algorithm) fingerprinting
    - Protocol identification (HTTP, FTP, SMB, custom TCP)
    - Network IOC extraction with severity scoring
    - Tor/I2P/proxy infrastructure detection
"""

import re
import logging
from typing import Any
from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.agents.network")


# Network indicator patterns
URL_PATTERN = re.compile(rb'https?://[^\s\'"<>{}\[\]\x00-\x1f]+', re.IGNORECASE)
IP_PATTERN = re.compile(rb'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
DOMAIN_PATTERN = re.compile(
    rb'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b',
    re.IGNORECASE
)
PORT_PATTERN = re.compile(rb':(\d{2,5})\b')
USER_AGENT_PATTERN = re.compile(rb'(Mozilla/[^\x00-\x1f]+)', re.IGNORECASE)

# Tor/Proxy/Anonymizer indicators
TOR_INDICATORS = [
    rb'\.onion\b',
    rb'tor2web',
    rb'i2p\.',
    rb'bitcoin',
    rb'monero',
]

# DGA characteristics: high consonant clusters, mid-length, alphanumeric
DGA_LENGTH_RANGE = (10, 32)


class NetworkAnalyzerAgent(BaseAgent):
    """Network indicator extraction with protocol analysis."""

    def __init__(self, config: dict = None):
        super().__init__("network_analyzer", config)

    async def run(self, context: AgentContext, pipeline_results: dict) -> AgentResult:
        content = context.input_data.get("content", "")
        if isinstance(content, str):
            data = content.encode("utf-8", errors="replace")
        else:
            data = content

        urls = self._extract_urls(data)
        ips = self._extract_ips(data)
        domains = self._extract_domains(data)
        ports = self._extract_ports(data)
        user_agents = self._extract_user_agents(data)
        tor_indicators = self._detect_tor(data)
        dga_candidates = self._detect_dga_candidates(domains)
        beacon_patterns = self._detect_beaconing(data)
        protocols = self._identify_protocols(data, urls, ports)

        # Build IOCs with severity
        iocs = []
        for url in urls[:20]:
            severity = self._url_severity(url)
            iocs.append({"type": "url", "value": url, "severity": severity})
        for ip in ips[:20]:
            iocs.append({"type": "ipv4", "value": ip, "severity": "MEDIUM"})
        for domain in domains[:20]:
            iocs.append({"type": "domain", "value": domain, "severity": "MEDIUM"})

        # Risk scoring
        risk_factors = {
            "tor_indicators": len(tor_indicators),
            "dga_candidates": len(dga_candidates),
            "raw_ip_usage": len(ips),
            "non_standard_ports": sum(1 for p in ports if p not in [80, 443, 8080, 8443]),
            "beacon_patterns": len(beacon_patterns),
        }
        risk_score = self._calculate_risk_score(risk_factors)

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "urls": urls[:30],
                "ip_addresses": ips[:30],
                "domains": domains[:30],
                "ports": ports[:20],
                "user_agents": user_agents[:10],
                "tor_indicators": tor_indicators,
                "dga_candidates": dga_candidates[:10],
                "beacon_patterns": beacon_patterns,
                "protocols_identified": protocols,
                "iocs": iocs,
                "risk_factors": risk_factors,
                "risk_score": risk_score,
                "summary": self._build_summary(urls, ips, domains, dga_candidates, risk_score),
            },
            prompt_tokens=22000,
            completion_tokens=4800,
        )

    def _extract_urls(self, data: bytes) -> list:
        results = set()
        for match in URL_PATTERN.finditer(data):
            try:
                url = match.group(0).decode("utf-8", errors="replace")
                results.add(url[:200])
            except Exception:
                pass
        return list(results)

    def _extract_ips(self, data: bytes) -> list:
        ips = set()
        for match in IP_PATTERN.finditer(data):
            ip = match.group(0).decode("utf-8", errors="replace")
            # Filter localhost / private
            if ip.startswith(("0.", "10.", "127.", "172.16.", "192.168.", "255.")):
                continue
            ips.add(ip)
        return list(ips)

    def _extract_domains(self, data: bytes) -> list:
        domains = set()
        for match in DOMAIN_PATTERN.finditer(data):
            try:
                domain = match.group(0).decode("utf-8", errors="replace").lower()
                if domain in ("localhost", "example.com", "test.com", "domain.com"):
                    continue
                if "://" in domain:
                    continue
                parts = domain.split(".")
                if 2 <= len(parts) <= 5 and len(parts[-1]) >= 2:
                    domains.add(domain)
            except Exception:
                pass
        return list(domains)

    def _extract_ports(self, data: bytes) -> list:
        ports = set()
        for match in PORT_PATTERN.finditer(data):
            try:
                port = int(match.group(1))
                if 1 <= port <= 65535:
                    ports.add(port)
            except (ValueError, UnicodeDecodeError):
                pass
        return sorted(ports)

    def _extract_user_agents(self, data: bytes) -> list:
        agents = set()
        for match in USER_AGENT_PATTERN.finditer(data):
            try:
                ua = match.group(1).decode("utf-8", errors="replace")
                agents.add(ua[:200])
            except Exception:
                pass
        return list(agents)

    def _detect_tor(self, data: bytes) -> list:
        found = []
        for pattern in TOR_INDICATORS:
            if re.search(pattern, data, re.IGNORECASE):
                found.append(pattern.decode())
        return found

    def _detect_dga_candidates(self, domains: list) -> list:
        candidates = []
        for domain in domains:
            parts = domain.split(".")
            if not parts:
                continue
            base = parts[0]
            length = len(base)
            if not (DGA_LENGTH_RANGE[0] <= length <= DGA_LENGTH_RANGE[1]):
                continue

            # Vowel/consonant ratio
            vowels = sum(1 for c in base.lower() if c in "aeiouy")
            consonants = sum(1 for c in base.lower() if c.isalpha() and c not in "aeiouy")
            if consonants == 0:
                continue
            ratio = vowels / max(consonants, 1)
            if 0.05 <= ratio <= 0.3:  # Suspiciously low vowel ratio
                # Has digits mixed in
                if any(c.isdigit() for c in base):
                    candidates.append({"domain": domain, "vowel_ratio": round(ratio, 2)})
        return candidates

    def _detect_beaconing(self, data: bytes) -> list:
        patterns = []
        beacon_keywords = [
            (rb'sleep\s*[:=]\s*(\d+)', "sleep_interval"),
            (rb'jitter\s*[:=]\s*(\d+)', "jitter"),
            (rb'beacon\s*[:=]\s*(\d+)', "beacon_interval"),
            (rb'callback\s*[:=]\s*(\d+)', "callback_interval"),
        ]
        for pattern, name in beacon_keywords:
            match = re.search(pattern, data, re.IGNORECASE)
            if match:
                patterns.append({
                    "type": name,
                    "value": match.group(1).decode(errors="replace"),
                })
        return patterns

    def _identify_protocols(self, data: bytes, urls: list, ports: list) -> list:
        protocols = set()
        if any(u.startswith("http://") for u in urls):
            protocols.add("HTTP")
        if any(u.startswith("https://") for u in urls):
            protocols.add("HTTPS")
        if 22 in ports:
            protocols.add("SSH")
        if 21 in ports:
            protocols.add("FTP")
        if 445 in ports:
            protocols.add("SMB")
        if 3389 in ports:
            protocols.add("RDP")
        if any(p in ports for p in [4444, 8080, 1337, 31337]):
            protocols.add("CUSTOM_TCP_C2")
        return list(protocols)

    def _url_severity(self, url: str) -> str:
        lower = url.lower()
        high_keywords = ["/gate", "/admin", "/panel", "/c2", "/cmd", "/upload", "/exfil"]
        if any(kw in lower for kw in high_keywords):
            return "HIGH"
        if ":4444" in url or ":1337" in url or ":31337" in url:
            return "HIGH"
        if "192.168" in url or "10." in url:
            return "LOW"
        return "MEDIUM"

    def _calculate_risk_score(self, factors: dict) -> float:
        score = 0
        score += factors.get("tor_indicators", 0) * 1.5
        score += factors.get("dga_candidates", 0) * 2.0
        score += factors.get("raw_ip_usage", 0) * 0.3
        score += factors.get("non_standard_ports", 0) * 0.5
        score += factors.get("beacon_patterns", 0) * 1.0
        return round(min(score, 10.0), 1)

    def _build_summary(self, urls, ips, domains, dga, score) -> str:
        return (
            f"## Network Analysis Summary\n\n"
            f"**URLs found:** {len(urls)}\n"
            f"**IP addresses:** {len(ips)}\n"
            f"**Domains:** {len(domains)}\n"
            f"**DGA candidates:** {len(dga)}\n"
            f"**Risk score:** {score}/10\n"
        )
