"""
MLflow Monitoring Service
Tracks token usage, costs, and performance for every LLM call in the OCR pipeline.

Usage:
    from services.monitoring_service import tracker
    tracker.log_llm_call(response, call_type="detection", document_type="SIEMENS RMU")

Dashboard:
    mlflow ui --host 0.0.0.0 --port 5000
"""

import os
import time
from datetime import datetime
from typing import Optional

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    print("[MONITORING] MLflow not installed. Run: pip install mlflow")

# ── GPT-4o-mini pricing (USD per 1K tokens) ─────────────────────────────────
PRICING = {
    "gpt-4o-mini": {"input": 0.000150, "output": 0.000600},   # per 1K tokens
    "gpt-4o":      {"input": 0.002500, "output": 0.010000},
    "gpt-4-turbo": {"input": 0.010000, "output": 0.030000},
}
DEFAULT_MODEL = "gpt-4o-mini"

EXPERIMENT_NAME = "Raas-OCR Token Monitoring"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow_raas_ocr.db")


class TokenMonitor:
    """
    Singleton service that logs every LLM call to MLflow.
    Each call is a separate MLflow run tagged by document type and call type.
    A parent 'session' run is opened per OCR request to group related calls.
    """

    def __init__(self):
        self._active_parent_run_id: Optional[str] = None
        self._session_tokens = {"input": 0, "output": 0, "total": 0, "cost": 0.0}
        self._session_calls = 0
        self._session_doc_type: Optional[str] = None
        self._session_start: Optional[float] = None

        if not MLFLOW_AVAILABLE:
            return

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        # Create or get experiment
        try:
            experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
            if experiment is None:
                mlflow.create_experiment(EXPERIMENT_NAME)
            mlflow.set_experiment(EXPERIMENT_NAME)
            print(f"[MONITORING] MLflow ready → {MLFLOW_TRACKING_URI}")
            print(f"[MONITORING] Dashboard: mlflow ui --host 0.0.0.0 --port 5000")
        except Exception as e:
            print(f"[MONITORING] MLflow init warning: {e}")

    # ── Session Management ─────────────────────────────────────────────────

    def start_session(self, document_name: str, document_type: Optional[str] = None):
        """
        Open a parent MLflow run for one full OCR request.
        All individual LLM calls (detection + extraction) nest under this run.
        """
        if not MLFLOW_AVAILABLE:
            return

        self._session_tokens = {"input": 0, "output": 0, "total": 0, "cost": 0.0}
        self._session_calls = 0
        self._session_doc_type = document_type or "UNKNOWN"
        self._session_start = time.time()

        try:
            parent_run = mlflow.start_run(
                run_name=f"[SESSION] {document_name[:40]}",
                tags={
                    "session_type": "ocr_request",
                    "document_name": document_name[:100],
                    "document_type": document_type or "auto-detect",
                    "started_at": datetime.now().isoformat(),
                },
            )
            self._active_parent_run_id = parent_run.info.run_id
            print(f"[MONITORING] Session started → run_id={self._active_parent_run_id[:8]}...")
        except Exception as e:
            print(f"[MONITORING] start_session error: {e}")
            self._active_parent_run_id = None

    def end_session(self):
        """
        Close the parent run and log session-level aggregated metrics.
        """
        if not MLFLOW_AVAILABLE or not self._active_parent_run_id:
            return

        try:
            elapsed = time.time() - (self._session_start or time.time())

            # Log aggregated session totals to the parent run
            with mlflow.start_run(
                run_id=self._active_parent_run_id,
                tags={"ended_at": datetime.now().isoformat()},
            ):
                mlflow.log_metrics({
                    "session_total_input_tokens":  self._session_tokens["input"],
                    "session_total_output_tokens": self._session_tokens["output"],
                    "session_total_tokens":        self._session_tokens["total"],
                    "session_total_cost_usd":      round(self._session_tokens["cost"], 6),
                    "session_llm_calls":           self._session_calls,
                    "session_duration_seconds":    round(elapsed, 2),
                })
                mlflow.log_param("final_document_type", self._session_doc_type or "unknown")

            mlflow.end_run()
            print(
                f"[MONITORING] Session ended | "
                f"calls={self._session_calls} | "
                f"tokens={self._session_tokens['total']} | "
                f"cost=${self._session_tokens['cost']:.6f} | "
                f"time={elapsed:.1f}s"
            )
        except Exception as e:
            print(f"[MONITORING] end_session error: {e}")
        finally:
            self._active_parent_run_id = None

    # ── LLM Call Logging ──────────────────────────────────────────────────

    def log_llm_call(
        self,
        response,
        call_type: str = "extraction",
        document_type: Optional[str] = None,
        page_num: Optional[int] = None,
        model: str = DEFAULT_MODEL,
    ):
        """
        Log one LLM invoke() call.

        Args:
            response:      The LangChain response object (has .usage_metadata)
            call_type:     'detection' or 'extraction'
            document_type: The identified/assumed document type
            page_num:      Page number being processed
            model:         Model name for cost calculation
        """
        # ── Extract token counts from LangChain response ──────────────────
        input_tokens = 0
        output_tokens = 0

        usage = getattr(response, "usage_metadata", None)
        if usage:
            input_tokens  = getattr(usage, "input_tokens",  0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
        else:
            # Fallback: try response_metadata (older LangChain versions)
            meta = getattr(response, "response_metadata", {}) or {}
            token_usage = meta.get("token_usage", {})
            input_tokens  = token_usage.get("prompt_tokens", 0)
            output_tokens = token_usage.get("completion_tokens", 0)

        total_tokens = input_tokens + output_tokens

        # ── Cost calculation ──────────────────────────────────────────────
        price = PRICING.get(model, PRICING[DEFAULT_MODEL])
        cost_usd = (
            (input_tokens  / 1000) * price["input"] +
            (output_tokens / 1000) * price["output"]
        )

        # ── Update session-level accumulators ─────────────────────────────
        self._session_tokens["input"]  += input_tokens
        self._session_tokens["output"] += output_tokens
        self._session_tokens["total"]  += total_tokens
        self._session_tokens["cost"]   += cost_usd
        self._session_calls += 1

        # Update session doc type if we detected it
        if document_type and document_type != "UNKNOWN":
            self._session_doc_type = document_type

        # ── Console log ───────────────────────────────────────────────────
        print(
            f"[TOKEN] {call_type.upper()} | "
            f"doc={document_type or 'unknown'} | "
            f"page={page_num or '-'} | "
            f"in={input_tokens} out={output_tokens} total={total_tokens} | "
            f"cost=${cost_usd:.6f}"
        )

        # ── Log to MLflow ─────────────────────────────────────────────────
        if not MLFLOW_AVAILABLE:
            return

        try:
            run_name = f"[{call_type.upper()}] {document_type or 'unknown'}"
            if page_num is not None:
                run_name += f" p{page_num}"

            nested = self._active_parent_run_id is not None

            with mlflow.start_run(
                run_name=run_name,
                nested=nested,
                tags={
                    "call_type":     call_type,
                    "document_type": document_type or "unknown",
                    "model":         model,
                    "page_num":      str(page_num) if page_num else "N/A",
                    "timestamp":     datetime.now().isoformat(),
                },
            ):
                mlflow.log_metrics({
                    "input_tokens":  input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens":  total_tokens,
                    "cost_usd":      round(cost_usd, 6),
                })
                mlflow.log_params({
                    "call_type":     call_type,
                    "document_type": (document_type or "unknown")[:250],
                    "model":         model,
                })

        except Exception as e:
            print(f"[MONITORING] log_llm_call mlflow error: {e}")

    # ── Stats API ─────────────────────────────────────────────────────────

    def get_session_stats(self) -> dict:
        """Return current session token stats (for the API endpoint)."""
        return {
            "session_active":       self._active_parent_run_id is not None,
            "llm_calls_this_session": self._session_calls,
            "tokens": {
                "input":  self._session_tokens["input"],
                "output": self._session_tokens["output"],
                "total":  self._session_tokens["total"],
            },
            "estimated_cost_usd": round(self._session_tokens["cost"], 6),
            "document_type": self._session_doc_type,
            "mlflow_tracking_uri": MLFLOW_TRACKING_URI,
            "mlflow_experiment": EXPERIMENT_NAME,
        }

    def get_all_time_stats(self) -> dict:
        """Query MLflow for all-time aggregated stats."""
        if not MLFLOW_AVAILABLE:
            return {"error": "MLflow not installed"}

        try:
            experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
            if not experiment:
                return {"error": "No experiment found yet. Run some extractions first."}

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string="tags.call_type != ''",   # only leaf call runs
                order_by=["start_time DESC"],
            )

            if runs.empty:
                return {"total_runs": 0, "message": "No LLM calls logged yet."}

            total_input  = int(runs.get("metrics.input_tokens",  0).sum())
            total_output = int(runs.get("metrics.output_tokens", 0).sum())
            total_cost   = float(runs.get("metrics.cost_usd",    0.0).sum())

            # Group by document_type
            by_doc = {}
            if "tags.document_type" in runs.columns:
                for doc_type, group in runs.groupby("tags.document_type"):
                    by_doc[doc_type] = {
                        "calls":        len(group),
                        "total_tokens": int(group.get("metrics.total_tokens", 0).sum()),
                        "cost_usd":     round(float(group.get("metrics.cost_usd", 0.0).sum()), 6),
                    }

            return {
                "total_llm_calls":     len(runs),
                "total_input_tokens":  total_input,
                "total_output_tokens": total_output,
                "total_tokens":        total_input + total_output,
                "total_cost_usd":      round(total_cost, 6),
                "by_document_type":    by_doc,
                "mlflow_ui":           "http://localhost:9000",
            }

        except Exception as e:
            return {"error": str(e)}


# ── Singleton ─────────────────────────────────────────────────────────────────
tracker = TokenMonitor()
