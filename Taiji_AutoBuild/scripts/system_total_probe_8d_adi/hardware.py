from __future__ import annotations

import os
import platform
import socket
from pathlib import Path
from typing import Any

from .foundation import sha256_bytes, utc_now


def read_signal(path: Path, max_bytes: int = 4096) -> bytes | None:
    try:
        data = path.read_bytes()[:max_bytes].strip()
    except OSError:
        return None
    return data or None


def commandless_hardware_signals() -> list[dict[str, Any]]:
    candidates = {
        "etc_machine_id": Path("/etc/machine-id"),
        "dbus_machine_id": Path("/var/lib/dbus/machine-id"),
        "dmi_product_uuid": Path("/sys/class/dmi/id/product_uuid"),
        "dmi_product_serial": Path("/sys/class/dmi/id/product_serial"),
        "dmi_board_serial": Path("/sys/class/dmi/id/board_serial"),
    }
    signals: list[dict[str, Any]] = []
    for name, path in candidates.items():
        data = read_signal(path)
        signals.append(
            {
                "name": name,
                "available": data is not None,
                "sha256": sha256_bytes(data) if data else None,
                "raw_printed": False,
            }
        )

    platform_blob = "\n".join(
        [
            platform.system(),
            platform.release(),
            platform.machine(),
            str(os.cpu_count() or ""),
            socket.gethostname(),
        ]
    ).encode("utf-8")
    signals.append(
        {
            "name": "platform_runtime",
            "available": True,
            "sha256": sha256_bytes(platform_blob),
            "raw_printed": False,
        }
    )
    return signals


def hardware_fingerprint() -> dict[str, Any]:
    signals = commandless_hardware_signals()
    stable = [
        f"{item['name']}={item['sha256']}"
        for item in signals
        if item.get("available") and item.get("sha256")
    ]
    aggregate = "\n".join(sorted(stable)).encode("utf-8")
    return {
        "schema": "taiji.hardware_fingerprint.v1",
        "generated_at": utc_now(),
        "fingerprint_sha256": sha256_bytes(aggregate),
        "signal_count": len(stable),
        "signals": signals,
        "raw_hardware_printed": False,
    }
