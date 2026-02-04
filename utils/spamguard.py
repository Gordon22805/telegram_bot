import time
from config import COOLDOWN_SECONDS

_last_action = {}  # user_id -> timestamp

def can_proceed(user_id: int) -> bool:
    now = time.time()
    last = _last_action.get(user_id, 0)
    if now - last < COOLDOWN_SECONDS:
        return False
    _last_action[user_id] = now
    return True
