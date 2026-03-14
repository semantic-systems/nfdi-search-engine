import base64
import time

from flask import abort


def validate_ts_token(ts: str, *, max_age_s: int = 3600) -> None:
    """
    ts is a urlsafe base64-encoded timestamp (int/float as string).
    Aborts 404 if invalid or older than max_age_s for bot id.
    Might be removed once we move to cloudflare.
    """
    try:
        # robust padding: add 0..3 '='
        pad = (4 - (len(ts) % 4)) % 4
        padded = ts.encode("utf-8") + b"=" * pad

        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        diff = int(time.time()) - int(float(decoded))
        if diff > max_age_s:
            abort(404)
    except Exception:
        abort(404)
