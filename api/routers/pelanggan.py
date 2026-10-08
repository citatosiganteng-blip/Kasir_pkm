"""
KasirKu API — Pelanggan (Customer) Router
Endpoint: CRUD pelanggan untuk kasir dan admin
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import or_

from database.db import db
from database.models import Pelanggan
from api.deps import get_current_user_payload, require_admin
from api.schemas import PelangganOut, PelangganCreate, PelangganUpdate, MessageResponse
from utils.helpers import generate_customer_code

router = APIRouter(prefix="/api/pelanggan", tags=["pelanggan"])


def _pelanggan_out(p: Pelanggan) -> PelangganOut:
    return PelangganOut.model_validate(p)


@router.get("", response_model=List[PelangganOut])
def list_pelanggan(
    q: Optional[str] = Query(None, description="Cari nama/kode/telepon"),
    aktif_only: bool = Query(True),
    limit: int = Query(200, ge=1, le=500),
    _: dict = Depends(get_current_user_payload),
):
    """Daftar pelanggan dengan pencarian opsional."""
    with db.get_session() as session:
        query = session.query(Pelanggan)
        if aktif_only:
            query = query.filter(Pelanggan.aktif == True)
        if q:
            search = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    Pelanggan.nama.ilike(search),
                    Pelanggan.kode.ilike(search),
                    Pelanggan.telepon.ilike(search),
                    Pelanggan.email.ilike(search),
                )
            )
        rows = query.order_by(Pelanggan.nama.asc()).limit(limit).all()
        return [_pelanggan_out(p) for p in rows]


@router.get("/{pelanggan_id}", response_model=PelangganOut)
def get_pelanggan(pelanggan_id: int, _: dict = Depends(get_current_user_payload)):
    """Detail satu pelanggan."""
    with db.get_session() as session:
        p = session.query(Pelanggan).filter_by(id=pelanggan_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
        return _pelanggan_out(p)


@router.post("", response_model=PelangganOut, status_code=status.HTTP_201_CREATED)
def create_pelanggan(body: PelangganCreate, _: dict = Depends(get_current_user_payload)):
    """
    Tambah pelanggan baru.
    Kode otomatis di-generate jika tidak diberikan.
    """
    nama = body.nama.strip() if body.nama else ""
    if not nama:
        raise HTTPException(status_code=400, detail="Nama pelanggan wajib diisi")

    with db.get_session() as session:
        kode = body.kode.strip() if body.kode else None
        if not kode:
            kode = generate_customer_code(session)
        else:
            existing = session.query(Pelanggan).filter_by(kode=kode).first()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Kode pelanggan '{kode}' sudah digunakan"
                )

        p = Pelanggan(
            kode=kode,
            nama=nama,
            telepon=body.telepon.strip() if body.telepon else None,
            alamat=body.alamat.strip() if body.alamat else None,
            email=body.email.strip() if body.email else None,
            npwp=body.npwp.strip() if body.npwp else None,
        )
        session.add(p)
        session.flush()
        return _pelanggan_out(p)


@router.put("/{pelanggan_id}", response_model=PelangganOut)
def update_pelanggan(
    pelanggan_id: int,
    body: PelangganUpdate,
    _: dict = Depends(get_current_user_payload),
):
    """Update data pelanggan."""
    with db.get_session() as session:
        p = session.query(Pelanggan).filter_by(id=pelanggan_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")

        if body.nama is not None:
            if not body.nama.strip():
                raise HTTPException(status_code=400, detail="Nama pelanggan tidak boleh kosong")
            p.nama = body.nama.strip()

        if body.telepon is not None:
            p.telepon = body.telepon.strip() or None
        if body.alamat is not None:
            p.alamat = body.alamat.strip() or None
        if body.email is not None:
            p.email = body.email.strip() or None
        if body.npwp is not None:
            p.npwp = body.npwp.strip() or None
        if body.aktif is not None:
            p.aktif = body.aktif

        session.flush()
        return _pelanggan_out(p)


@router.delete("/{pelanggan_id}", response_model=MessageResponse)
def delete_pelanggan(
    pelanggan_id: int,
    _: dict = Depends(require_admin),
):
    """Soft-delete (nonaktifkan) pelanggan. Hanya admin."""
    with db.get_session() as session:
        p = session.query(Pelanggan).filter_by(id=pelanggan_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
        p.aktif = False
        session.flush()
        return MessageResponse(message=f"Pelanggan '{p.nama}' berhasil dinonaktifkan")

