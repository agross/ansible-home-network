"""Hermes MiniMax H3 Image backend, porting the H3 route from OpenClaw PR #196627.

H3 is NOT supported by the old /v1/image_generation endpoint. Requests go to
/v1/images/generations or /v1/images/edits, and results are data[].url.
No automatic retries: each image request is billable and non-idempotent.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO, ImageGenProvider, error_response,
    normalize_reference_images, resolve_aspect_ratio, save_b64_image,
    save_url_image, success_response,
)

logger = logging.getLogger(__name__)
_MODELS = ("MiniMax-H3-Image", "MiniMax-H3-Image-Highspeed")
_ASPECTS = {"landscape": "16:9", "square": "1:1", "portrait": "9:16"}


def _config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        cfg = load_config().get("image_gen", {})
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _source(value: str) -> str:
    if value.startswith(("https://", "data:image/")):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        raise ValueError(f"Reference image not found: {value}")
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Reference image exceeds 10 MiB inline limit; use a URL")
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"):
        raise ValueError(f"Unsupported reference image format: {mime}")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


class MiniMaxH3Provider(ImageGenProvider):
    @property
    def name(self) -> str:
        return "minimax-h3"

    @property
    def display_name(self) -> str:
        return "MiniMax H3 Image"

    def is_available(self) -> bool:
        return bool(os.environ.get("MINIMAX_API_KEY"))

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"id": model, "display": model, "speed": "~15–60s",
             "strengths": "Text-to-image and multi-image editing", "price": "MiniMax API"}
            for model in _MODELS
        ]

    def default_model(self) -> str:
        return _MODELS[0]

    def capabilities(self) -> dict[str, Any]:
        return {"modalities": ["text", "image"], "max_reference_images": 16,
                "creative_controls": ["resolution"]}

    def generate(
        self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        *, image_url: str | None = None,
        reference_image_urls: list[str] | None = None, **kwargs: Any,
    ) -> dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        cfg = _config()
        section = cfg.get("minimax_h3") if isinstance(cfg.get("minimax_h3"), dict) else {}
        model = kwargs.get("model") or section.get("model") or cfg.get("model") or self.default_model()
        if model not in _MODELS:
            return error_response(error=f"Unsupported H3 model: {model}", error_type="invalid_input",
                                  provider=self.name, model=str(model), prompt=prompt, aspect_ratio=aspect)
        if not prompt or len(prompt) > 32000:
            return error_response(error="Prompt must contain 1–32000 characters", error_type="invalid_input",
                                  provider=self.name, model=model, prompt=prompt, aspect_ratio=aspect)
        key = os.environ.get("MINIMAX_API_KEY")
        if not key:
            return error_response(error="MINIMAX_API_KEY is not set", error_type="auth_required",
                                  provider=self.name, model=model, prompt=prompt, aspect_ratio=aspect)
        refs = ([image_url] if image_url else []) + (normalize_reference_images(reference_image_urls) or [])
        if len(refs) > 16:
            return error_response(error="At most 16 reference images are supported", error_type="invalid_input",
                                  provider=self.name, model=model, prompt=prompt, aspect_ratio=aspect)
        try:
            images = [{"image_url": _source(item)} for item in refs]
        except ValueError as exc:
            return error_response(error=str(exc), error_type="invalid_input", provider=self.name,
                                  model=model, prompt=prompt, aspect_ratio=aspect)
        area = kwargs.get("resolution") or section.get("area") or "1K"
        if area not in ("1K", "2K", "4K"):
            return error_response(error=f"Unsupported H3 resolution: {area}", error_type="invalid_input",
                                  provider=self.name, model=model, prompt=prompt, aspect_ratio=aspect)
        payload: dict[str, Any] = {
            "model": model, "prompt": prompt, "aspect_ratio": _ASPECTS[aspect],
            "area": area, "n": 1, "response_format": "url", "stream": False,
        }
        # Match the H3 API default (prompt enhancement on); allow an explicit
        # opt-out via image_gen.minimax_h3.disable_prompt_enhanced.
        if images:
            payload["images"] = images
        elif "disable_prompt_enhanced" in section:
            payload["disable_prompt_enhanced"] = bool(section["disable_prompt_enhanced"])
        base = section.get("api") or (cfg.get("minimax") or {}).get("api") or "https://api.minimax.io"
        endpoint = "edits" if images else "generations"
        try:
            import requests
            response = requests.post(
                f"{str(base).rstrip('/')}/v1/images/{endpoint}",
                headers={"Authorization": f"Bearer {key}"}, json=payload,
                timeout=(15, 610),
            )
            # Do not log or echo request headers, credentials, or full response.
            result = response.json()
            if response.status_code != 200:
                err = result.get("error", {})
                message = err.get("message", "request failed") if isinstance(err, dict) else "request failed"
                raise ValueError(f"MiniMax HTTP {response.status_code}: {message}")
            items = result.get("data") or []
            item = items[0] if items else {}
            if not isinstance(item, dict) or item.get("error"):
                detail = item.get("error") if isinstance(item, dict) else None
                raise ValueError(f"MiniMax produced no image: {detail or 'empty data'}")
            ref = item.get("url")
            if ref:
                image = str(save_url_image(ref, prefix="minimax_h3", timeout=90, max_bytes=35 * 1024 * 1024))
            elif item.get("b64_json"):
                ext = {"jpeg": "jpg", "png": "png", "webp": "webp"}.get(result.get("output_format"), "jpg")
                image = str(save_b64_image(item["b64_json"], prefix="minimax_h3", extension=ext))
            else:
                raise ValueError("MiniMax response contains neither URL nor image bytes")
        except Exception as exc:
            logger.warning("MiniMax H3 request or image download failed: %s", exc)
            return error_response(error=str(exc), error_type="api_error", provider=self.name,
                                  model=model, prompt=prompt, aspect_ratio=aspect)
        return success_response(
            image=image, model=model, prompt=prompt, aspect_ratio=aspect,
            provider=self.name, modality="image" if images else "text",
            extra={"request_id": result.get("request_id"), "revised_prompt": item.get("revised_prompt"),
                   "size": item.get("size"), "area": area},
        )


def register(ctx: Any) -> None:
    ctx.register_image_gen_provider(MiniMaxH3Provider())
