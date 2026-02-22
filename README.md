# dante-config

Async Python library for discovering and configuring [Dante](https://www.audinate.com/dante) audio networking devices over a local network.

Uses `asyncio` and `zeroconf` for mDNS discovery. Requires Python 3.11+.

## Installation

```bash
pip install dante-config
```

Or from source:

```bash
git clone <repo-url>
cd dante-config
pip install .
```

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```

### Running tests

```bash
pytest                                                # all tests
pytest tests/test_client.py                           # single file
pytest tests/test_client.py::TestClass::test_method   # single test
```

### Linting and formatting

```bash
ruff check .   # lint
black .        # format
mypy src/      # type check (strict mode)
```

## License

MIT
