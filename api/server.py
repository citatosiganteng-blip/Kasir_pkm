"""
KasirKu API — Uvicorn Server Entry Point
Jalankan: python api/server.py
"""

import sys
import os
import socket

# Root project ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn


def get_local_ip() -> str:
    """Dapatkan IP address LAN lokal mesin ini"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("KASIRKU_API_PORT", "8000"))
    local_ip = get_local_ip()

    print("=" * 55)
    print("  [*]  KasirKu REST API Server")
    print("=" * 55)
    print(f"  [PC]  Lokal    : http://127.0.0.1:{port}")
    print(f"  [HP]  LAN/WiFi : http://{local_ip}:{port}")
    print(f"  [Doc] Docs     : http://{local_ip}:{port}/docs")
    print(f"  [Web] Web UI   : http://{local_ip}:{port}/")
    print("=" * 55)
    print("  Bagikan URL LAN ke HP/Tablet di WiFi yang sama")
    print("=" * 55)

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="warning",
    )
