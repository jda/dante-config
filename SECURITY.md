# Security Policy

## Reporting a Vulnerability

If you find a security issue in dante-config, please email jade@jade.wtf rather than opening a public issue. Include reproduction steps and the affected version. You can expect an acknowledgement within 7 days.

## Scope

This library sends and parses Dante ARC and Settings protocol frames over a local network. Issues of particular interest:

- Frame parsers reading beyond buffer bounds or panicking on malformed input.
- Anything in the discovery layer (`zeroconf`) that could be triggered by a malicious responder on the same LAN.
- Frame builders that could be coerced into sending unintended commands to a device.

Out of scope: vulnerabilities in Dante devices themselves (report those to Audinate) or in transitive dependencies (report upstream).
