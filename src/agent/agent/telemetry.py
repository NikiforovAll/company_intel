from __future__ import annotations

import logging
import os

import logfire
from opentelemetry._logs import get_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import Histogram, UpDownCounter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View


def _configure_aspire_otlp() -> None:
    """Aspire's gRPC OTLP endpoint requires HTTP/2 ALPN which Python can't do.
    Use the HTTP OTLP endpoint instead (accepts HTTP/1.1)."""
    http_endpoint = os.environ.get("DOTNET_DASHBOARD_OTLP_HTTP_ENDPOINT_URL")
    if http_endpoint:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = http_endpoint
        os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
        # Aspire dashboard cannot render exponential histograms (dotnet/aspire#4381)
        os.environ.setdefault(
            "OTEL_EXPORTER_OTLP_METRICS_DEFAULT_HISTOGRAM_AGGREGATION",
            "explicit_bucket_histogram",
        )
        os.environ.setdefault(
            "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE",
            "cumulative",
        )


def configure_telemetry() -> None:
    _configure_aspire_otlp()
    # Logfire DEFAULT_VIEWS forces ExponentialBucketHistogramAggregation
    # which Aspire dashboard cannot render (dotnet/aspire#4381).
    # Override with explicit buckets.
    aspire_views = [
        View(
            instrument_type=Histogram,
            aggregation=ExplicitBucketHistogramAggregation(),
        ),
        View(
            instrument_type=UpDownCounter,
            instrument_name="http.server.active_requests",
            attribute_keys={
                "url.scheme",
                "http.scheme",
                "http.flavor",
                "http.method",
                "http.request.method",
            },
        ),
    ]
    logfire.configure(
        service_name="company-intel-agent",
        send_to_logfire=False,
        inspect_arguments=False,
        metrics=logfire.MetricsOptions(
            additional_readers=[
                PeriodicExportingMetricReader(OTLPMetricExporter()),
            ],
            views=aspire_views,
        ),
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx()

    provider = get_logger_provider()
    if hasattr(provider, "add_log_record_processor"):
        provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))

    logging.basicConfig(
        handlers=[LoggingHandler(), logging.StreamHandler()],
        level=logging.INFO,
    )
    logging.getLogger("agent").setLevel(logging.DEBUG)
