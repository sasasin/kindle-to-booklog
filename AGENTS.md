# Codex Instructions

## Python Changes

When modifying Python code in this repository, always finish by running the following commands and make sure they succeed:

```bash
uv run --group dev ruff check . --fix
uv run --group dev ruff format .
uv run --group dev coverage run -m unittest discover -s tests
```

If a command cannot be completed in the current sandbox because of permissions or cache access, rerun it with the required approval instead of skipping it.
