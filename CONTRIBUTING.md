# Contributing

Thanks for your interest in contributing to korean-pii.

## Scope
This project targets CPU-only, air-gapped environments. Changes should
preserve this constraint.

## How to contribute
- Use GitHub Issues for bugs or feature requests.
- Keep PRs focused and small.
- If you change behavior or API, update `README.md`.

## Development setup
Requirements:
- Python 3.12
- uv

Setup:
```bash
uv sync
```

Run locally:
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Model assets
- If you add or update model files under `models/`, include the upstream
  license and attribution in `NOTICE`.
- Large binaries should use Git LFS or be distributed via releases.

## Testing
There is no formal test suite documented yet. If you add tests, please
document how to run them here.

## Security
If you discover a security or PII-related issue, please report it privately:
- Contact: TBD

## License
By contributing, you agree that your contributions are licensed under the
Apache License 2.0.
