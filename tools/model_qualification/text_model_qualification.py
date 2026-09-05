from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    endpoint: str
    api_key_env: str
    model_env: str
    default_model: str


PROVIDERS: dict[str, ProviderSpec] = {
    "gemini": ProviderSpec(
        name="gemini",
        endpoint="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        api_key_env="GEMINI_API_KEY",
        model_env="GEMINI_MODEL",
        default_model="gemini-3.8-flash",
    ),
    "groq": ProviderSpec(
        name="groq",
        endpoint="https://api.groq.com/openai/v1/chat/completions",
        api_key_env="GROQ_API_KEY",
        model_env="GROQ_MODEL",
        default_model="openai/gpt-oss-120b",
    ),
    "openrouter": ProviderSpec(
        name="openrouter",
        endpoint="https://openrouter.ai/api/v1/chat/completions",
        api_key_env="OPENROUTER_API_KEY",
        model_env="OPENROUTER_MODEL",
        default_model="openrouter/free",
    ),
    "pollinations": ProviderSpec(
        name="pollinations",
        endpoint="https://gen.pollinations.ai/v1/chat/completions",
        api_key_env="POLLINATIONS_API_KEY",
        model_env="POLLINATIONS_TEXT_MODEL",
        default_model="openai",
    ),
}

SYSTEM_PROMPT = """You are SoloForge's product-content qualification model.
Return Thai commercial copy grounded only in the supplied product JSON.
Do not invent product properties, discounts, certifications, performance claims, or guarantees.
Return ONLY one JSON object with this exact shape:
{
  "selling_angles": [
    {
      "name": "Thai angle name",
      "rationale": "Thai explanation",
      "audience": "Thai audience",
      "evidence": ["exact fact copied verbatim from the product JSON"]
    }
  ],
  "hook": "Thai hook",
  "caption": "Thai caption",
  "cta": "Thai CTA",
  "hashtags": ["#tag"],
  "claims_used": ["exact fact copied verbatim from the product JSON"]
}
Requirements:
- selling_angles must contain exactly 3 distinct angles.
- evidence and claims_used must contain only exact strings visible in the product JSON.
- Prefer no claim over an unsupported claim.
- Write hook, caption, CTA, angle names, rationales and audiences primarily in Thai.
"""


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _source_text(product: dict[str, Any]) -> str:
    return _normalize_text(json.dumps(product, ensure_ascii=False, sort_keys=True))


