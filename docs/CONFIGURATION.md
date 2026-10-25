# Configuration

## Settings

| Variable | Required | Default | Purpose |
|----------|----------|---------|-------------|
| `GEOFAHAM_DEFAULT_MODEL_CLIENT` | Unless roles override it | - | AutoGen `ChatCompletionClient` component config for Maps and STAC |
| `GEOFAHAM_REASONING_MODEL_CLIENT` | Unless roles override it | - | AutoGen `ChatCompletionClient` component config for Vector, Raster, and Orchestrator |
| `GEOFAHAM_*_MODEL_CLIENT` | No | - | Per-agent model client override |
| `AZURE_MAPS_KEY` | For the web map | - | Served to the frontend through `/api/config` |
| `POSTGRES_HOST` | No | localhost | PostgreSQL host |
| `POSTGRES_PORT` | No | 5432 | PostgreSQL port |
| `POSTGRES_DB` | Yes | - | Database name |
| `POSTGRES_USER` | Yes | - | Database user |
| `POSTGRES_PASSWORD` | Yes | - | Database password |
| `GEOFAHAM_BASE_DIR` | No | ./runtime | Runtime artifacts directory |
| `GEOFAHAM_DATA_DIR` | No | ./data | Static data directory |

## Model clients

GeoFaham loads AutoGen model-client component configs directly:

```bash
GEOFAHAM_DEFAULT_MODEL_CLIENT='{"provider":"autogen_ext.models.openai.OpenAIChatCompletionClient","config":{"model":"gpt-4o","api_key":"$OPENAI_API_KEY"}}'
GEOFAHAM_REASONING_MODEL_CLIENT='{"provider":"autogen_ext.models.openai.OpenAIChatCompletionClient","config":{"model":"gpt-5.1","api_key":"$OPENAI_API_KEY","reasoning_effort":"medium"}}'
```

For OpenAI/Azure OpenAI clients, GeoFaham adds a default `model_info` block when it is omitted. These defaults assume tool calling, JSON output, and structured output support, and disable vision. Override `model_info` explicitly if your model has different capabilities.

To use an OpenAI-compatible API:

```bash
GEOFAHAM_DEFAULT_MODEL_CLIENT='{"provider":"autogen_ext.models.openai.OpenAIChatCompletionClient","config":{"model":"provider-model-name","base_url":"https://your-provider.example/v1","api_key":"$PROVIDER_API_KEY"}}'
```

For Azure OpenAI:

```bash
GEOFAHAM_DEFAULT_MODEL_CLIENT='{"provider":"autogen_ext.models.openai.AzureOpenAIChatCompletionClient","config":{"model":"gpt-4o","azure_deployment":"gpt-4o","azure_endpoint":"https://your-resource.openai.azure.com/","api_version":"2024-08-01-preview","api_key":"$AZURE_OPENAI_KEY"}}'
```

Model selection is implemented in [config.py](../agents/core/config.py) and [client.py](../agents/base/client.py).

## Role overrides

Set a complete component configuration for any role that should use a different
client:

- `GEOFAHAM_VECTOR_AGENT_MODEL_CLIENT`
- `GEOFAHAM_MAPS_AGENT_MODEL_CLIENT`
- `GEOFAHAM_STAC_AGENT_MODEL_CLIENT`
- `GEOFAHAM_RASTER_AGENT_MODEL_CLIENT`
- `GEOFAHAM_ORCHESTRATOR_PLANNER_MODEL_CLIENT`
- `GEOFAHAM_ORCHESTRATOR_PROGRESS_MODEL_CLIENT`

The default and reasoning profiles are required for roles without an override.
The reasoning profile chooses a client; `reasoning_effort` is a separate setting
inside its `config`. Use it only with models that support that parameter.

GeoFaham expands exact `$VARIABLE` or `${VARIABLE}` string values recursively
inside a component. Set the referenced credentials in your environment or `.env`.
Provider packages must be installed separately if they are not in the project's
dependencies. See [data directories](DATA_DIRECTORY_STRUCTURE.md) for path settings.

## Execution limits

`GEOFAHAM_SQL_TIMEOUT_SECONDS` defaults to 60. Vector tool queries run in read-only
transactions with PostgreSQL `statement_timeout`; cancellation waits for the query
to stop before its connection is reused.

`GEOFAHAM_RASTER_TIMEOUT_SECONDS` defaults to 300. Each Raster tool call runs in a
separate spawned process, including export. Timeout or chat cancellation stops and
joins the process. Both settings must be positive integers. Memory, filesystem,
and network access are not isolated.

Scripts calling the Raster tool must use Python's `if __name__ == "__main__":`
entry-point guard, as required by spawned multiprocessing. The application entry
point already uses this guard.

## Startup checks

FastAPI checks all six model-client configurations, metadata files, runtime
paths, PostGIS, and SELECT access to `disasters`, `building_damage_assessment`,
and `flood_maps` before accepting requests. A failed check stops startup with
an error identifying the dependency.

Model clients are initialized and closed without sending prompts. These checks
do not verify API authentication, external imagery services, or complete agent
workflows. Database probes are read-only and do not validate every table record.
