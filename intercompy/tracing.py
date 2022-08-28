"""Setup observability stuff"""

import opentelemetry
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from intercompy.config import Tracing

# pylint: disable=global-at-module-level
TRACING_CONFIG = None


def setup_tracing(cfg: Tracing):
    """
    Setup the Opentelemetry tracing system, and save the configuration globally for the @trace
    decorator to use later.
    """
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="https://api.honeycomb.io"))
    provider.add_span_processor(processor)
    opentelemetry.trace.set_tracer_provider(provider)

    global TRACING_CONFIG
    TRACING_CONFIG = cfg

    RequestsInstrumentor().instrument()


def get_tracer():
    return opentelemetry.trace.get_tracer("intercompy")


def trace(func):
    """Decorator for tracing"""

    def wrapper_trace(*args, **kwargs):
        """Create a new span with the """
        tracer = get_tracer()
        with tracer.start_as_current_span(func.__name__, attributes={
            "service.name": "intercompy",
            "intercom.name": TRACING_CONFIG.intercom_name
        }):
            return func(*args, **kwargs)

    return wrapper_trace
