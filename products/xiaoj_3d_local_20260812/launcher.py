#!/usr/bin/env python3
"""Isolated local launcher: serves only this product directory."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
port = int(os.environ.get("XIAOJ_3D_PORT", "4173"))
print(f"Xiao J 3D local product: http://127.0.0.1:{port}", flush=True)
ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler).serve_forever()
