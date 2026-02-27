# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**dante-config** — async Python library for discovering and controlling Dante audio networking devices over a local network. Pure library with no framework; uses `asyncio` and `zeroconf` for mDNS discovery. Intended consumer is Home Assistant.

## Commands

```bash
pip install -e ".[dev]"    # Install with dev dependencies
pytest                      # Run all tests (asyncio_mode=auto)
pytest tests/test_client.py             # Run a single test file
pytest tests/test_client.py::TestClass::test_method  # Run a single test
mypy src/                   # Type check (strict mode)
ruff check .                # Lint
black .                     # Format
```

## Architecture

Two independent UDP binary protocols communicate with each Dante device:

| Protocol | Port | Module | Purpose | Response matching |
|----------|------|--------|---------|-------------------|
| ARC | 4440 (`PORT_ARC`) | `protocol/arc.py` | Channels, subscriptions, device names, identification | 16-bit `seq_id` in frame header; pending dict in transport |
| Settings | 8700 (unicast) / 8702 (multicast responses) | `protocol/settings.py` | Sample rate, encoding, reboot, identify LED | Single serialized waiter in transport; multicast listener delivers responses |

### Layer stack

```
DanteClient (client.py)          — High-level async API, orchestrates both protocols
    ├── protocol/arc.py          — ARC frame builders + response parsers
    ├── protocol/settings.py     — Settings frame builders + response parsers
    └── protocol/common.py       — Shared: build_arc_frame(), build_settings_frame(), get_label(), mac_str_to_bytes()
DanteUDPProtocol (transport.py)  — asyncio.DatagramProtocol, request/response matching
DanteMulticastProtocol (transport.py) — Multicast listener; delivers Settings responses via deliver_response()
    Factory: create_dante_transport(), create_multicast_listener()
DanteBrowser (discovery.py)      — mDNS browser over zeroconf (4 service types), builds DanteDeviceInfo
models.py                        — Dataclasses: DanteDeviceInfo, DanteChannel, DanteSubscription, DanteServiceRecord
const.py                         — Enums (ArcCommand, SettingsCommand, SubscriptionStatus, Encoding), ports, magic bytes
exceptions.py                    — DanteError hierarchy (Connection, Timeout, Protocol, Command)
```

### Wire protocol conventions

- All frames are big-endian (`struct.pack(">...")`).
- ARC frames: magic `0x28 0x09`, length patched at byte 3, seq_id at bytes 4-5, command at bytes 6-7. Transport also accepts legacy `0x27` magic for backward compatibility.
- Settings frames: magic `0xFFFF`, 6-byte MAC target, "Audinate" vendor string, command at bytes 26-27.
- Responses are parsed by hex-slicing (`response.hex()[offset:offset+n]`) — this mirrors the pointer-arithmetic style of the Dante protocol and is intentional.
- `get_label()` dereferences null-terminated strings via hex offset fields embedded in responses (Dante's offset-pointer scheme).
- Frame builders return `(bytes, seq_id)` for ARC, plain `bytes` for Settings.

### Key design decisions

- `DanteBrowser` accepts an external `Zeroconf` instance (caller shares it, e.g., Home Assistant's shared instance).
- Pagination: TX channels up to 32/page, RX channels up to 16/page, via `_build_pagination()`.
- `SubscriptionStatus` IntEnum has property-based classification: `.is_connected`, `.is_error`, `.is_transient`.
- All modules use `from __future__ import annotations`.

## Testing

Tests use `unittest.mock` exclusively — no real network calls. Test files mirror source modules (`test_protocol_arc.py`, `test_protocol_settings.py`, `test_client.py`, `test_transport.py`, `test_discovery.py`, `test_models.py`).

## Tool config

- Python >=3.11 required (union type syntax, match statements)
- mypy strict mode enabled
- ruff targets py311
- Hatchling build system with `src/` layout
