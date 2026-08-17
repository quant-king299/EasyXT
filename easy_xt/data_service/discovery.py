"""EasyXT 局域网服务发现（mDNS/Bonjour）。"""

from __future__ import annotations

import logging
import socket
from typing import Any, Dict, Optional

SERVICE_TYPE = "_easyxt._tcp.local."
logger = logging.getLogger(__name__)


def _lan_ipv4(hostname: str) -> list[str]:
    """Return non-loopback IPv4 addresses for all active network interfaces."""
    candidates = socket.getaddrinfo(hostname, None, socket.AF_INET)
    addresses = []
    for item in candidates:
        address = item[4][0]
        if not address.startswith("127.") and address not in addresses:
            addresses.append(address)
    # Put the interface selected for the local multicast route first; this
    # avoids advertising a VPN/virtual adapter before the real LAN adapter.
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("224.0.0.251", 5353))
        preferred = probe.getsockname()[0]
        probe.close()
        if preferred in addresses:
            addresses.remove(preferred)
            addresses.insert(0, preferred)
    except OSError:
        pass
    return addresses


def publish_service(node_id: str, port: int):
    """广播 EasyXT 数据节点；缺少 zeroconf 时安全降级。"""
    try:
        from zeroconf import ServiceInfo, Zeroconf
        host = socket.gethostname()
        addresses = _lan_ipv4(host)
        if not addresses:
            raise RuntimeError("no non-loopback IPv4 address")
        info = ServiceInfo(
            SERVICE_TYPE,
            f"{node_id}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(address) for address in addresses],
            port=port,
            properties={"node_id": node_id.encode(), "api": b"easyxt-data-v1"},
            server=f"{host}.local.",
        )
        zc = Zeroconf()
        zc.register_service(info)
        logger.info("EasyXT mDNS service published: %s:%s", host, port)
        return zc, info
    except Exception as exc:
        logger.info("mDNS unavailable, fallback to configured host: %s", exc)
        return None


def discover_service(timeout_ms: int = 1500) -> Optional[Dict[str, Any]]:
    """发现局域网中第一个 EasyXT 数据节点。"""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        return None

    found: Dict[str, Any] = {}

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            info = zc.get_service_info(type_, name, timeout=timeout_ms)
            if info and info.addresses:
                found.update({"host": socket.inet_ntoa(info.addresses[0]), "port": info.port,
                              "node_id": info.properties.get(b"node_id", b"").decode(errors="ignore")})

        def update_service(self, zc, type_, name):
            self.add_service(zc, type_, name)

        def remove_service(self, zc, type_, name):
            return None

    zc = Zeroconf()
    browser = ServiceBrowser(zc, SERVICE_TYPE, Listener())
    import time
    time.sleep(timeout_ms / 1000)
    browser.cancel()
    zc.close()
    return found or None
