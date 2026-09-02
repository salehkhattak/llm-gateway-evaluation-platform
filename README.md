# LLM Gateway & Model Evaluation Platform

A FastAPI gateway that sends chat requests to [OpenRouter](https://openrouter.ai), compares multiple LLMs on the same prompt, and records the operational data needed to choose models by quality, speed, cost, and reliability.

## What the App Does

### Chat gateway

`POST /v1/chat/completions` forwards a chat request to OpenRouter. It returns the generated text together with the model used, latency, token usage, estimated cost, and an optional quality score.

### Model evaluation

`POST /v1/evaluate` sends one prompt to 2 to 8 models and returns a result for each model. The comparison includes latency, input/output/total tokens, estimated cost, success state, response text, and quality score.

### Persistence and monitoring

- PostgreSQL stores request and evaluation records.
- Prometheus scrapes the gateway's `/metrics` endpoint.
- Grafana loads the provisioned dashboard from `grafana/dashboards`.
- OpenRouter model metadata supplies model pricing and provider discovery.

The gateway prefers the cost returned by OpenRouter. If no cost is returned, it estimates cost from token usage and the model catalog. Quality scoring is heuristic by default; the comparison endpoint can optionally use a judge model.

## Architecture

```text
Client
  |
  v
FastAPI gateway -----> OpenRouter -----> LLM providers
  |
  +----> PostgreSQL request and evaluation history
  |
  +----> Prometheus metrics ----> Grafana dashboard
```

## Quick Start With Docker

### Prerequisites

- Docker Desktop with Docker Compose
- An OpenRouter API key for live model requests

Run these commands from:

```text
gpt-llm/llm-gateway-evaluation-platform/llm-gateway-evaluation-platform
```

### 1. Create `.env`

Windows PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `OPENROUTER_API_KEY` to a valid key. Keep `.env` private and do not commit it. Create a key at <https://openrouter.ai/keys>.

### 2. Build and start the full stack

```powershell
docker compose up -d --build
```

The `-d` flag keeps the services running in the background. The first build downloads the Python, PostgreSQL, Prometheus, and Grafana images and may take a few minutes.

Check service status:

```powershell
docker compose ps
```

Open:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>

Grafana credentials are `admin` / `admin` by default.

### 3. Verify the API

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"LLM Gateway & Model Evaluation Platform"}
```

### Start without Grafana

If another application already uses port `3000`, start the core services only:

```powershell
docker compose up -d --build api postgres prometheus
```

The API and Prometheus remain available on ports `8000` and `9090`.

### Stop the stack

```powershell
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete the PostgreSQL and Grafana data volumes.

## Run Without Docker

This mode is useful for API development. SQLite can replace PostgreSQL locally; Docker Compose remains the recommended way to run the complete stack.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

$env:OPENROUTER_API_KEY = "your-openrouter-key"
$env:DATABASE_URL = "sqlite:///./dev.db"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

export OPENROUTER_API_KEY="your-openrouter-key"
export DATABASE_URL="sqlite:///./dev.db"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The local API is available at <http://localhost:8000>. Tables are created automatically when the application starts.

## Configuration

Settings are read from environment variables and `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | required | Authenticates requests to OpenRouter |
| `DATABASE_URL` | Docker PostgreSQL URL | SQLAlchemy database connection |
| `OPENROUTER_BASE_URL` | OpenRouter API URL | OpenRouter-compatible API base URL |
| `DEFAULT_MODEL` | `openrouter/free` | Model used when a chat request omits `model` |
| `EVALUATION_MODEL` | `openai/gpt-5.5` | Default judge model setting |
| `SITE_URL` | `http://localhost:8000` | Application URL sent as metadata |
| `SITE_NAME` | `LLM Gateway` | Application name sent as metadata |
| `HTTP_TIMEOUT_SECONDS` | `90` | Upstream request timeout |
| `MODEL_CACHE_SECONDS` | `300` | OpenRouter model-catalog cache duration |

## API Usage

