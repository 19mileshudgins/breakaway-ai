import json
import logging
import re
import time
from typing import Dict, Any, Optional

PII_REGEX_PATTERNS = [
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email addresses
    r"\b\d{3}-\d{2}-\d{4}\b",                          # SSN
    r"\b(?:\d[ -]*?){13,16}\b"                          # Credit cards
]

class AgentJsonFormatter(logging.Formatter):
    """
    Structured JSON log formatter outputting agent intent, execution outcomes, and telemetry.
    Automatically redacts PII data.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": self.redact_pii(record.getMessage()),
            "agent_intent": getattr(record, "agent_intent", None),
            "execution_outcome": getattr(record, "execution_outcome", None),
            "tool_name": getattr(record, "tool_name", None),
            "latency_ms": getattr(record, "latency_ms", None)
        }
        # Filter out None values
        log_data = {k: v for k, v in log_data.items() if v is not None}
        return json.dumps(log_data)

    @staticmethod
    def redact_pii(text: str) -> str:
        if not isinstance(text, str):
            return text
        redacted = text
        for pattern in PII_REGEX_PATTERNS:
            redacted = re.sub(pattern, "[REDACTED_PII]", redacted)
        return redacted

def setup_agent_logging() -> logging.Logger:
    """
    Configures structured JSON logging for BreakawayAI agent operations.
    """
    logger = logging.getLogger("breakaway_ai")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(AgentJsonFormatter())
    
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

def log_agent_trace(
    intent: str,
    outcome: str,
    tool_name: Optional[str] = None,
    latency_ms: Optional[float] = None
):
    """
    Logs explicit agent intent vs execution outcome telemetry.
    """
    logger = logging.getLogger("breakaway_ai")
    extra = {
        "agent_intent": intent,
        "execution_outcome": outcome,
        "tool_name": tool_name,
        "latency_ms": latency_ms
    }
    logger.info(f"Agent Intent: {intent} | Outcome: {outcome}", extra=extra)

def setup_opentelemetry_tracing():
    """
    Initializes OpenTelemetry distributed Cloud Trace telemetry.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider()
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger = logging.getLogger("breakaway_ai")
        logger.info("OpenTelemetry distributed tracing initialized successfully.")
    except Exception as e:
        pass
