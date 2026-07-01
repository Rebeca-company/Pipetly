"""
Telemetry and Cost Tracking Utilities.
Calculates token usage and retrieves dynamic pricing from OpenRouter if configured.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import httpx

from config import get_settings
from utils.intermediate_io import TEST_LLM_TOKEN_USAGE_FILE, save_json

logger = logging.getLogger(__name__)


async def fetch_model_pricing(model_id: str) -> Tuple[float, float]:
    """
    Fetch the per-million-token input and output cost for a specific model
    from OpenRouter API. If it fails or is disabled, returns fallback settings.

    Returns:
        (input_usd_per_1m, output_usd_per_1m)
    """
    _s = get_settings()
    
    # Fallback to config values
    fallback_input = _s.llm_cost_input_usd_per_1m
    fallback_output = _s.llm_cost_output_usd_per_1m

    if not _s.fetch_openrouter_pricing:
        logger.debug("OpenRouter dynamic pricing disabled. Using config values.")
        return fallback_input, fallback_output

    url = "https://openrouter.ai/api/v1/models"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            
            for model_info in data:
                if model_info.get("id") == model_id:
                    pricing = model_info.get("pricing", {})
                    # OpenRouter returns pricing per token as string (e.g. "0.000000075")
                    prompt_price = float(pricing.get("prompt", "0"))
                    completion_price = float(pricing.get("completion", "0"))
                    
                    # Convert per-token to per-million-tokens
                    input_1m = prompt_price * 1_000_000
                    output_1m = completion_price * 1_000_000
                    
                    logger.debug(
                        "Fetched pricing for %s: $%.4f/1M input, $%.4f/1M output", 
                        model_id, input_1m, output_1m
                    )
                    return input_1m, output_1m
                    
            logger.warning("Model %s not found in OpenRouter API. Using fallback.", model_id)
            
    except Exception as exc:
        logger.warning("Failed to fetch dynamic pricing from OpenRouter: %s", exc)

    return fallback_input, fallback_output


async def calculate_pipeline_costs(
    raw_events: List[Dict[str, Any]], 
    model_id: str
) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Given a list of raw token events and the model used, computes the real USD cost
    and returns the enriched events along with a total summary.
    
    Returns:
        (enriched_token_events, total_summary_dict)
    """
    input_usd_per_1m, output_usd_per_1m = await fetch_model_pricing(model_id)

    token_events = []
    for event in raw_events:
        input_tokens = int(event.get("input_tokens", 0))
        output_tokens = int(event.get("output_tokens", 0))
        input_cost_usd = (input_tokens / 1_000_000) * input_usd_per_1m
        output_cost_usd = (output_tokens / 1_000_000) * output_usd_per_1m
        token_events.append(
            {
                **event,
                "input_cost_usd": round(input_cost_usd, 8),
                "output_cost_usd": round(output_cost_usd, 8),
                "total_cost_usd": round(input_cost_usd + output_cost_usd, 8),
            }
        )

    total_input_tokens = sum(int(item.get("input_tokens", 0)) for item in token_events)
    total_output_tokens = sum(int(item.get("output_tokens", 0)) for item in token_events)
    total_input_cost_usd = (total_input_tokens / 1_000_000) * input_usd_per_1m
    total_output_cost_usd = (total_output_tokens / 1_000_000) * output_usd_per_1m

    total_summary = {
        "model": model_id,
        "pricing_usd_per_1m": {
            "input": input_usd_per_1m,
            "output": output_usd_per_1m,
        },
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "total_input_cost_usd": round(total_input_cost_usd, 8),
        "total_output_cost_usd": round(total_output_cost_usd, 8),
        "total_pipeline_cost_usd": round(total_input_cost_usd + total_output_cost_usd, 8),
    }

    return token_events, total_summary


async def log_standalone_telemetry(raw_events: List[Dict[str, Any]], model_id: str, component_name: str) -> None:
    """
    Convenience method for processors run in standalone mode.
    Calculates costs and logs the summary.
    """
    if not raw_events:
        logger.info("No LLM token events recorded.")
        return

    events_with_component = [{"component": component_name, **ev} for ev in raw_events]
    token_events, total_summary = await calculate_pipeline_costs(events_with_component, model_id)
    
    logger.info("Standalone Execution LLM Telemetry:")
    logger.info("  Input  : %d tokens", total_summary["total_input_tokens"])
    logger.info("  Output : %d tokens", total_summary["total_output_tokens"])
    logger.info(
        "  Cost   : $%.6f (input) + $%.6f (output) = $%.6f total", 
        total_summary["total_input_cost_usd"], 
        total_summary["total_output_cost_usd"], 
        total_summary["total_pipeline_cost_usd"]
    )
    
    out_file = f"telemetry/{component_name}.json"
    save_json(
        {
            "token_events": token_events,
            "total_summary": total_summary,
        },
        out_file,
    )
    logger.info("Saved standalone telemetry to intermediate_outputs/%s", out_file)
