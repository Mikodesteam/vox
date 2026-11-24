# Excerpt from VOX (app/voice/rings.py). Shown for illustration only.
# The full source code is available at https://store.mikodes.com/p/vox/
#
# Decides which privacy ring an outbound phone call runs under. A call counts as
# a call to the owner only if the dialled number really is the owner's verified number;
# everyone else hears an AI disclosure first, and cold-call campaigns are refused outright.

"""The three call rings — the Python half of app/src/call.js.

THE RINGS ARE ENFORCED HERE, STRUCTURALLY — not by a config flag.

  SELF   → the assistant calls its own user. Consent is inherent: their number, their setup.
  THIRD  → anyone else. The AI disclosure is spoken FIRST, the callee cannot talk over it,
           and there is no parameter that removes it.
  COLD   → campaign dialling. Not implemented, and must not be.

One thing this half adds over call.js: the ring is not taken on trust. A call asked for as
SELF is only SELF when the number dialled IS the user's own number from the profile. Any other
number — a typo, a placeholder, a number the model found in an email — is a third party, and
the callee hears the disclosure. Unknown always falls toward disclosure, never away from it.

EU AI Act Art. 50 (enforceable 2026-08-02) and US TCPA (FCC, Feb 2024).
If a future code path can disable the disclosure, that path is a bug. Treat it as one.
"""
# …
from __future__ import annotations

import re
from enum import Enum
# …
class Ring(str, Enum):
    SELF = "self"
    THIRD = "third_party"
    COLD = "cold"

# …
class RingForbidden(Exception):
    code = "RING_FORBIDDEN"

    def __init__(self):
        super().__init__(
            "Cold-call campaigns are not implemented and must not be. US TCPA exposure is "
            "$500-1500 per call with no aggregate cap; one campaign to 1,000 wrong numbers is "
            "$500k-1.5M."
        )

# …
def normalize_number(number: str | None) -> str | None:
    """E.164-ish digits, or None when it is not a real, complete number (e.g. '+421 9xx xxx xxx')."""
    if not number:
        return None
    raw = str(number).strip()
    # ASCII only: \d would also match Arabic-Indic or full-width digits.
    if re.search(r"[^0-9 +().\-/]", raw):  # letters, 'x' placeholders, anything odd
        return None
    digits = re.sub(r"[^0-9]", "", raw)
    if raw.startswith("00"):
        digits = digits[2:]
    elif not raw.startswith("+"):
        return None  # no country code → cannot prove it is the same number
    if not 8 <= len(digits) <= 15:
        return None
    return "+" + digits


def resolve_ring(requested: Ring | str, to: str | None, user_phone: str | None) -> Ring:
    """The ring a call actually runs under. Raises RingForbidden for COLD, before anything else."""
    requested = Ring(requested)
    if requested is Ring.COLD:
        raise RingForbidden()
    dialled, own = normalize_number(to), normalize_number(user_phone)
    if requested is Ring.SELF and dialled is not None and dialled == own:
        return Ring.SELF
    return Ring.THIRD
