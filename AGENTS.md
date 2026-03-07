## Dev environment tips
- Use `uv sync --group dev` to create or refresh the local `.venv`.
- The `rg` command is installed; use it for quick searching.
- This is a MacOS environment.
- The git server we use it Bitbucket.
- Commit every change you make and ask the user to push changes when a significant batch of changes has been made.

## Dev process tips
- Use Python logging liberally to insert judicious info, warning, and debug messages in the code.
- Import logging into each module, create a logger, and use it for logging in that module.
- In most cases where an error message is called for, you should raise an appropriate exception. We want to know.

## Testing instructions
- Add or update tests for the code you change, even if nobody asked.
- Test liberally. We want to code cautiously.
- There is a test suite in tests that can be run using `uv run pytest`
- Run the full test suite every time you make a change before you commit.
