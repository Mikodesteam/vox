# Excerpt from VOX (app/voice/disclosure.py). Shown for illustration only.
# The full source code is available at https://store.mikodes.com/p/vox/
#
# Proof that the AI disclosure was actually played to the callee. The server sends a marker
# behind the disclosure audio and counts it heard only when the telephony provider echoes that
# exact marker back. An echo is accepted once, for this stream only, for a marker really sent.

import asyncio
import hmac
# …

class PlayoutMarks:
    # …
    def __init__(self, stream_sid: str, send: Callable[[dict], Awaitable] | None = None):
        self.stream_sid = str(stream_sid)
        self.send = send                      # for mark(); frame() goes through the pipeline
        self._pending: dict[str, asyncio.Future] = {}
        self._sent: set[str] = set()
        self.echoes: list[str] = []           # names accepted, in order (tests, logs)
        self.ignored = 0

    # …

    def sent(self, name: str):
        if name in self._pending:
            self._sent.add(name)

    def was_sent(self, name: str) -> bool:
        return name in self._sent

    def echoed(self, message: dict) -> bool:
        """An inbound `mark` event from Twilio. True if it completed one of our marks."""
        sid = message.get("streamSid")
        mark = message.get("mark")
        name = mark.get("name") if isinstance(mark, dict) else None
        if not (isinstance(sid, str) and hmac.compare_digest(sid.encode(), self.stream_sid.encode())
                and isinstance(name, str) and name in self._sent):
            self.ignored += 1
            logger.warning("ignored a Twilio mark echo that is not one this stream sent")
            return False
        self._sent.discard(name)
        fut = self._pending.pop(name, None)
        if fut is None or fut.done():
            return False
        self.echoes.append(name)
        fut.set_result(asyncio.get_running_loop().time())
        return True

    def close(self):
        """The stream ended: nobody waits for an echo any more."""
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()
        self._sent.clear()
