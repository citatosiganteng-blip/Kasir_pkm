"""
KasirKu API — FastAPI Application
Mendaftarkan semua router, CORS, static files, dan middleware
"""

import sys
import os

# Tambahkan root project ke path agar bisa import database, auth, utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from database.db import db

# ──────────────────────────── Init DB ────────────────────────────
db.initialize()

# ──────────────────────────── FastAPI App ────────────────────────────
app = FastAPI(
    title="KasirKu API",
    description=(
        "REST API untuk aplikasi kasir KasirKu. "
        "Akses Swagger UI di **/docs** atau ReDoc di **/redoc**."
    ),
    version="1.0.0",
    contact={"name": "PKM Team"},
)

# ──────────────────────────── CORS ────────────────────────────
# Izinkan semua origin di LAN (WiFi lokal)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Aman untuk LAN; batasi di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────── Routers ────────────────────────────
from api.routers.auth import router as auth_router
from api.routers.barang import router as barang_router
from api.routers.transaksi import router as transaksi_router
from api.routers.laporan import router as laporan_router
from api.routers.pengaturan import pengeluaran_router, pengaturan_router

app.include_router(auth_router)
app.include_router(barang_router)
app.include_router(transaksi_router)
app.include_router(laporan_router)
app.include_router(pengeluaran_router)
app.include_router(pengaturan_router)

# ──────────────────────────── Static / PWA ────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_pwa():
        """Sajikan Web UI (PWA) kasir mobile"""
        return FileResponse(str(STATIC_DIR / "index.html"))


# ──────────────────────────── Health Check ────────────────────────────
@app.get("/api/health", tags=["health"])
def health_check():
    """Cek status server API"""
    return {"status": "ok", "app": "KasirKu API", "version": "1.0.0"}
