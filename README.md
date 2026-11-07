# Noir incident-evidence demonstration

A read-only FastAPI tool service for the V1 incident-investigation demonstration.
It serves synthetic incident, release, observability and knowledge fixtures from
`data/`. The multi-agent architecture and demonstration scope are described in
[the solution design](docs/solution-design/FINAL-SUBMISSION.md).

## Local setup

From the repository root, create an isolated Python environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/api/requirements.txt
.venv/bin/python -m uvicorn tools.api.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` for the API explorer. The demonstration uses
local files; no model endpoint, Microsoft Foundry account, cloud credentials or
database is needed to run this tool service. The existing dependencies are
unpinned; setup requires package access and is not a locked, offline install.

| Route | Purpose |
| --- | --- |
| `GET /health` | Tool-service health; does not validate evidence availability |
| `GET /incidents/{incident_id}` | Incident record |
| `GET /observability/{incident_id}` | Incident observability evidence |
| `GET /repository/releases/{version}` | Bundled `v2.8.4` release evidence; other versions return 404 |
| `GET /knowledge/historical-incidents` | Historical incident evidence |
| `GET /knowledge/database-troubleshooting` | Markdown runbook |

## Regression tests

```sh
.venv/bin/python -m pip install -r tools/api/requirements-test.txt
.venv/bin/python -m unittest discover -s tests -v
```

The suite uses FastAPI's in-process TestClient with `httpx2` and standard-library
unittest, following the [current TestClient guidance](https://starlette.dev/testclient/).
Each test redirects the evidence root to its own temporary directory;
it does not modify the checked-in fixtures, start a listening server, contact
cloud services or require credentials. Package installation requires network
access, but test requests remain in process.

Coverage includes successful routes, ID/version selection, missing evidence,
malformed JSON, unsupported releases, UTF-8 runbooks, fixture isolation and
rejection of POST requests. The read-only GitHub Actions workflow runs the suite
on Python 3.12 and 3.15. These tests cover the local evidence service, not agent
orchestration, production integrations or deployment readiness.
