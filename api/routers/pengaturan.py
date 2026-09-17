"""
KasirKu API — Pengeluaran & Pengaturan Router
"""

from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, status, Depends, Query

from database.db import db
from database.models import Pengeluaran, Pengaturan
from api.deps import get_current_user_payload, require_admin, get_current_user_id
from api.schemas import (
    PengeluaranCreate, PengeluaranOut,
    PengaturanOut, PengaturanUpdate, MessageResponse,
)

# ──────────────────────────── PENGELUARAN ────────────────────────────

pengeluaran_router = APIRouter(prefix="/api/pengeluaran", tags=["pengeluaran"])


@pengeluaran_router.get("", response_model=List[PengeluaranOut])
def list_pengeluaran(
    tanggal: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    _: dict = Depends(get_current_user_payload),
):
    """Daftar pengeluaran. Filter by tanggal opsional."""
    with db.get_session() as session:
        q = session.query(Pengeluaran)
        if tanggal:
            start = datetime(tanggal.year, tanggal.month, tanggal.day, 0, 0, 0)
            end = datetime(tanggal.year, tanggal.month, tanggal.day, 23, 59, 59)
            q = q.filter(Pengeluaran.tanggal >= start, Pengeluaran.tanggal <= end)
        items = q.order_by(Pengeluaran.tanggal.desc()).limit(limit).all()
        return [PengeluaranOut.model_validate(p) for p in items]


@pengeluaran_router.post("", response_model=PengeluaranOut, status_code=status.HTTP_201_CREATED)
def create_pengeluaran(
    body: PengeluaranCreate,
    user_id: int = Depends(get_current_user_id),
):
    """Catat pengeluaran baru."""
    with db.get_session() as session:
        p = Pengeluaran(
            kategori=body.kategori,
            deskripsi=body.deskripsi,
            nominal=body.nominal,
            user_id=user_id,
        )
        session.add(p)
        session.flush()
        return PengeluaranOut.model_validate(p)


@pengeluaran_router.delete("/{pengeluaran_id}", response_model=MessageResponse)
def delete_pengeluaran(
    pengeluaran_id: int,
    _: dict = Depends(require_admin),
):
    """Hapus pengeluaran. Hanya admin."""
    with db.get_session() as session:
        p = session.query(Pengeluaran).filter_by(id=pengeluaran_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Pengeluaran tidak ditemukan")
        session.delete(p)
        return MessageResponse(message="Pengeluaran berhasil dihapus")


# ──────────────────────────── PENGATURAN ────────────────────────────

pengaturan_router = APIRouter(prefix="/api/pengaturan", tags=["pengaturan"])

# Kunci pengaturan yang boleh dibaca siapa saja (tanpa admin)
_PUBLIC_KEYS = {"store_name", "store_address", "store_phone", "store_tagline"}


@pengaturan_router.get("", response_model=List[PengaturanOut])
def list_pengaturan(_: dict = Depends(get_current_user_payload)):
    """Semua pengaturan toko."""
    with db.get_session() as session:
        items = session.query(Pengaturan).order_by(Pengaturan.kunci).all()
        return [PengaturanOut.model_validate(p) for p in items]


@pengaturan_router.get("/{kunci}", response_model=PengaturanOut)
def get_pengaturan(kunci: str, _: dict = Depends(get_current_user_payload)):
    """Ambil satu pengaturan by kunci."""
    with db.get_session() as session:
        p = session.query(Pengaturan).filter_by(kunci=kunci).first()
        if not p:
            raise HTTPException(status_code=404, detail=f"Kunci '{kunci}' tidak ditemukan")
        return PengaturanOut.model_validate(p)


@pengaturan_router.put("/{kunci}", response_model=PengaturanOut)
def update_pengaturan(
    kunci: str,
    body: PengaturanUpdate,
    _: dict = Depends(require_admin),
):
    """Update pengaturan. Hanya admin."""
    db.set_setting(kunci, body.nilai or "")
    with db.get_session() as session:
        p = session.query(Pengaturan).filter_by(kunci=kunci).first()
        if not p:
            raise HTTPException(status_code=404, detail=f"Kunci '{kunci}' tidak ditemukan")
        return PengaturanOut.model_validate(p)
