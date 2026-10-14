# Kestrel field service agent

The agent you build in this lab. Kestrel Industrial is fictional; so is every part number.

## The three files that matter

| File | What it holds |
|---|---|
| `tools.py` | The tool definitions the model is shown, and the code behind them |
| `agent.py` | The agent loop |
| `config.toml` | Which model endpoint the agent calls, and the other settings |

Everything else supports those three: `llm.py` (the one function that calls the model),
`runlog.py` and `payloads.py` (saved request and response payloads), `tracing.py` (MLflow),
`fixtures/` (the fictional data), `retrieval.py` and `ingest_corpus.py` (knowledge search),
`regression.py` (module 7).

## Run it

```bash
pip install -r requirements.txt
python agent.py --q m1            # the module 1 question; see questions.py for the others
python agent.py "your own question"
python payloads.py                # the raw request and response of the last run
```

Every run saves the raw request and response of each model call under `runs/`. No debug
logging is needed.

## Tracing (optional)

```bash
export MLFLOW_TRACKING_URI=https://<direct-route-to-mlflow>/mlflow   # not the OpenShift AI Gateway; keep /mlflow
export MLFLOW_WORKSPACE=<your-namespace>                              # OpenShift AI MLflow workspaces are namespaces
export MLFLOW_TRACKING_TOKEN=<bearer-token>
```

Without the `/mlflow` path the client's workspace check (`/api/3.0/mlflow/server-info`) gets a 404,
and `set_experiment` fails with "the remote server does not support workspaces".

Unset, tracing does nothing and the agent runs as normal.

## Knowledge search (module 5)

The corpus is ingested at provisioning time with `python ingest_corpus.py`. Both scripts read
`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD`. Query it directly with
`python retrieval.py "your query"`.

## Maintainers

`solutions/` holds the supplied fixes, cumulative by module (copy the `.py` files over this
directory). Tests and a local mock of the model endpoints are in `../tests/agent/`.
