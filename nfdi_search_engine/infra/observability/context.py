from opentelemetry import context as otel_context


def with_parent_context(fn):
    parent_ctx = otel_context.get_current()
    def wrapped(*args, **kwargs):
        token = otel_context.attach(parent_ctx)
        try:
            return fn(*args, **kwargs)
        finally:
            otel_context.detach(token)
    return wrapped
