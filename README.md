# dante-config

Async Python library for discovering and configuring [Dante](https://www.audinate.com/dante) audio networking devices over a local network.

Uses `asyncio` and `zeroconf` for mDNS discovery. Requires Python 3.11+.

## Installation

```bash
pip install dante-config
```

Or from source:

```bash
git clone https://github.com/jda/dante-config.git
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

## Contributing

Issues and pull requests welcome at https://github.com/jda/dante-config/issues. This is a small project — open an issue to discuss larger changes before sending a PR.

## License

MIT

## Trademarks

Dante is a registered trademark of Audinate Group Pty Ltd. This project is not affiliated with or endorsed by Audinate.
