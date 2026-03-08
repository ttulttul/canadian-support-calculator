# Canadian Support Calculator

A React + Flask calculator for child support and SSAG-style spousal support estimates, now packaged as both a browser app and a macOS Electron desktop app with GitHub-release auto-updates.

## Scope

- Child support supports 1 through 7 children.
- Seven children use the federal "6 or more" table.
- Child support uses bundled 2017 federal tables and the official over-$150,000 formulas for all supported non-Quebec jurisdictions.
- Spousal support is an estimate based on the notebook's net-disposable-income approach and indexed federal and provincial tax brackets with a user-selected tax year.
- The app can export a styled PDF working report generated with WeasyPrint.
- Desktop releases are packaged for macOS and publish update metadata through GitHub Releases.
- This is not legal advice.

## Setup

```bash
uv sync --group dev
npm install
```

The root `package.json` is the canonical application version. Release tooling syncs that version into the frontend package and `pyproject.toml`.

## Local development

### Browser app

```bash
uv run python run_dev.py
```

The launcher starts Flask and Vite together, beginning with ports `5001` and `5173`. If either port is already in use, it increments until it finds an available port and wires the frontend proxy to the selected backend port automatically.

### Backend only

```bash
uv run python -m support_calculator
```

The Flask API starts on `http://127.0.0.1:5001`.

### Frontend only

```bash
npm run frontend:dev
```

The Vite dev server runs on `http://127.0.0.1:5173`.

### Electron desktop app

```bash
npm run desktop:dev
```

This starts Vite on `127.0.0.1:5173`, launches Electron, and has Electron start its own local Flask backend on an available loopback port.

## Desktop builds

```bash
npm run desktop:build
```

The build flow:

1. Builds the Vite frontend.
2. Freezes the Flask backend with PyInstaller into `dist/backend-bundle`.
3. Builds a universal macOS Electron app, DMG, ZIP, and updater metadata into `dist/electron`.

Local macOS builds also require the Xcode license to be accepted once:

```bash
sudo xcodebuild -license
```

## Tests

Run the full project test suite with:

```bash
npm run backend:test
npm run frontend:test
npm run desktop:test
```

## Tagged releases

Prepare a release commit and tag:

```bash
npm run release:prepare -- 0.2.0
```

Push the branch and tag to GitHub:

```bash
npm run release:push -- 0.2.0
```

The GitHub Actions workflow on `v*` tags runs tests, builds the backend bundle, signs and notarizes the Electron app when signing secrets are present, and publishes the release artifacts to GitHub Releases.

### Required release secrets

- `CSC_LINK`
- `CSC_KEY_PASSWORD`
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`
