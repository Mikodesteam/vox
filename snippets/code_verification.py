# Excerpt from VOX (app/voice/channels/verify.py). Shown for illustration only.
# The full source code is available at https://store.mikodes.com/p/vox/
#
# Read-back verification: a destination (a chat, a mailbox) only counts as the user's own after
# they type back a 6-digit code. Only a salted hash is stored, codes expire after 10 minutes,
# and five wrong tries cancel the attempt. The comparison is constant-time.

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from . import store

TTL_SECS = 10 * 60
MAX_ATTEMPTS = 5


def code_hash(salt: str, code: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(10 ** 6):06d}"


def sealed(code: str, now: datetime) -> dict:
    """The fields a state file keeps for `code`: never the code itself."""
    salt = secrets.token_hex(8)
    return {"salt": salt, "hash": code_hash(salt, code), "expires": (now + timedelta(seconds=TTL_SECS)).timestamp(),
            "attempts": 0}


# …


def check(data_dir, name: str, code, now: datetime) -> dict:
    """The state when `code` is right (the state file is removed); ChannelError otherwise."""
    state = store.read_json(data_dir, name)
    if not state or not state.get("hash"):
        raise store.ChannelError(404, "NO_VERIFICATION", "No verification is in progress — start one first.")
    try:
        expired = now.timestamp() > float(state.get("expires", 0))
    except (TypeError, ValueError):
        expired = True
    if expired:
        store.remove(data_dir, name)
        raise store.ChannelError(410, "CODE_EXPIRED", "The code expired — start the verification again.")
    if int(state.get("attempts", 0)) >= MAX_ATTEMPTS:
        store.remove(data_dir, name)
        raise store.ChannelError(429, "TOO_MANY_ATTEMPTS", "Too many wrong codes — start the verification again.")
    given = str(code or "").strip().replace(" ", "")
    if not hmac.compare_digest(code_hash(str(state.get("salt")), given), str(state["hash"])):
        state["attempts"] = int(state.get("attempts", 0)) + 1
        store.write_json(data_dir, name, state)
        raise store.ChannelError(422, "BAD_CODE", f"Wrong code (attempts left: {MAX_ATTEMPTS - state['attempts']}).")
    store.remove(data_dir, name)
    return state
