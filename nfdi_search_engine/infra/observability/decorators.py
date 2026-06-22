from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("nfdi_search_engine")


def traced(
    name: Optional[str] = None,
    *,
    attrs: Optional[Callable[..., dict[str, Any]]] = None,
):
    """
    Decorator to create an OpenTelemetry span around a function.

    - name: span name (defaults to qualname)
    - attrs: optional callback that returns span attributes from *args/**kwargs
    """
    def deco(fn: Callable[..., Any]):
        span_name = name or fn.__qualname__

        @wraps(fn)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                if attrs:
                    try:
                        for k, v in (attrs(*args, **kwargs) or {}).items():
                            if v is not None:
                                span.set_attribute(k, v)
                    except Exception:
                        # never fail the request because of tracing
                        pass
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        return wrapper
    return deco
