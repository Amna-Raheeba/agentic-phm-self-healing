# Root conftest: pytest adds this file's directory (the repo root) to sys.path,
# which keeps `import phm_agents` working when tests are run with the plain
# `pytest` binary in CI — not just with `python -m pytest` locally.
