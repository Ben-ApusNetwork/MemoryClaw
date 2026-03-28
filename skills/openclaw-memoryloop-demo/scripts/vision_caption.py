#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Tuple
from urllib import error, request


SYSTEM_PROMPT = (
    "You are describing an uploaded image for a memory sidecar. "
    "Return one or two short sentences capturing durable signals only. "
    "If the image is a moodboard, scene, or design reference, focus on aesthetic cues such as restrained, editorial, minimal, flashy, calm, dense, black-and-gold, muted palette, or gimmicky. "
    "If the image contains handwritten notes, screenshots, slides, or whiteboards, summarize stable strategic or operational signals such as growth priorities, bottlenecks, risk posture, long-term vision, urgency, or explicit rules. "
    "Do not infer identity, demographics, private facts, or emotions beyond obvious visual tone. "
    "Return plain text only."
)


def read_image_as_data_url(image_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/jpeg"
    payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


def build_image_url(args: argparse.Namespace) -> str:
    if args.image_url:
        return args.image_url
    if args.image_path:
        return read_image_as_data_url(Path(args.image_path))
    raise ValueError("either --image-path or --image-url is required")


def load_openclaw_provider() -> Tuple[str, str, str]:
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return "", "", ""

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "", "", ""

    provider_name = os.getenv("OPENCLAW_VISION_PROVIDER", "").strip()
    providers = config.get("models", {}).get("providers", {})
    if not provider_name:
        for name, provider in providers.items():
            if not isinstance(provider, dict):
                continue
            models = provider.get("models", [])
            if not isinstance(models, list):
                continue
            for model in models:
                if isinstance(model, dict) and any(token in model.get("input", []) for token in ["image", "vision"]):
                    provider_name = str(name)
                    break
            if provider_name:
                break

    provider = providers.get(provider_name) if provider_name else None
    if not isinstance(provider, dict):
        return "", "", ""

    api_key = str(provider.get("apiKey", "")).strip()
    base_url = str(provider.get("baseUrl", "")).strip()
    model_name = os.getenv("OPENCLAW_VISION_MODEL", "").strip()
    if not model_name:
        models = provider.get("models", [])
        if isinstance(models, list):
            for model in models:
                if not isinstance(model, dict):
                    continue
                inputs = [str(item).lower() for item in model.get("input", [])]
                if any(token in inputs for token in ["image", "vision"]):
                    model_name = str(model.get("id", "")).strip()
                    break

    return api_key, base_url, model_name


def parse_content_text(payload: dict) -> str:
    choices = payload.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        pieces = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if text:
                pieces.append(str(text).strip())
        return " ".join(part for part in pieces if part).strip()
    return ""


def describe_image(image_url: str, hint_text: str, model: str, api_key: str, base_url: str, timeout: float) -> str:
    prompt = (
        "Describe the image for an audited memory system. "
        "Mention only durable signals that could inform long-term or held-for-review memory. "
        "If the image is text-heavy, extract the stable strategic notes rather than surface-level layout details. "
        "Keep it concise."
    )
    if hint_text.strip():
        prompt += f" User caption or hint: {hint_text.strip()}"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 120,
    }
    endpoint = base_url.rstrip("/") + "/chat/completions"
    req = request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_content_text(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a compact image caption for the MemoryLoop sidecar.")
    parser.add_argument("--image-path", default="", help="Local path to the image")
    parser.add_argument("--image-url", default="", help="Remote URL to the image")
    parser.add_argument("--hint-text", default="", help="Optional user caption or context")
    parser.add_argument("--model", default=os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser


def resolve_api_settings(args: argparse.Namespace) -> Tuple[str, str, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base_url = args.base_url
    model = args.model
    if api_key:
        return api_key, base_url, model

    provider_key, provider_base_url, provider_model = load_openclaw_provider()
    if provider_key and provider_base_url and provider_model:
        return provider_key, provider_base_url.rstrip("/") + "/chat/completions", provider_model

    return "", "", ""


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    api_key, endpoint_or_base, model = resolve_api_settings(args)
    if not api_key:
        return 0

    if not args.image_path and not args.image_url:
        parser.error("either --image-path or --image-url is required")

    try:
        image_url = build_image_url(args)
        caption = describe_image(
            image_url=image_url,
            hint_text=args.hint_text,
            model=model,
            api_key=api_key,
            base_url=endpoint_or_base.removesuffix("/chat/completions"),
            timeout=args.timeout,
        )
    except (OSError, ValueError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
        print(f"vision_error:{exc}", file=sys.stderr)
        return 0

    if caption:
        print(caption.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
