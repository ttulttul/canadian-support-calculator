# Canadian Support Calculator

A React + Flask application for exploring child support and spousal support estimates using bundled 2017 federal child-support tables for all supported non-Quebec jurisdictions and a jurisdiction-aware tax and benefit model for SSAG-style spousal-support modelling.

## Scope

- Child support supports 1 through 7 children.
- Seven children use the federal "6 or more" table.
- Child support uses bundled 2017 federal tables before tax year 2025 and the updated October 1, 2025 federal tables for tax year 2025 onward, with official over-$150,000 formulas for all supported non-Quebec jurisdictions.
- Spousal support is an estimate based on the notebook's net-disposable-income approach and a payroll-aware annual tax model with federal and provincial brackets, basic credits, CPP, EI, and a user-selected tax year.
- The app can export a styled PDF working report generated with WeasyPrint.
- This is not legal advice.

## Local development

### Combined launcher

```bash
uv run python run_dev.py
```

The launcher starts Flask and Vite together, beginning with ports `5001` and `5173`. If either port is already in use, it increments until it finds an available port and wires the frontend proxy to the selected backend port automatically.
The launcher also enables Flask reload mode, so backend source changes are picked up automatically while developing.

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
