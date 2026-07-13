from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal

OtlpProtocol = Literal[
    "grpc",
    "http/protobuf"
]

SamplerName = Literal[
    "always_on",
    "always_off",
    "traceidratio",
    "parentbased_traceidratio"
]


@dataclass(frozen=True)
class TracingConfig:
    """
    Configuration for OpenTelemetry tracing initialization.

    :param enabled: Global on/off switch. If False, a NoOp tracer provider is installed.
    :type enabled: bool
    :param service_name: OTel resource service name ("service.name").
    :type service_name: str
    :param otlp_endpoint: OTLP exporter endpoint, e.g. "otel-collector:4317" (gRPC) or "http://otel-collector:4318" (HTTP).
    :type otlp_endpoint: str
    :param otlp_protocol: OTLP protocol ("grpc" or "http/protobuf").
    :type otlp_protocol: OtlpProtocol
    :param traces_sampler: Sampling strategy.
    :type traces_sampler: SamplerName
    :param traces_sampler_arg: Ratio for ratio-based samplers (e.g. 0.05 for 5%).
    :type traces_sampler_arg: Optional[float]
    :param instrument_flask: Enable Flask auto-instrumentation.
    :type instrument_flask: bool
    :param instrument_requests: Enable requests auto-instrumentation.
    :type instrument_requests: bool
    :param instrument_celery: Enable Celery auto-instrumentation.
    :type instrument_celery: bool
    """
    enabled: bool
    service_name: str = "nfdi-search-engine"
    otlp_endpoint: str = "otel-collector:4317"
    otlp_protocol: OtlpProtocol = "grpc"
    traces_sampler: SamplerName = "always_on"
    traces_sampler_arg: Optional[float] = None
    instrument_flask: bool = True
    instrument_requests: bool = True
    instrument_celery: bool = True

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "TracingConfig":
        return cls(
            enabled=bool(cfg.get("TRACING_ENABLED", False)),
            service_name=str(cfg.get(
                "TRACING_SERVICE_NAME",
                "nfdi-search-engine"
            )),
            otlp_endpoint=str(cfg.get(
                "TRACING_OTLP_ENDPOINT",
                "otel-collector:4317"
            )),
            otlp_protocol=cfg.get("TRACING_OTLP_PROTOCOL", "grpc"),
            traces_sampler=cfg.get("TRACING_SAMPLER", "always_on"),
            traces_sampler_arg=(
                float(cfg["TRACING_SAMPLER_ARG"])
                if cfg.get("TRACING_SAMPLER_ARG") is not None else None
            ),
            instrument_flask=bool(cfg.get("TRACING_INSTRUMENT_FLASK", True)),
            instrument_requests=bool(cfg.get(
                "TRACING_INSTRUMENT_REQUESTS",
                True
            )),
            instrument_celery=bool(cfg.get("TRACING_INSTRUMENT_CELERY", True)),
        )
