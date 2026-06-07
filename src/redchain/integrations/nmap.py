"""Nmap integration — minimal wrapper around ``nmap -sV``.

This MVP wrapper executes ``nmap -sV -oX -`` against the target if nmap is
installed locally. If nmap is missing the integration returns an explanatory
stub result instead of raising — phases can decide whether to fail-fast.
"""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from typing import Any

from redchain.integrations.base import Integration


class NmapIntegration(Integration):
    name = "nmap"

    def run(self, *, target: str, timeout: int = 60, **kwargs: Any) -> dict[str, Any]:
        nmap_path = shutil.which("nmap")
        if not nmap_path:
            return {
                "available": False,
                "target": target,
                "services": [],
                "notes": "nmap binary not found on PATH; install nmap to enable this integration.",
            }
        cmd = [nmap_path, "-sV", "-oX", "-", target]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "available": True,
                "target": target,
                "services": [],
                "notes": f"nmap timed out after {timeout}s",
            }
        if proc.returncode != 0:
            return {
                "available": True,
                "target": target,
                "services": [],
                "notes": f"nmap exited {proc.returncode}: {proc.stderr.strip()[:500]}",
            }
        return {
            "available": True,
            "target": target,
            "services": _parse_nmap_xml(proc.stdout),
            "notes": "",
        }


def _parse_nmap_xml(xml: str) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return services
    for host in root.findall("host"):
        address_el = host.find("address")
        host_ip = address_el.get("addr") if address_el is not None else None
        for port in host.findall(".//port"):
            state_el = port.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue
            service_el = port.find("service")
            services.append(
                {
                    "host": host_ip,
                    "port": int(port.get("portid", "0")) or None,
                    "protocol": port.get("protocol"),
                    "service": service_el.get("name") if service_el is not None else None,
                    "version": (
                        " ".join(
                            v
                            for v in [
                                service_el.get("product") if service_el is not None else None,
                                service_el.get("version") if service_el is not None else None,
                            ]
                            if v
                        )
                        or None
                    ),
                }
            )
    return services
