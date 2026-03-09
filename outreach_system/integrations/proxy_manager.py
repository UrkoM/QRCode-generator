from __future__ import annotations
import logging
import os
from typing import Optional
from config import config

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages a list of residential proxies for Mode A accounts.
    Each LinkedIn account should use a dedicated proxy.

    Proxy file format (one per line):
        user:password@host:port
    or
        host:port
    """

    def __init__(self, proxy_file: str = None):
        self.proxy_file = proxy_file or config.PROXY_LIST_FILE
        self._proxies: list[str] = []
        self._used: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.proxy_file):
            logger.warning(f"Proxy file not found: {self.proxy_file}. Running without proxies.")
            return
        with open(self.proxy_file, "r") as f:
            self._proxies = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(self._proxies)} proxies")

    def get_available_proxy(self) -> Optional[str]:
        """Returns an unused proxy, or None if none available."""
        for proxy in self._proxies:
            if proxy not in self._used:
                self._used.add(proxy)
                return proxy
        logger.warning("No available proxies — using direct connection (risky for Mode A)")
        return None

    def release_proxy(self, proxy: str) -> None:
        self._used.discard(proxy)

    def get_all(self) -> list[str]:
        return list(self._proxies)
