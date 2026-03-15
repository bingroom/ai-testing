# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a SONiC (Software for Open Networking in the Cloud) network switch smoke testing script. It connects to a SONiC switch running in QEMU via SSH port forwarding and validates basic functionality including Docker services, running config, syslog, and reboot/reconnection behavior.

## Running the Script

```bash
python test.py
```

Requires `netmiko` installed:
```bash
pip install netmiko
```

## Architecture

Single-file script (`test.py`) using the `netmiko` library. The `run_smoke_test()` function:

1. Connects via SSH to `127.0.0.1:2222` (QEMU port-forwarded SONiC device)
2. Runs sequential health checks: Docker status → running config → syslog
3. Triggers a reboot, then polls reconnection (60s initial wait, up to 10 retries × 15s)
4. Validates uptime post-reboot

## Device Connection

Connection parameters are hardcoded at the top of `test.py` in the `sonic_device` dict. The device type is `linux` since SONiC is Linux-based. `global_delay_factor: 2` accommodates VM latency.

## Code Comments

Source code comments and print statements are in Traditional Chinese (繁體中文).
