"""
KasirKu API — Barang Router
Endpoint: CRUD produk, search, stok
"""

from typing import Optional, List
from pathlib import Path
import uuid
import shutil
from fastapi import APIRouter, HTTPException, status, Depends, Query, UploadFile, File

import config
from database.db import db
from database.models import Barang
from utils.helpers import generate_item_code
from api.deps import get_current_user_payload, require_admin
from api.schemas import BarangOut, BarangCreate, BarangUpdate, MessageResponse

router = APIRouter(prefix="/api/barang", tags=["barang"])


def _barang_to_schema(b: Barang) -> BarangOut:
    return BarangOut(
        id=b.id,
        kode=b.kode,
        barcode=b.barcode,
        nama=b.nama,
        kategori=b.kategori,
        harga_beli=b.harga_beli,
        harga_jual=b.harga_jual,
        stok=b.stok,
        stok_min=b.stok_min,
        satuan=b.satuan,
        deskripsi=b.deskripsi,
        foto=getattr(b, "foto", None),
        aktif=b.aktif,
        is_low_stock=b.is_low_stock,
    )


@router.get("", response_model=List[BarangOut])
def list_barang(
    search: Optional[str] = Query(None, description="Cari nama/kode/barcode"),
    kategori: Optional[str] = Query(None),
    aktif_only: bool = Query(True),
    low_stock_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: dict = Depends(get_current_user_payload),
):
    """Daftar semua barang dengan opsional filter."""
    with db.get_session() as session:
        q = session.query(Barang)
        if aktif_only:
            q = q.filter(Barang.aktif == True)
        if kategori:
            q = q.filter(Barang.kategori == kategori)
        if search:
            term = f"%{search.lower()}%"
            q = q.filter(
                Barang.nama.ilike(term) |
                Barang.kode.ilike(term) |
                Barang.barcode.ilike(term)
            )
        if low_stock_only:
            q = q.filter(Barang.stok <= Barang.stok_min)

        items = q.order_by(Barang.nama).offset(offset).limit(limit).all()
        return [_barang_to_schema(b) for b in items]


@router.get("/kategori", response_model=List[str])
def list_kategori(_: dict = Depends(get_current_user_payload)):
    """Daftar semua kategori barang yang ada."""
    with db.get_session() as session:
        rows = session.query(Barang.kategori).filter(
            Barang.kategori != None, Barang.aktif == True
        ).distinct().all()
        return sorted([r[0] for r in rows if r[0]])


@router.get("/{barang_id}", response_model=BarangOut)
def get_barang(barang_id: int, _: dict = Depends(get_current_user_payload)):
    """Detail satu barang by ID."""
    with db.get_session() as session:
        b = session.query(Barang).filter_by(id=barang_id).first()
        if not b:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
        return _barang_to_schema(b)


@router.post("", response_model=BarangOut, status_code=status.HTTP_201_CREATED)
def create_barang(body: BarangCreate, _: dict = Depends(require_admin)):
    """Tambah barang baru. Hanya admin."""
    with db.get_session() as session:
        # Auto-generate kode jika tidak diisi
        kode = body.kode
        if not kode:
            kode = generate_item_code(session)

        # Cek duplikat kode
        if session.query(Barang).filter_by(kode=kode).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Kode barang '{kode}' sudah digunakan",
            )

        # Cek duplikat nama
        if session.query(Barang).filter_by(nama=body.nama).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Nama barang '{body.nama}' sudah ada",
            )

        b = Barang(
            kode=kode,
            barcode=body.barcode,
            nama=body.nama,
            kategori=body.kategori,
            harga_beli=body.harga_beli,
            harga_jual=body.harga_jual,
            stok=body.stok,
            stok_min=body.stok_min,
            satuan=body.satuan,
            deskripsi=body.deskripsi,
            foto=body.foto,
        )
        session.add(b)
        session.flush()
        return _barang_to_schema(b)


@router.put("/{barang_id}", response_model=BarangOut)
def update_barang(
    barang_id: int,
    body: BarangUpdate,
    _: dict = Depends(require_admin),
):
    """Update data barang. Hanya admin."""
    with db.get_session() as session:
        b = session.query(Barang).filter_by(id=barang_id).first()
        if not b:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")

        if body.barcode is not None:
            b.barcode = body.barcode
        if body.nama is not None:
            b.nama = body.nama
        if body.kategori is not None:
            b.kategori = body.kategori
        if body.harga_beli is not None:
            b.harga_beli = body.harga_beli
        if body.harga_jual is not None:
            b.harga_jual = body.harga_jual
        if body.stok is not None:
            b.stok = body.stok
        if body.stok_min is not None:
            b.stok_min = body.stok_min
        if body.satuan is not None:
            b.satuan = body.satuan
        if body.deskripsi is not None:
            b.deskripsi = body.deskripsi
        if body.foto is not None:
            b.foto = body.foto
        if body.aktif is not None:
            b.aktif = body.aktif

        session.flush()
        return _barang_to_schema(b)


@router.post("/{barang_id}/foto", response_model=BarangOut)
def upload_foto_barang(
    barang_id: int,
    file: UploadFile = File(...),
    _: dict = Depends(require_admin),
):
    """Upload dan update foto produk untuk satu barang."""
    with db.get_session() as session:
        b = session.query(Barang).filter_by(id=barang_id).first()
        if not b:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")

        ext = Path(file.filename or "").suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format file tidak didukung (harus JPG, PNG, WEBP, atau BMP)"
            )

        clean_name = f"brg_{b.kode.lower()}_{uuid.uuid4().hex[:6]}{ext}"
        target_path = config.UPLOAD_PRODUK_DIR / clean_name
        try:
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            b.foto = f"uploads/produk/{clean_name}"
            session.flush()
            return _barang_to_schema(b)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal mengunggah foto: {e}"
            )


@router.delete("/{barang_id}", response_model=MessageResponse)
def deactivate_barang(barang_id: int, _: dict = Depends(require_admin)):
    """Nonaktifkan barang (soft delete). Hanya admin."""
    with db.get_session() as session:
        b = session.query(Barang).filter_by(id=barang_id).first()
        if not b:
            raise HTTPException(status_code=404, detail="Barang tidak ditemukan")
        b.aktif = False
        return MessageResponse(message=f"Barang '{b.nama}' berhasil dinonaktifkan")
