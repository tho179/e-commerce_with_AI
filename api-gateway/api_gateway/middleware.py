import time
import uuid

from .telemetry import record_trace


class RequestTelemetryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        started = time.perf_counter()

        response = self.get_response(request)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        record_trace(
            path=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=elapsed_ms,
            request_id=request_id,
        )
        response["X-Request-Id"] = request_id
        return response
