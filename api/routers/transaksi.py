"""
KasirKu API — Transaksi Router
Endpoint: buat transaksi baru (kasir Android), riwayat, detail
"""

from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query

from database.db import db
from database.models import Barang, Transaksi, TransaksiDetail, Pelanggan
from utils.helpers import generate_invoice_number
from api.deps import get_current_user_payload, get_current_user_id, require_admin
from api.schemas import TransaksiCreate, TransaksiOut, TransaksiDetailOut

router = APIRouter(prefix="/api/transaksi", tags=["transaksi"])


def _transaksi_to_schema(t: Transaksi) -> TransaksiOut:
    kasir_username = t.kasir.username if t.kasir else None
    detail_list = [
        TransaksiDetailOut(
            id=d.id,
            barang_id=d.barang_id,
            nama_barang=d.nama_barang,
            kode_barang=d.kode_barang,
            qty=d.qty,
            harga=d.harga,
            diskon=d.diskon,
            subtotal=d.subtotal,
        )
        for d in (t.detail or [])
    ]
    return TransaksiOut(
        id=t.id,
        no_invoice=t.no_invoice,
        tanggal=t.tanggal,
        kasir_id=t.kasir_id,
        kasir_username=kasir_username,
        pelanggan_id=t.pelanggan_id,
        nama_pelanggan=t.nama_pelanggan,
        telepon_pelanggan=t.telepon_pelanggan,
        alamat_pelanggan=t.alamat_pelanggan,
        npwp_pelanggan=t.npwp_pelanggan,
        total=t.total,
        diskon_total=t.diskon_total,
        bayar=t.bayar,
        kembalian=t.kembalian,
        metode_bayar=t.metode_bayar,
        status=t.status,
        status_bayar=t.status_bayar or "lunas",
        jatuh_tempo=t.jatuh_tempo,
        dpp=t.dpp or 0.0,
        ppn_persen=t.ppn_persen or 0.0,
        ppn_nominal=t.ppn_nominal or 0.0,
        pph_persen=t.pph_persen or 0.0,
        pph_nominal=t.pph_nominal or 0.0,
        no_faktur_pajak=t.no_faktur_pajak,
        catatan=t.catatan,
        detail=detail_list,
    )



