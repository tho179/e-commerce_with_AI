import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_started_at = time.time()
_request_count = 0
_status_counts = defaultdict(int)
_path_counts = defaultdict(int)
_total_latency_ms = 0.0
_recent_traces = deque(maxlen=200)


def record_trace(path, method, status_code, duration_ms, request_id):
    global _request_count, _total_latency_ms
    with _lock:
        _request_count += 1
        _status_counts[str(status_code)] += 1
        _path_counts[path] += 1
        _total_latency_ms += duration_ms
        _recent_traces.appendleft(
            {
                "request_id": request_id,
                "path": path,
                "method": method,
                "status": status_code,
                "duration_ms": round(duration_ms, 2),
                "timestamp": int(time.time()),
            }
        )


def metrics_snapshot(top_paths=8):
    with _lock:
        avg_latency = (_total_latency_ms / _request_count) if _request_count else 0.0
        top = sorted(_path_counts.items(), key=lambda item: item[1], reverse=True)[:top_paths]
        return {
            "uptime_seconds": int(time.time() - _started_at),
            "request_count": _request_count,
            "average_latency_ms": round(avg_latency, 2),
            "status_counts": dict(_status_counts),
            "top_paths": [{"path": path, "count": count} for path, count in top],
        }


def traces_snapshot(limit=20):
    with _lock:
        return list(_recent_traces)[:limit]
