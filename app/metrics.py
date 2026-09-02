from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("llm_gateway_requests_total", "Total gateway requests", ["model", "status"])
ERRORS = Counter("llm_gateway_errors_total", "Total gateway errors", ["model", "error_type"])
LATENCY = Histogram("llm_gateway_request_latency_seconds", "Gateway request latency", ["model"], buckets=(0.05,0.1,0.25,0.5,1,2,5,10,30,60,120))
TOKENS = Counter("llm_gateway_tokens_total", "Tokens consumed", ["model", "type"])
COST = Counter("llm_gateway_estimated_cost_usd_total", "Estimated inference cost", ["model"])
QUALITY = Histogram("llm_gateway_quality_score", "Quality scores (0-1)", ["model"], buckets=(0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0))
PROVIDER_AVAILABILITY = Gauge("llm_gateway_provider_availability", "Whether OpenRouter model/provider discovery is available", ["source"])
ACTIVE_MODELS = Gauge("llm_gateway_discovered_models", "Number of models discovered from OpenRouter")
