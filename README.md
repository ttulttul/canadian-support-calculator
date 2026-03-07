# Canadian Support Calculator

A React + Flask application for exploring child support and spousal support estimates using the bundled British Columbia child-support table from the provided notebook and a BC tax approximation for SSAG-style spousal-support modelling.

## Scope

- Child support uses the bundled BC table data from the supplied CSV.
- Spousal support is an estimate based on the notebook's net-disposable-income approach and an approximate BC tax model.
- This is not legal advice.

## Local development

### Combined launcher

```bash
uv run python run_dev.py
```

The launcher starts Flask and Vite together, beginning with ports `5001` and `5173`. If either port is already in use, it increments until it finds an available port and wires the frontend proxy to the selected backend port automatically.

### Backend

```bash
uv sync --group dev
uv run python -m support_calculator
```

The Flask API starts on `http://127.0.0.1:5001`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` and proxies `/api` to Flask.

## Tests

```bash
uv run pytest
```
