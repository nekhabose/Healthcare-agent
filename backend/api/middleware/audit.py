"""
HIPAA audit middleware — logs every request that touches PHI.

Logs contain: timestamp, method, path, user_id, patient_id (if in path).
Never logs request/response bodies (which may contain PHI).
"""
import logging
import time
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("hipaa.audit")

# Paths that may involve PHI — match for audit logging
PHI_PATH_PATTERN = re.compile(
    r"/(patients|discharges|sessions|escalations|dashboard)"
)


class HIPAAAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        if PHI_PATH_PATTERN.search(request.url.path):
            user_id = self._extract_user_id(request)
            logger.info(
                "PHI_ACCESS method=%s path=%s status=%s user_id=%s duration_ms=%s",
                request.method,
                request.url.path,
                response.status_code,
                user_id,
                duration_ms,
            )

        return response

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # Decode without verification — user_id is non-sensitive metadata
            import base64, json
            try:
                payload_b64 = auth.split(".")[1] + "=="
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                return payload.get("sub")
            except Exception:
                pass
        return None
