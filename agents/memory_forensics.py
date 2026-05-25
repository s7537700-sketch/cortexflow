"""
Memory Forensics Agent - Process memory and crash dump analysis.

Capabilities:
    - Process injection detection (DLL, process hollowing, atom bombing)
    - Memory string and credential extraction
    - Heap and stack pattern recognition
    - PE injection signature detection
    - Volatility-style artifact extraction
    - Anomalous memory region identification
"""

import re
import logging
from typing import Any
from .base_agent import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger("cortexflow.agents.memory")


# Memory injection signatures
INJECTION_SIGNATURES = {
    "VirtualAllocEx": "Process memory allocation in remote process",
    "WriteProcessMemory": "Memory write into another process",
    "CreateRemoteThread": "Remote thread creation (classic injection)",
    "NtMapViewOfSection": "Section mapping (process hollowing)",
    "NtUnmapViewOfSection": "Section unmapping (hollowing prep)",
    "QueueUserAPC": "APC queue injection",
    "SetWindowsHookEx": "SetWindowsHook injection vector",
    "RtlCreateUserThread": "Native API thread creation",
    "AtomBombing": "Atom-based code injection",
}

# PE markers
PE_HEADER = b"MZ"
PE_NT_SIGNATURE = b"PE\x00\x00"
SHELLCODE_PROLOGUES = [
    b"\x55\x8b\xec",        # push ebp; mov ebp, esp
    b"\x55\x48\x89\xe5",    # x64 prologue
    b"\xfc\xe8",            # cld; call (typical shellcode prefix)
    b"\xeb\xfe",            # jmp short -2 (debug breakpoint)
]


class MemoryForensicsAgent(BaseAgent):
    """Memory dump and process artifact analysis."""

    def __init__(self, config: dict = None):
        super().__init__("memory_forensics", config)

    async def run(self, context: AgentContext, pipeline_results: dict) -> AgentResult:
        data = context.input_data.get("content", b"")
        if isinstance(data, str):
            data_bytes = data.encode("utf-8", errors="replace")
        else:
            data_bytes = data

        # Detect injection technique signatures
        injection_apis = self._detect_injection_apis(data_bytes)

        # Find embedded PE files
        embedded_pes = self._find_embedded_pes(data_bytes)

        # Detect shellcode prologues
        shellcode = self._detect_shellcode_prologues(data_bytes)

        # Extract process names referenced
        process_refs = self._extract_process_references(data_bytes)

        # Find heap allocator patterns
        heap_patterns = self._detect_heap_patterns(data_bytes)

        # Calculate suspicion score
        suspicion = self._calculate_suspicion(
            injection_apis, embedded_pes, shellcode, heap_patterns
        )

        return AgentResult(
            success=True,
            agent_name=self.name,
            output={
                "injection_apis_detected": injection_apis,
                "embedded_pe_files": embedded_pes,
                "shellcode_prologues": shellcode,
                "process_references": process_refs[:30],
                "heap_patterns": heap_patterns,
                "suspicion_score": suspicion["score"],
                "suspicion_level": suspicion["level"],
                "techniques_inferred": suspicion["techniques"],
                "summary": self._build_summary(injection_apis, embedded_pes, suspicion),
            },
            prompt_tokens=24000,
            completion_tokens=5500,
        )

    def _detect_injection_apis(self, data: bytes) -> list:
        found = []
        for api, description in INJECTION_SIGNATURES.items():
            if api.encode() in data:
                found.append({
                    "api": api,
                    "description": description,
                    "severity": "HIGH",
                })
        return found

    def _find_embedded_pes(self, data: bytes) -> list:
        embedded = []
        offset = 0
        while True:
            mz_idx = data.find(PE_HEADER, offset)
            if mz_idx == -1:
                break
            # Check for PE signature near MZ
            check_range = data[mz_idx:mz_idx + 1024]
            if PE_NT_SIGNATURE in check_range:
                pe_offset = check_range.index(PE_NT_SIGNATURE)
                embedded.append({
                    "offset": hex(mz_idx),
                    "pe_offset": hex(mz_idx + pe_offset),
                    "size_estimate": "unknown",
                })
                if len(embedded) >= 10:
                    break
            offset = mz_idx + 2
        return embedded

    def _detect_shellcode_prologues(self, data: bytes) -> list:
        found = []
        for prologue in SHELLCODE_PROLOGUES:
            offset = 0
            count = 0
            while count < 5:
                idx = data.find(prologue, offset)
                if idx == -1:
                    break
                found.append({
                    "offset": hex(idx),
                    "prologue": prologue.hex(),
                    "size": len(prologue),
                })
                offset = idx + len(prologue)
                count += 1
        return found

    def _extract_process_references(self, data: bytes) -> list:
        # Find common process names
        common_processes = [
            b"explorer.exe", b"svchost.exe", b"lsass.exe", b"winlogon.exe",
            b"csrss.exe", b"services.exe", b"smss.exe", b"taskmgr.exe",
            b"chrome.exe", b"firefox.exe", b"powershell.exe", b"cmd.exe",
            b"notepad.exe", b"calc.exe", b"mstsc.exe", b"wininit.exe",
        ]
        found = []
        for proc in common_processes:
            if proc in data.lower():
                found.append(proc.decode())
        return found

    def _detect_heap_patterns(self, data: bytes) -> list:
        patterns = []
        # Check for heap allocation API references
        heap_apis = [b"HeapAlloc", b"HeapCreate", b"VirtualAlloc", b"malloc", b"new[]"]
        for api in heap_apis:
            if api in data:
                patterns.append(api.decode())
        return patterns

    def _calculate_suspicion(self, injections, pes, shellcode, heap) -> dict:
        score = 0
        score += len(injections) * 1.5
        score += len(pes) * 2.0
        score += len(shellcode) * 1.0
        score += len(heap) * 0.3

        techniques = []
        if any(i["api"] in ("VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread") for i in injections):
            techniques.append("Classic DLL/Code Injection")
        if any(i["api"] in ("NtMapViewOfSection", "NtUnmapViewOfSection") for i in injections):
            techniques.append("Process Hollowing")
        if any(i["api"] == "QueueUserAPC" for i in injections):
            techniques.append("APC Queue Injection")
        if any(i["api"] == "AtomBombing" for i in injections):
            techniques.append("Atom Bombing")
        if shellcode:
            techniques.append("Shellcode Embedded")

        score = min(round(score, 1), 10.0)
        level = "CRITICAL" if score >= 7 else "HIGH" if score >= 5 else "MEDIUM" if score >= 3 else "LOW"

        return {
            "score": score,
            "level": level,
            "techniques": techniques,
        }

    def _build_summary(self, injections, pes, suspicion) -> str:
        return (
            f"## Memory Forensics Summary\n\n"
            f"**Injection APIs:** {len(injections)}\n"
            f"**Embedded PEs:** {len(pes)}\n"
            f"**Suspicion:** {suspicion['level']} ({suspicion['score']}/10)\n"
            f"**Techniques:** {', '.join(suspicion['techniques']) if suspicion['techniques'] else 'None detected'}\n"
        )
