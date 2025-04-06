import inspect
import json
import logging
import time
import traceback
from functools import wraps
from typing import Any, Callable

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None # Define a fallback if pydantic is not available

logger = logging.getLogger(__name__) # Use a logger specific to this module

def log_tool_execution(func: Callable) -> Callable:
    """Decorator to log tool execution details."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = time.time()
        try:
            sig = inspect.signature(func)
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            # Filter out 'ctx' which is common and often large/complex
            log_params = {k: v for k, v in bound_args.arguments.items() if k != 'ctx'}
            # Simplified logging for potentially large/complex objects
            for k, v in log_params.items():
                if isinstance(v, str) and len(v) > 100:
                    log_params[k] = f"{v[:100]}..."
                elif isinstance(v, (list, tuple)) and len(v) > 5:
                    preview = [repr(item)[:30] + ('...' if isinstance(item, str) and len(item) > 30 else '') for item in v[:5]]
                    log_params[k] = f"[{', '.join(preview)}... ({len(v)} items)]"
                elif isinstance(v, dict) and len(v) > 5:
                    log_params[k] = f"Dict[{len(v)}]"
                elif BaseModel and isinstance(v, BaseModel): # Check if BaseModel exists
                    try:
                        # Attempt to dump, but keep it concise
                        dumped = v.model_dump(exclude_defaults=True, exclude_none=True)
                        dumped_json = json.dumps(dumped, default=str)
                        log_params[k] = dumped if len(dumped_json) <= 150 else f"{type(v).__name__}[{len(dumped)} keys]"
                    except Exception:
                        log_params[k] = f"{type(v).__name__}" # Fallback to type name

            logger.info(f"🛠️ EXECUTING TOOL: {func_name}")
            # Use DEBUG level for potentially verbose parameters
            logger.debug(f"   PARAMS: {json.dumps(log_params, default=str)}")
        except Exception as log_err:
            # Log param formatting errors less severely
            logger.warning(f"⚠️ Param log error for {func_name}: {log_err}")
            logger.info(f"🛠️ EXECUTING TOOL: {func_name}") # Still log execution

        try:
            result = await func(*args, **kwargs)
            exec_time = time.time() - start_time
            res_prev, res_detail = _format_result_for_logging(result)
            logger.info(f"✅ TOOL SUCCEEDED: {func_name} ({exec_time:.2f}s)")
            # Log result preview at INFO, details at DEBUG
            logger.debug(f"   RESULT DETAIL: {res_detail}")
            logger.info(f"   RESULT PREVIEW: {res_prev}")
            return result
        except Exception as e:
            exec_time = time.time() - start_time
            # Log tool failures as ERROR
            logger.error(f"❌ TOOL FAILED: {func_name} ({exec_time:.2f}s)")
            logger.error(f"   ERROR: {type(e).__name__} - {e}")
            logger.debug(traceback.format_exc()) # Keep traceback at DEBUG
            raise # Re-raise the exception after logging

    return wrapper


def _format_result_for_logging(result: Any) -> tuple[str, Any]:
    """Helper to format tool results for logging."""
    res_prev, res_detail = repr(result), result
    try:
        if BaseModel and isinstance(result, BaseModel): # Check if BaseModel exists
            json_prev = result.model_dump_json(exclude_defaults=True, exclude_none=True, indent=None)
            res_detail = result.model_dump(exclude_defaults=True, exclude_none=True) # Keep full detail for debug
            res_prev = f"{type(result).__name__}[{len(json_prev)} chars]" if len(json_prev) > 300 else json_prev
        elif isinstance(result, str) and len(result) > 200:
            res_prev = f"{result[:200]}..."
        elif isinstance(result, list) and len(result) > 10:
            res_prev = f"List[{len(result)} items]"
        elif isinstance(result, dict) and len(result) > 10:
            res_prev = f"Dict[{len(result)} keys]"
    except Exception as fmt_err:
        logger.warning(f"Result format error: {fmt_err}")
        res_prev = f"{type(result).__name__}(FormatErr)"

    # Ensure detail is serializable or representable for debug logs
    if not isinstance(res_detail, (str, int, float, bool, list, dict, type(None))):
        res_detail = repr(res_detail) # Use repr for non-standard types

    return str(res_prev), res_detail 