"""
Rate Limiter berbasis Sliding Window in-memory untuk endpoint sensitif Kiosk.
Huawei ICT Competition 2026–2027 | Innovation Track
Team: Inovexa
"""

import time
import threading
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, HTTPException, status
from app.core.config import settings


class InMemoryRateLimiter:
    """
    Sliding window rate limiter berbasis in-memory.
    Thread-safe menggunakan threading.Lock.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60, name: str = "generic"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name
        self._lock = threading.Lock()
        self._history: dict[str, deque[float]] = defaultdict(deque)
        self._last_cleanup = time.monotonic()

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        # Periksa header X-Forwarded-For jika di balik reverse proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()

        now = time.monotonic()

        with self._lock:
            # 1. Bersihkan memory jika sudah lebih dari 2x window
            if now - self._last_cleanup > (self.window_seconds * 2):
                self._cleanup(now)

            # 2. Ambil riwayat IP klien
            timestamps = self._history[client_ip]

            # 3. Evict timestamp yang sudah di luar sliding window
            cutoff = now - self.window_seconds
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            # 4. Evaluasi kuota
            if len(timestamps) >= self.max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Terlalu banyak permintaan. Silakan tunggu beberapa saat lagi.",
                    headers={"Retry-After": str(retry_after)},
                )

            # 5. Catat permintaan baru
            timestamps.append(now)

    def _cleanup(self, now: float) -> None:
        """Pembersihan kunci IP yang sudah tidak aktif."""
        cutoff = now - self.window_seconds
        stale_keys = [k for k, q in self._history.items() if not q or q[-1] <= cutoff]
        for k in stale_keys:
            del self._history[k]
        self._last_cleanup = now


# Instansiasi dependency rate limiter terkonfigurasi
rate_limit_rfid = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_RFID_PER_MINUTE,
    window_seconds=60,
    name="rfid_identify",
)

rate_limit_session_create = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_SESSION_CREATE_PER_MINUTE,
    window_seconds=60,
    name="session_create",
)
