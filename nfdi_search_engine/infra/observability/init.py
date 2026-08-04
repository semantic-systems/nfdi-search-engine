from __future__ import annotations

from opentelemetry import trace
from opentelemetry.trace import NoOpTracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON, TraceIdRatioBased, ParentBased
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPGrpcSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHttpSpanExporter

from nfdi_search_engine.infra.observability.config import TracingConfig


def init_tracing(app, cfg: TracingConfig) -> None:
    """
    Configure OpenTelemetry tracing for the Flask app.
    """
    # prevents double initialization, e.g. during testing later
    if getattr(app, "_otel_initialized", False):
        return

    if not cfg.enabled:
        trace.set_tracer_provider(NoOpTracerProvider())
        app._otel_initialized = True
        return

    if cfg.traces_sampler == "always_off":
        sampler = ALWAYS_OFF
    elif cfg.traces_sampler == "always_on":
        sampler = ALWAYS_ON
    elif cfg.traces_sampler in {"traceidratio", "parentbased_traceidratio"}:
        ratio = cfg.traces_sampler_arg if cfg.traces_sampler_arg is not None else 0.05
        base = TraceIdRatioBased(ratio)
        sampler = ParentBased(
            base) if cfg.traces_sampler == "parentbased_traceidratio" else base
    else:
        sampler = ALWAYS_ON

    resource = Resource.create({"service.name": cfg.service_name})
    provider = TracerProvider(resource=resource, sampler=sampler)
    trace.set_tracer_provider(provider)

    if cfg.otlp_protocol == "http/protobuf":
        exporter = OTLPHttpSpanExporter(endpoint=cfg.otlp_endpoint)
    else:
        exporter = OTLPGrpcSpanExporter(endpoint=cfg.otlp_endpoint)

    provider.add_span_processor(BatchSpanProcessor(exporter))

    if cfg.instrument_flask:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)

    if cfg.instrument_requests:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        RequestsInstrumentor().instrument()

    if cfg.instrument_celery:
        # background jobs run after the request has returned, so their spans are
        # linked to the enqueuing request through the broker message headers
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        CeleryInstrumentor().instrument()

    app._otel_initialized = True
