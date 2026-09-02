import uuid
from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .config import get_settings
from .db import get_db, init_db, RequestLog
from .evaluator import Evaluator
from .metrics import REQUESTS, ERRORS, LATENCY, TOKENS, COST, QUALITY, PROVIDER_AVAILABILITY, ACTIVE_MODELS
from .openrouter import OpenRouterClient
from .schemas import ChatRequest, ChatResponse, CompareRequest, CompareResponse, CompareResult

settings = get_settings()
client = OpenRouterClient()
evaluator = Evaluator(client)
app = FastAPI(title=settings.app_name, version="1.0.0")

@app.on_event("startup")
def startup():
    init_db()
    try:
        models = client.models()
        ACTIVE_MODELS.set(len(models))
        PROVIDER_AVAILABILITY.labels(source="openrouter_models_api").set(1)
    except Exception:
        PROVIDER_AVAILABILITY.labels(source="openrouter_models_api").set(0)

@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}

@app.get("/health/providers")
def provider_health():
    try:
        models = client.models()
        providers = set()
        for model in models:
            for endpoint in model.get("endpoints", []) or []:
                if endpoint.get("provider_name"):
                    providers.add(endpoint["provider_name"])
        PROVIDER_AVAILABILITY.labels(source="openrouter_provider_discovery").set(1)
        return {"available": True, "model_count": len(models), "provider_count": len(providers), "providers": sorted(providers)}
    except Exception as exc:
        PROVIDER_AVAILABILITY.labels(source="openrouter_provider_discovery").set(0)
        return {"available": False, "error": str(exc)}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/v1/chat/completions", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    request_id = str(uuid.uuid4())
    model = request.model or settings.default_model
    prompt_text = "\n".join(str(m.content) for m in request.messages if m.role == "user")
    payload = {"model": model, "messages": [m.model_dump() for m in request.messages], "usage": {"include": True}}
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    try:
        data, elapsed = client.chat(payload)
        usage = data.get("usage") or {}
        inp = int(usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0)
        out = int(usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0)
        total = int(usage.get("total_tokens", inp + out))
        model_used = data.get("model") or model
        prices = client.pricing_map()
        prompt_price, completion_price = prices.get(model_used, prices.get(model, (0.0, 0.0)))
        reported_cost = usage.get("cost")
        cost = float(reported_cost) if reported_cost is not None else (inp * prompt_price + out * completion_price)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        quality = evaluator.judge(prompt_text, content) if request.evaluate else None
        log = RequestLog(request_id=request_id, model_requested=model, model_used=model_used, provider="OpenRouter", prompt=prompt_text, response=content, latency_ms=elapsed*1000, input_tokens=inp, output_tokens=out, total_tokens=total, estimated_cost_usd=cost, quality_score=quality, success=True, status_code=200)
        db.add(log); db.commit()
        REQUESTS.labels(model=model_used, status="success").inc(); LATENCY.labels(model=model_used).observe(elapsed); TOKENS.labels(model=model_used, type="input").inc(inp); TOKENS.labels(model=model_used, type="output").inc(out); COST.labels(model=model_used).inc(cost)
        if quality is not None: QUALITY.labels(model=model_used).observe(quality)
        return ChatResponse(request_id=request_id, model=model_used, content=content, latency_ms=round(elapsed*1000, 2), usage={"input_tokens": inp, "output_tokens": out, "total_tokens": total}, estimated_cost_usd=round(cost, 8), quality_score=quality)
    except Exception as exc:
        log = RequestLog(request_id=request_id, model_requested=model, prompt=prompt_text, latency_ms=0, success=False, status_code=502, error_type=type(exc).__name__)
        db.add(log); db.commit(); REQUESTS.labels(model=model, status="error").inc(); ERRORS.labels(model=model, error_type=type(exc).__name__).inc()
        raise HTTPException(status_code=502, detail={"request_id": request_id, "error": str(exc)})

@app.post("/v1/evaluate", response_model=CompareResponse)
def compare(request: CompareRequest):
    results = []
    for model in request.models:
        messages = []
        if request.system_prompt: messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        try:
            data, elapsed = client.chat({"model": model, "messages": messages, "usage": {"include": True}})
            usage = data.get("usage") or {}
            inp = int(usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0) or 0); out = int(usage.get("completion_tokens", 0) or usage.get("output_tokens", 0) or 0); total = int(usage.get("total_tokens", inp+out))
            prices = client.pricing_map(); pp, cp = prices.get(model, (0.0,0.0)); reported_cost = usage.get("cost")
            cost = float(reported_cost) if reported_cost is not None else (inp*pp + out*cp)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            quality = evaluator.judge(request.prompt, content, request.judge_model)
            results.append(CompareResult(model=model, success=True, latency_ms=round(elapsed*1000,2), input_tokens=inp, output_tokens=out, total_tokens=total, estimated_cost_usd=round(cost,8), quality_score=quality, response=content))
        except Exception as exc:
            results.append(CompareResult(model=model, success=False, latency_ms=0, input_tokens=0, output_tokens=0, total_tokens=0, estimated_cost_usd=0, error=str(exc)))
    return CompareResponse(prompt=request.prompt, results=results)
