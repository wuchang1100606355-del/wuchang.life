#!/usr/bin/env python3
"""Systemd entrypoint; loads the existing versioned capability and hash contract."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from w7tp_adaptive_network.runtime_adapter import AdaptiveRuntime, load_contract, serve

if __name__ == "__main__":
    load_contract()
    serve(AdaptiveRuntime())