@router.post("", response_model=TransaksiOut, status_code=status.HTTP_201_CREATED)
def create_transaksi(
    body: TransaksiCreate,
    user_id: int = Depends(get_current_user_id),
):
    """
    Buat transaksi baru dari kasir Android/web.
    Otomatis validasi stok, generate nomor invoice, kurangi stok.
    """
    if not body.items:
        raise HTTPException(status_code=400, detail="Keranjang tidak boleh kosong")

    with db.get_session() as session:
        # Hitung total & validasi stok
        total = 0.0
        diskon_total = 0.0
        stok_issues = []

        for item in body.items:
            diskon_amount = item.harga * (item.diskon / 100)
            subtotal = (item.harga - diskon_amount) * item.qty
            total += subtotal
            diskon_total += diskon_amount * item.qty

            if item.barang_id:
                b = session.query(Barang).filter_by(id=item.barang_id).first()
                if not b:
                    stok_issues.append(f"Barang ID {item.barang_id} tidak ditemukan")
                elif b.stok < item.qty:
                    stok_issues.append(
                        f"Stok '{b.nama}' tidak cukup (tersedia: {b.stok}, diminta: {item.qty})"
                    )

        if stok_issues:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Stok tidak mencukupi", "errors": stok_issues},
            )

        kembalian = max(0.0, body.bayar - total)
        no_invoice = generate_invoice_number(session)

        # Rincian pelanggan
        nama_pelanggan = body.nama_pelanggan
        telepon_pelanggan = body.telepon_pelanggan
        alamat_pelanggan = body.alamat_pelanggan
        npwp_pelanggan = body.npwp_pelanggan

        if body.pelanggan_id:
            cust = session.query(Pelanggan).filter_by(id=body.pelanggan_id).first()
            if cust:
                nama_pelanggan = nama_pelanggan or cust.nama
                telepon_pelanggan = telepon_pelanggan or cust.telepon
                alamat_pelanggan = alamat_pelanggan or cust.alamat
                npwp_pelanggan = npwp_pelanggan or cust.npwp

        transaksi = Transaksi(
            no_invoice=no_invoice,
            kasir_id=user_id,
            pelanggan_id=body.pelanggan_id,
            nama_pelanggan=nama_pelanggan,
            telepon_pelanggan=telepon_pelanggan,
            alamat_pelanggan=alamat_pelanggan,
            npwp_pelanggan=npwp_pelanggan,
            total=total,
            diskon_total=diskon_total,
            bayar=body.bayar,
            kembalian=kembalian,
            metode_bayar=body.metode_bayar,
            catatan=body.catatan,
            status="selesai",
            status_bayar=body.status_bayar or "lunas",
            jatuh_tempo=body.jatuh_tempo,
            dpp=body.dpp or 0.0,
            ppn_persen=body.ppn_persen or 0.0,
            ppn_nominal=body.ppn_nominal or 0.0,
            pph_persen=body.pph_persen or 0.0,
            pph_nominal=body.pph_nominal or 0.0,
            no_faktur_pajak=body.no_faktur_pajak,
        )
        session.add(transaksi)
        session.flush()  # dapatkan transaksi.id

        for item in body.items:
            diskon_amount = item.harga * (item.diskon / 100)
            subtotal = (item.harga - diskon_amount) * item.qty

            detail = TransaksiDetail(
                transaksi_id=transaksi.id,
                barang_id=item.barang_id,
                nama_barang=item.nama_barang,
                kode_barang=item.kode_barang,
                qty=item.qty,
                harga=item.harga,
                diskon=item.diskon,
                subtotal=subtotal,
            )
            session.add(detail)

            # Kurangi stok
            if item.barang_id:
                b = session.query(Barang).filter_by(id=item.barang_id).first()
                if b:
                    b.stok -= item.qty

        session.flush()
        return _transaksi_to_schema(transaksi)


@router.get("", response_model=List[TransaksiOut])
def list_transaksi(
    tanggal_mulai: Optional[date] = Query(None),
    tanggal_selesai: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: dict = Depends(get_current_user_payload),
):
    """Riwayat transaksi dengan filter tanggal opsional."""
    with db.get_session() as session:
        q = session.query(Transaksi)
        if tanggal_mulai:
            start_dt = datetime.combine(tanggal_mulai, datetime.min.time())
            q = q.filter(Transaksi.tanggal >= start_dt)
        if tanggal_selesai:
            end_dt = datetime.combine(tanggal_selesai, datetime.max.time())
            q = q.filter(Transaksi.tanggal <= end_dt)
        if status:
            q = q.filter(Transaksi.status == status)

        items = q.order_by(Transaksi.tanggal.desc()).offset(offset).limit(limit).all()
        return [_transaksi_to_schema(t) for t in items]


@router.get("/{transaksi_id}", response_model=TransaksiOut)
def get_transaksi(transaksi_id: int, _: dict = Depends(get_current_user_payload)):
    """Detail satu transaksi lengkap dengan item-itemnya."""
    with db.get_session() as session:
        t = session.query(Transaksi).filter_by(id=transaksi_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
        return _transaksi_to_schema(t)


@router.post("/{transaksi_id}/void", response_model=TransaksiOut)
def void_transaksi(
    transaksi_id: int,
    _: dict = Depends(require_admin),
):
    """
    Void / batalkan transaksi. Stok dikembalikan.
    """
    with db.get_session() as session:
        t = session.query(Transaksi).filter_by(id=transaksi_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
        if t.status == "void":
            raise HTTPException(status_code=400, detail="Transaksi sudah di-void sebelumnya")

        t.status = "void"

        # Kembalikan stok
        for detail in t.detail:
            if detail.barang_id:
                b = session.query(Barang).filter_by(id=detail.barang_id).first()
                if b:
                    b.stok += detail.qty

        session.flush()
        return _transaksi_to_schema(t)
