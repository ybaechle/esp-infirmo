# ia/ — private service scaffold

Owner: Pierre-Arthur Toutouom Yountebo. The service currently exposes `/health` only; Whisper transcription is not implemented and is outside the v0.1 login/profile increment.

## Reproduce validation

Prerequisites: Python 3.12 and uv 0.11.17. From `ia/`:

```sh
uv sync --locked --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run pytest -q --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=70 --junitxml=test-results.xml
```

Coverage measures the existing scaffold only; it is not transcription coverage. CI uploads `coverage.xml` and `test-results.xml`. The image is built from this lockfile by root Docker Compose; IA remains on a private network reachable only by the backend. Use synthetic test data only.

Released independently as `ia-vX.Y.Z`.