def build_user_prompt(product: dict[str, Any]) -> str:
    return (
        "Evaluate this product for a Product-to-Post workflow. "
        "Return 3 evidence-grounded selling angles and one Thai post package.\n\n"
        f"PRODUCT_JSON:\n{json.dumps(product, ensure_ascii=False, sort_keys=True, indent=2)}"
    )


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("model response did not contain a JSON object")
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError("model response contained invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("model response JSON must be an object")
    return parsed


def validate_output(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    angles = output.get("selling_angles")
    if not isinstance(angles, list) or len(angles) != 3:
        errors.append("selling_angles must contain exactly 3 items")
    else:
        for index, angle in enumerate(angles):
            if not isinstance(angle, dict):
                errors.append(f"selling_angles[{index}] must be an object")
                continue
            for key in ("name", "rationale", "audience"):
                if not isinstance(angle.get(key), str) or not angle[key].strip():
                    errors.append(f"selling_angles[{index}].{key} must be a non-empty string")
            evidence = angle.get("evidence")
            if not isinstance(evidence, list) or not all(
                isinstance(item, str) and item.strip() for item in evidence
            ):
                errors.append(f"selling_angles[{index}].evidence must be a list of strings")

    for key in ("hook", "caption", "cta"):
        if not isinstance(output.get(key), str) or not output[key].strip():
            errors.append(f"{key} must be a non-empty string")

    hashtags = output.get("hashtags")
    if not isinstance(hashtags, list) or not all(
        isinstance(item, str) and item.strip() for item in hashtags
    ):
        errors.append("hashtags must be a list of strings")

    claims = output.get("claims_used")
    if not isinstance(claims, list) or not all(
        isinstance(item, str) and item.strip() for item in claims
    ):
        errors.append("claims_used must be a list of strings")

    return errors


def _thai_ratio(text: str) -> float:
    thai = sum(1 for char in text if "\u0e00" <= char <= "\u0e7f")
    alpha = sum(1 for char in text if char.isalpha())
    return thai / max(alpha, 1)


def _collect_narrative_text(output: dict[str, Any]) -> str:
    parts = [
        str(output.get("hook", "")),
        str(output.get("caption", "")),
        str(output.get("cta", "")),
    ]
    for angle in output.get("selling_angles", []):
        if isinstance(angle, dict):
            parts.extend(
                str(angle.get(key, "")) for key in ("name", "rationale", "audience")
            )
    return "\n".join(parts)


def _evidence_items(output: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for angle in output.get("selling_angles", []):
        if isinstance(angle, dict) and isinstance(angle.get("evidence"), list):
            items.extend(item for item in angle["evidence"] if isinstance(item, str))
    claims = output.get("claims_used")
    if isinstance(claims, list):
        items.extend(item for item in claims if isinstance(item, str))
    return items


def score_output(product: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    validation_errors = validate_output(output)
    structure_score = 25 if not validation_errors else max(0, 25 - 5 * len(validation_errors))

    narrative = _collect_narrative_text(output)
    thai_ratio = _thai_ratio(narrative)
    thai_score = 25 if thai_ratio >= 0.45 else round(25 * min(thai_ratio / 0.45, 1), 1)

    evidence = _evidence_items(output)
    source = _source_text(product)
    if evidence:
        grounded = sum(1 for item in evidence if _normalize_text(item) in source)
        evidence_ratio = grounded / len(evidence)
        evidence_score = round(25 * evidence_ratio, 1)
    else:
        evidence_ratio = 0.0
        evidence_score = 0.0

    angles = output.get("selling_angles")
    complete = (
        isinstance(angles, list)
        and len(angles) == 3
        and all(str(output.get(key, "")).strip() for key in ("hook", "caption", "cta"))
        and isinstance(output.get("hashtags"), list)
        and len(output["hashtags"]) > 0
    )
    completeness_score = 25 if complete else 10

    total = round(
        float(structure_score)
        + float(thai_score)
        + float(evidence_score)
        + float(completeness_score),
        1,
    )

    return {
        "total": total,
        "structure": structure_score,
        "thai": thai_score,
        "evidence_grounding": evidence_score,
        "completeness": completeness_score,
        "thai_ratio": round(thai_ratio, 3),
        "evidence_ratio": round(evidence_ratio, 3),
        "validation_errors": validation_errors,
    }


def _message_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("provider response is missing choices[0].message.content") from exc

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        if text_parts:
            return "\n".join(text_parts)
    raise ValueError("provider returned unsupported message content")


def build_request_payload(model: str, product: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(product)},
        ],
        "temperature": 0.2,
        "max_tokens": 1400,
    }


def _pricing_for(
    pricing: dict[str, Any], provider: str, model: str
) -> dict[str, float] | None:
    value = pricing.get(f"{provider}/{model}") or pricing.get(provider)
    if not isinstance(value, dict):
        return None
    try:
        return {
            "input_per_million": float(value["input_per_million"]),
            "output_per_million": float(value["output_per_million"]),
        }
    except (KeyError, TypeError, ValueError):
        return None


def estimate_cost_usd(
    usage: dict[str, Any], pricing: dict[str, float] | None
) -> float | None:
    if pricing is None:
        return None
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    return round(
        prompt_tokens / 1_000_000 * pricing["input_per_million"]
        + completion_tokens / 1_000_000 * pricing["output_per_million"],
        8,
    )


def run_provider(
    spec: ProviderSpec,
    product: dict[str, Any],
    *,
    timeout_seconds: int,
    pricing: dict[str, Any],
    max_cost_usd: float | None,
) -> dict[str, Any]:
    api_key = os.getenv(spec.api_key_env, "").strip()
    model = os.getenv(spec.model_env, spec.default_model).strip() or spec.default_model

    if not api_key:
        return {
            "provider": spec.name,
            "model": model,
            "stage": "UNTESTED",
            "status": "SKIPPED",
            "reason": f"missing {spec.api_key_env}",
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if spec.name == "openrouter":
        headers["X-OpenRouter-Title"] = "SoloForge Text Model Qualification"
        referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
        if referer:
            headers["HTTP-Referer"] = referer

    request = urllib.request.Request(
        spec.endpoint,
        data=json.dumps(build_request_payload(model, product)).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read()
            http_status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:1200]
        return {
            "provider": spec.name,
            "model": model,
            "stage": "UNTESTED",
            "status": "ERROR",
            "http_status": exc.code,
            "error": body or exc.reason,
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "provider": spec.name,
            "model": model,
            "stage": "UNTESTED",
            "status": "ERROR",
            "error": str(exc),
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    try:
        response_payload = json.loads(raw_body.decode("utf-8"))
        content = _message_content(response_payload)
        output = extract_json_object(content)
        scores = score_output(product, output)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "provider": spec.name,
            "model": model,
            "stage": "UNTESTED",
            "status": "ERROR",
            "http_status": http_status,
            "latency_ms": latency_ms,
            "error": str(exc),
        }

    usage = response_payload.get("usage") if isinstance(response_payload.get("usage"), dict) else {}
    model_pricing = _pricing_for(pricing, spec.name, model)
    estimated_cost = estimate_cost_usd(usage, model_pricing)

    cost_status = "UNASSESSED"
    if estimated_cost is not None and max_cost_usd is not None:
        cost_status = "PASS" if estimated_cost <= max_cost_usd else "FAIL"

    stage = "TECHNICALLY_WORKS"
    if not scores["validation_errors"] and scores["total"] >= 80:
        stage = "QUALITY_PASS"
    if stage == "QUALITY_PASS" and cost_status == "PASS":
        stage = "COST_PASS"

    return {
        "provider": spec.name,
        "model": model,
        "stage": stage,
        "status": "OK",
        "http_status": http_status,
        "latency_ms": latency_ms,
        "usage": usage,
        "estimated_cost_usd": estimated_cost,
        "cost_status": cost_status,
        "scores": scores,
        "output": output,
    }


def load_pricing() -> dict[str, Any]:
    raw = os.getenv("TEXT_QUALIFICATION_PRICING_JSON", "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("TEXT_QUALIFICATION_PRICING_JSON must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("TEXT_QUALIFICATION_PRICING_JSON must be a JSON object")
    return value


def load_product(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("product JSON must be an object")
    if not data:
        raise ValueError("product JSON must not be empty")
    return data


def qualify(
    product: dict[str, Any],
    providers: list[str],
    *,
    timeout_seconds: int,
    max_cost_usd: float | None,
) -> dict[str, Any]:
    pricing = load_pricing()
    results: list[dict[str, Any]] = []
    for provider_name in providers:
        spec = PROVIDERS.get(provider_name)
        if spec is None:
            results.append(
                {
                    "provider": provider_name,
                    "stage": "UNTESTED",
                    "status": "ERROR",
                    "error": "unknown provider",
                }
            )
            continue
        results.append(
            run_provider(
                spec,
                product,
                timeout_seconds=timeout_seconds,
                pricing=pricing,
                max_cost_usd=max_cost_usd,
            )
        )

    successful = [item for item in results if item.get("status") == "OK"]
    ranking = sorted(
        successful,
        key=lambda item: (
            float(item.get("scores", {}).get("total", 0)),
            -float(item.get("latency_ms", 0)),
        ),
        reverse=True,
    )

    return {
        "schema_version": 1,
        "qualification_policy": {
            "quality_pass_min_score": 80,
            "production_approval": "MANUAL_OWNER_GATE",
            "cost_rule": (
                f"estimated_cost_usd <= {max_cost_usd}"
                if max_cost_usd is not None
                else "UNASSESSED"
            ),
        },
        "results": results,
        "ranking": [
            {
                "provider": item["provider"],
                "model": item["model"],
                "stage": item["stage"],
                "score": item["scores"]["total"],
                "latency_ms": item["latency_ms"],
                "estimated_cost_usd": item["estimated_cost_usd"],
            }
            for item in ranking
        ],
    }


def parse_provider_names(raw: str) -> list[str]:
    values = [value.strip().lower() for value in raw.split(",") if value.strip()]
    if not values:
        raise ValueError("at least one provider is required")
    return values


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare SoloForge text providers using one evidence-grounded Thai Product-to-Post contract."
    )
    parser.add_argument("--product-json", help="Path to one real product JSON file.")
    parser.add_argument(
        "--providers",
        default="gemini,groq,openrouter,pollinations",
        help="Comma-separated provider names.",
    )
    parser.add_argument("--output", help="Optional report JSON path.")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="Optional maximum acceptable estimated cost per qualification request.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.product_json:
        print("--product-json is required", file=sys.stderr)
        return 2

    try:
        product = load_product(args.product_json)
        providers = parse_provider_names(args.providers)
        report = qualify(
            product,
            providers,
            timeout_seconds=args.timeout_seconds,
            max_cost_usd=args.max_cost_usd,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"qualification setup failed: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
