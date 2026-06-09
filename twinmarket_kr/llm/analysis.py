from __future__ import annotations

import json
from typing import Any

from twinmarket_kr.llm.belief import load_prompt
from twinmarket_kr.llm.client import OpenRouterClient


NEWS_INTERPRETATION_KEYS = (
    "selected_news",
    "news_sentiment",
    "short_term_impact",
    "long_term_impact",
    "persona_interpretation",
    "confidence",
    "reason",
)

MARKET_ANALYSIS_KEYS = (
    "market_view",
    "valuation_view",
    "technical_view",
    "news_view",
    "portfolio_view",
    "key_risks",
    "opportunity",
    "caution",
    "confidence",
)


def parse_json_object(content: str, required_keys: tuple[str, ...], label: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    data = json.loads(text)
    missing = [key for key in required_keys if key not in data]
    if missing:
        raise ValueError(f"{label} JSON missing keys: {missing}")
    return data


async def interpret_news(
    agent: dict[str, Any],
    news_context: dict[str, Any],
    *,
    client: OpenRouterClient | None = None,
) -> dict[str, Any]:
    client = client or OpenRouterClient()
    prompt = load_prompt("news_interpretation.txt").format(
        persona_prompt=agent["persona_prompt"],
        news_context=json.dumps(news_context, ensure_ascii=False, indent=2),
    )
    response = await client.chat(
        [{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return parse_json_object(
        response.choices[0].message.content or "{}",
        NEWS_INTERPRETATION_KEYS,
        "news interpretation",
    )


async def analyze_market(
    agent: dict[str, Any],
    *,
    today_belief: dict[str, Any],
    market_features: dict[str, Any],
    portfolio_summary: str,
    news_interpretation: dict[str, Any],
    client: OpenRouterClient | None = None,
) -> dict[str, Any]:
    client = client or OpenRouterClient()
    prompt = load_prompt("market_analysis.txt").format(
        persona_prompt=agent["persona_prompt"],
        today_belief=json.dumps(today_belief, ensure_ascii=False, indent=2),
        market_features=json.dumps(market_features, ensure_ascii=False, indent=2),
        portfolio_summary=portfolio_summary,
        news_interpretation=json.dumps(news_interpretation, ensure_ascii=False, indent=2),
    )
    response = await client.chat(
        [{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return parse_json_object(
        response.choices[0].message.content or "{}",
        MARKET_ANALYSIS_KEYS,
        "market analysis",
    )
