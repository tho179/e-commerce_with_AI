import threading
import time
from collections import defaultdict, deque

_lock = threading.Lock()
_events = defaultdict(lambda: deque())


def is_rate_limited(key, limit, window_seconds):
    now = time.time()
    with _lock:
        queue = _events[key]
        while queue and now - queue[0] > window_seconds:
            queue.popleft()
        if len(queue) >= limit:
            return True
        queue.append(now)
        return False
