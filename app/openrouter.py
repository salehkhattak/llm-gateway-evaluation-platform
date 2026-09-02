import time
from functools import lru_cache
import httpx
from .config import get_settings

class OpenRouterClient:
    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.settings.site_url,
            "X-Title": self.settings.site_name,
        }
        self._model_cache: tuple[float, dict[str, dict]] = (0, {})

    def chat(self, payload: dict) -> tuple[dict, float]:
        start = time.perf_counter()
        with httpx.Client(timeout=self.settings.http_timeout_seconds) as client:
            response = client.post(f"{self.settings.openrouter_base_url}/chat/completions", headers=self.headers, json=payload)
            latency = time.perf_counter() - start
            response.raise_for_status()
            return response.json(), latency

    def models(self) -> list[dict]:
        now = time.time()
        if now - self._model_cache[0] < self.settings.model_cache_seconds and self._model_cache[1]:
            return list(self._model_cache[1].values())
        with httpx.Client(timeout=20) as client:
            response = client.get(f"{self.settings.openrouter_base_url}/models", headers=self.headers)
            response.raise_for_status()
            data = response.json().get("data", [])
        cache = {m.get("id"): m for m in data if m.get("id")}
        self._model_cache = (now, cache)
        return data

    def pricing_map(self) -> dict[str, tuple[float, float]]:
        prices = {}
        for model in self.models():
            pricing = model.get("pricing") or {}
            try:
                prices[model["id"]] = (float(pricing.get("prompt", 0)), float(pricing.get("completion", 0)))
            except (TypeError, ValueError):
                prices[model["id"]] = (0.0, 0.0)
        return prices
