"""
In-memory session cost tracker.
Resets to zero each time the API restarts.
Gemini 2.5 Flash pricing on OpenRouter (update if prices change).
"""

# Gemini 2.5 Flash via OpenRouter — per 1M tokens
INPUT_PRICE_PER_M  = 0.075   # $0.075 / 1M input tokens
OUTPUT_PRICE_PER_M = 0.30    # $0.30  / 1M output tokens

_session = {
    "cost_usd": 0.0,
    "input_tokens": 0,
    "output_tokens": 0,
    "llm_calls": 0,
    "applications": 0,
}


def record_call(input_tokens: int, output_tokens: int) -> float:
    """Record one LLM call. Returns its cost in USD."""
    cost = (
        input_tokens  * INPUT_PRICE_PER_M +
        output_tokens * OUTPUT_PRICE_PER_M
    ) / 1_000_000
    _session["cost_usd"]       += cost
    _session["input_tokens"]   += input_tokens
    _session["output_tokens"]  += output_tokens
    _session["llm_calls"]      += 1
    return cost


def record_application() -> None:
    _session["applications"] += 1


def snapshot_cost() -> float:
    return _session["cost_usd"]


def get_stats() -> dict:
    return {
        "session_cost_usd":   round(_session["cost_usd"], 6),
        "input_tokens":       _session["input_tokens"],
        "output_tokens":      _session["output_tokens"],
        "llm_calls":          _session["llm_calls"],
        "applications":       _session["applications"],
    }
