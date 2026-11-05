from collections import defaultdict
from threading import Lock
from uuid import uuid4


live_request = defaultdict(list)
_lock = Lock()


def enqueue_request(match_id: int, request: dict) -> str:
    request_id = uuid4().hex

    with _lock:
        live_request[match_id].append({
            **request,
            "request_id": request_id,
        })

    return request_id


def pending_requests(match_id: int) -> list[dict]:
    with _lock:
        return list(live_request.get(match_id, ()))


def acknowledge_requests(match_id: int, request_ids: set[str]) -> None:
    with _lock:
        remaining = [
            request
            for request in live_request.get(match_id, ())
            if request["request_id"] not in request_ids
        ]

        if remaining:
            live_request[match_id] = remaining
        else:
            live_request.pop(match_id, None)


def clear_requests(match_id: int) -> None:
    with _lock:
        live_request.pop(match_id, None)