### Health and provider discovery

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/providers
```

`/health` checks that the application is running. `/health/providers` checks OpenRouter model and provider discovery and reports the number of available models/providers.

### Send a chat request

PowerShell:

```powershell
$body = @{
  model = "openrouter/free"
  messages = @(
    @{ role = "user"; content = "Explain Kubernetes in three bullets." }
  )
  evaluate = $true
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/chat/completions `
  -ContentType "application/json" `
  -Body $body
```

Optional request fields are `temperature` from 0 to 2 and a positive `max_tokens` value. Set `evaluate` to `false` to skip the quality score.

### Compare models

```powershell
$body = @{
  prompt = "Explain Kubernetes in simple terms."
  models = @("openrouter/free", "openai/gpt-5.5")
  system_prompt = "Answer clearly for a beginner."
  judge_model = "openai/gpt-5.5"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/evaluate `
  -ContentType "application/json" `
  -Body $body
```

The `models` list must contain between 2 and 8 model IDs. A failed model is returned as a result with `success: false` and an error instead of failing the entire comparison.

## Metrics and Monitoring

Prometheus scrapes the API at:

```text
http://localhost:8000/metrics
```

The project tracks request counts, errors, latency, token usage, cost, quality, active model count, and provider availability. Prometheus is available at <http://localhost:9090>, and Grafana is available at <http://localhost:3000> when the Grafana service is running.

## Testing

Install the dependencies and run:

```powershell
python -m pip install -r requirements.txt
pytest -q
```

The test suite uses mocked HTTP calls and does not require a live OpenRouter key. For tests, SQLite is used instead of PostgreSQL.

## Project Structure

```text
app/
  main.py             FastAPI routes, startup, health, and metrics
  config.py           Environment-backed settings
  db.py               SQLAlchemy database setup and request log model
  schemas.py          API request and response models
  openrouter.py       OpenRouter catalog, pricing, and chat client
  evaluator.py        Heuristic and judge-model quality scoring
  metrics.py          Prometheus metric definitions
tests/                Automated tests
prometheus/           Prometheus scrape configuration
grafana/              Provisioned dashboards and data sources
k8s/                  Kubernetes deployment manifest
docker-compose.yml    API, PostgreSQL, Prometheus, and Grafana services
Dockerfile            API container image
Makefile              Common install, test, run, and Docker commands
```

## Common Commands

```powershell
# Install dependencies
make install

# Run tests
make test

# Run the API with reload
make run

# Start the Docker stack
make up

# Stop the Docker stack
make down
```

On Windows, use the equivalent commands directly if `make` is not installed.

## Troubleshooting

### `env file ... .env not found`

Create the required file before starting Compose:

```powershell
Copy-Item .env.example .env
```

### Port already in use

Check a port in PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8000,3000,5432,9090 -ErrorAction SilentlyContinue
```

Run only `api postgres prometheus` when port `3000` is occupied by another application.

### OpenRouter calls fail

Check that `OPENROUTER_API_KEY` is set in `.env`, then recreate the API container:

```powershell
docker compose up -d --force-recreate api
```

Inspect logs:

```powershell
docker compose logs --tail 100 api
```

## Kubernetes

The included manifest can be applied after replacing the image reference and configuring the API key:

```bash
kubectl apply -f k8s/deploy.yaml
```

Before production use, add managed PostgreSQL, TLS, an ingress, resource limits, autoscaling, external secrets, network policies, and durable monitoring storage.

## GitHub Actions

The workflow runs tests and builds the Docker image on pushes and pull requests. It does not publish credentials or deploy automatically until a registry and cluster are configured.

## Future Roadmap

### Phase 1: Developer experience and reliability

- Add structured error responses with stable error codes and request IDs.
- Add request validation for unsupported models, oversized prompts, and unsafe token limits.
- Add database migrations with Alembic instead of relying only on startup table creation.
- Expand unit and API coverage for provider failures, timeouts, rate limits, and partial evaluation results.
- Add a health check that distinguishes API availability, database availability, and OpenRouter availability.

### Phase 2: Smarter gateway behavior

- Add routing policies for cheapest, fastest, highest-quality, or fallback models.
- Store OpenRouter generation IDs, provider metadata, and selected endpoint information.
- Add configurable retries with exponential backoff for transient upstream failures.
- Add Redis-backed response caching, rate limiting, and short-lived model-catalog caching.
- Support streaming responses with Server-Sent Events for interactive chat clients.

### Phase 3: Scalable evaluation

- Move long-running evaluations and judge-model calls to background workers or a task queue.
- Add evaluation datasets with reusable prompts, expected answers, tags, and versioning.
- Support batch evaluation runs and historical model-to-model comparisons.
- Add configurable quality metrics, including exact match, similarity, JSON validity, and rubric-based judging.
- Add export of evaluation results as JSON or CSV for offline analysis.

### Phase 4: Production operations

- Add OpenTelemetry traces covering gateway, database, OpenRouter, and judge calls.
- Add Prometheus alert rules for error rate, latency, provider outages, and unexpected cost increases.
- Add load testing with k6 and define performance targets for common workloads.
- Add Kubernetes resource requests, limits, autoscaling, network policies, and external secret management.
- Add continuous delivery to a container registry and a staging environment with approval-based production deploys.

### Long-term product direction

The platform can evolve from a request proxy into a model decision system: it can learn from historical evaluations, recommend a model for each workload, explain the cost and quality trade-offs, and automatically fall back when a provider is slow or unavailable.
