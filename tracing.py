import inspect
from functools import wraps
from opentelemetry import trace

_tracer = trace.get_tracer("nfdi-se")

def traced(name: str | None = None, *, include_code_meta: bool = True):
    def deco(fn):
        span_name = name or fn.__qualname__  # e.g. "Module.func"
        if include_code_meta:
            file = inspect.getsourcefile(fn) or ""
            _, lineno = inspect.getsourcelines(fn)
            mod = fn.__module__
        else:
            file, lineno, mod = "", 0, fn.__module__

        @wraps(fn)
        def wrapper(*args, **kwargs):
            with _tracer.start_as_current_span(span_name) as span:
                if include_code_meta:
                    span.set_attribute("code.function", fn.__qualname__)
                    span.set_attribute("code.namespace", mod)
                    span.set_attribute("code.filepath", file)
                    span.set_attribute("code.lineno", lineno)
                return fn(*args, **kwargs)
        return wrapper
    return deco