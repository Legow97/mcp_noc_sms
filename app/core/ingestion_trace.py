from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4


LOGS_DIR = Path("logs")
TRACE_LOG_PATH = LOGS_DIR / "ingestion_trace.log"
SUMMARY_LOG_PATH = LOGS_DIR / "ingestion_summary.jsonl"
_TRACE_CONTEXT: ContextVar["IngestionTraceContext | None"] = ContextVar(
    "ingestion_trace_context",
    default=None,
)
_WRITE_LOCK = threading.Lock()


@dataclass(slots=True)
class IngestionTraceContext:
    trace_id: str
    started_at: str
    source_channel: str | None = None
    case_id: str | None = None
    judge_decision: str | None = None
    final_score: float | None = None
    fallback_triggered: bool | None = None
    timeline_entries_count: int | None = None
    troubleshooting_actions_count: int | None = None
    finalized: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def start_ingestion_trace(
    *,
    source_channel: str | None = None,
    raw_text: str | None = None,
) -> str:
    trace_id = f"ing-{uuid4().hex[:12]}"
    context = IngestionTraceContext(
        trace_id=trace_id,
        started_at=_now_iso(),
        source_channel=source_channel,
    )
    _TRACE_CONTEXT.set(context)
    log_ingestion_event(
        layer="api",
        event="trace_started",
        payload={
            "source_channel": source_channel,
            "raw_text_preview": _truncate(raw_text, 240),
        },
    )
    return trace_id


def get_trace_id() -> str | None:
    context = _TRACE_CONTEXT.get()
    if context is None:
        return None
    return context.trace_id


def bind_case_id(case_id: str | None) -> None:
    context = _TRACE_CONTEXT.get()
    if context is None or not case_id:
        return
    context.case_id = case_id


def bind_judge_result(
    *,
    judge_decision: str | None = None,
    final_score: float | None = None,
    fallback_triggered: bool | None = None,
) -> None:
    context = _TRACE_CONTEXT.get()
    if context is None:
        return
    if judge_decision is not None:
        context.judge_decision = judge_decision
    if final_score is not None:
        context.final_score = final_score
    if fallback_triggered is not None:
        context.fallback_triggered = fallback_triggered


def bind_persistence_counts(
    *,
    timeline_entries_count: int | None = None,
    troubleshooting_actions_count: int | None = None,
) -> None:
    context = _TRACE_CONTEXT.get()
    if context is None:
        return
    if timeline_entries_count is not None:
        context.timeline_entries_count = timeline_entries_count
    if troubleshooting_actions_count is not None:
        context.troubleshooting_actions_count = troubleshooting_actions_count


def log_ingestion_event(
    *,
    layer: str,
    event: str,
    payload: Any | None = None,
    status: str = "ok",
    error: str | None = None,
) -> None:
    context = _TRACE_CONTEXT.get()
    if context is None:
        return

    line = (
        f"{_now_iso()} "
        f"trace_id={context.trace_id} "
        f"case_id={context.case_id or '-'} "
        f"layer={layer} "
        f"event={event} "
        f"status={status}"
    )
    if error:
        line += f" error={_sanitize_text(error)}"
    if payload is not None:
        line += f" payload={_serialize_payload(payload)}"
    _safe_append_text(TRACE_LOG_PATH, line + "\n")


def finalize_ingestion_summary(
    *,
    http_status: int,
    persisted_ok: bool,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    context = _TRACE_CONTEXT.get()
    if context is None or context.finalized:
        return

    summary = {
        "timestamp": _now_iso(),
        "trace_id": context.trace_id,
        "case_id": context.case_id,
        "source_channel": context.source_channel,
        "judge_decision": context.judge_decision,
        "final_score": context.final_score,
        "fallback_triggered": context.fallback_triggered,
        "timeline_entries_count": context.timeline_entries_count,
        "troubleshooting_actions_count": context.troubleshooting_actions_count,
        "persisted_ok": persisted_ok,
        "http_status": http_status,
        "error_type": error_type,
        "error_message": _truncate(error_message, 500),
    }
    _safe_append_text(
        SUMMARY_LOG_PATH,
        json.dumps(summary, ensure_ascii=True, default=str) + "\n",
    )
    context.finalized = True
    _TRACE_CONTEXT.set(None)


def _safe_append_text(path: Path, content: str) -> None:
    try:
        with _WRITE_LOCK:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as file_handle:
                file_handle.write(content)
                file_handle.flush()
    except Exception:
        return


def _serialize_payload(payload: Any) -> str:
    compact = _to_compact_data(payload)
    try:
        return json.dumps(compact, ensure_ascii=True, default=str, separators=(",", ":"))
    except Exception:
        return json.dumps({"repr": _truncate(repr(payload), 500)}, ensure_ascii=True)


def _to_compact_data(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return _truncate(value, 500) if isinstance(value, str) else value
    if isinstance(value, dict):
        return {str(k): _to_compact_data(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_compact_data(item) for item in value[:20]]
    if hasattr(value, "model_dump"):
        return _to_compact_data(value.model_dump(mode="json"))
    if hasattr(value, "__dict__"):
        return _truncate(repr(value), 500)
    return _truncate(str(value), 500)


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def _sanitize_text(value: str) -> str:
    return (_truncate(value, 500) or "").replace(" ", "_")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
