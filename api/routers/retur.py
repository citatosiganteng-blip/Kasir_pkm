"""
KasirKu API — Retur Router
Endpoint: Retur Penjualan (Sales Return) & Retur Pembelian (Purchase Return)
Dilengkapi JWT authentication dan otorisasi role (require_admin untuk retur pembelian)
"""

from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query

from database.db import db
from database.models import (
    Barang, Transaksi, TransaksiDetail,
    Pembelian, PembelianDetail,
    ReturPenjualan, ReturPenjualanDetail,
    ReturPembelian, ReturPembelianDetail,
    Pengeluaran
)
from utils.helpers import (
    generate_retur_penjualan_number,
    generate_retur_pembelian_number
)
from api.deps import get_current_user_payload, get_current_user_id, require_admin
from api.schemas import (
    ReturPenjualanCreate, ReturPenjualanOut, ReturDetailOut,
    ReturPembelianCreate, ReturPembelianOut, ReturPembelianDetailOut
)

router = APIRouter(prefix="/api/retur", tags=["retur"])


def _retur_penjualan_to_schema(r: ReturPenjualan) -> ReturPenjualanOut:
    detail_list = [
        ReturDetailOut(
            id=d.id,
            barang_id=d.barang_id,
            kode_barang=d.kode_barang,
            nama_barang=d.nama_barang,
            qty=d.qty,
            harga_satuan=d.harga_satuan,
            subtotal=d.subtotal,
        )
        for d in r.detail
    ]
    return ReturPenjualanOut(
        id=r.id,
        no_retur=r.no_retur,
        transaksi_id=r.transaksi_id,
        no_invoice=r.no_invoice,
        tanggal=r.tanggal,
        total_retur=r.total_retur,
        alasan=r.alasan,
        metode_kembali=r.metode_kembali,
        user_id=r.user_id,
        detail=detail_list,
    )


def _retur_pembelian_to_schema(r: ReturPembelian) -> ReturPembelianOut:
    detail_list = [
        ReturPembelianDetailOut(
            id=d.id,
            barang_id=d.barang_id,
            kode_barang=d.kode_barang,
            nama_barang=d.nama_barang,
            qty=d.qty,
            harga_beli=d.harga_beli,
            subtotal=d.subtotal,
        )
        for d in r.detail
    ]
    return ReturPembelianOut(
        id=r.id,
        no_retur=r.no_retur,
        pembelian_id=r.pembelian_id,
        no_po=r.no_po,
        supplier_id=r.supplier_id,
        tanggal=r.tanggal,
        total_retur=r.total_retur,
        alasan=r.alasan,
        metode_kembali=r.metode_kembali,
        user_id=r.user_id,
        detail=detail_list,
    )


# ──────────────────────────────────────────────────────────────────────────────
# RETUR PENJUALAN (SALES RETURN)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/penjualan", response_model=ReturPenjualanOut, status_code=status.HTTP_201_CREATED)
def create_retur_penjualan(
    req: ReturPenjualanCreate,
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Proses pengembalian barang dari pembeli:
    - Memvalidasi qty retur <= sisa qty yang belum diretur
    - Auto restock: menambah stok barang kembali ke gudang
    - Jika metode 'cash', otomatis mencatat pengeluaran toko
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="Minimal satu barang harus ditentukan untuk retur")

    with db.get_session() as session:
        t = session.query(Transaksi).filter_by(id=req.transaksi_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Transaksi asal tidak ditemukan")
        if t.status == "void":
            raise HTTPException(status_code=400, detail="Transaksi sudah di-void, tidak bisa diretur")

        # Hitung barang yang sudah pernah diretur sebelumnya
        already_returned = {}
        for prev_ret in t.retur:
            for rd in prev_ret.detail:
                bid = rd.barang_id or rd.nama_barang
                already_returned[bid] = already_returned.get(bid, 0) + rd.qty

        # Map detail barang transaksi asal
        trx_detail_map = {}
        for d in t.detail:
            bid = d.barang_id or d.nama_barang
            trx_detail_map[bid] = d

        items_processed = []
        total_retur = 0.0

        for itm in req.items:
            bid = itm.barang_id
            if bid not in trx_detail_map:
                raise HTTPException(
                    status_code=400,
                    detail=f"Barang ID {bid} tidak ada dalam transaksi #{t.no_invoice}"
                )

            d = trx_detail_map[bid]
            prev_qty = already_returned.get(bid, 0)
            remaining_qty = max(0, d.qty - prev_qty)

            if itm.qty > remaining_qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Qty retur untuk '{d.nama_barang}' ({itm.qty}) melebihi sisa yang bisa diretur ({remaining_qty})"
                )

            subtotal = itm.qty * d.harga
            total_retur += subtotal
            items_processed.append({
                "barang_id": d.barang_id,
                "kode_barang": d.kode_barang,
                "nama_barang": d.nama_barang,
                "qty": itm.qty,
                "harga_satuan": d.harga,
                "subtotal": subtotal,
            })

            # Update already_returned accumulator
            already_returned[bid] = prev_qty + itm.qty

        no_retur = generate_retur_penjualan_number(session)

        retur_obj = ReturPenjualan(
            no_retur=no_retur,
            transaksi_id=t.id,
            no_invoice=t.no_invoice,
            total_retur=total_retur,
            alasan=req.alasan,
            metode_kembali=req.metode_kembali,
            user_id=current_user_id,
        )
        session.add(retur_obj)
        session.flush()

        for itm in items_processed:
            rd = ReturPenjualanDetail(
                retur_id=retur_obj.id,
                barang_id=itm["barang_id"],
                kode_barang=itm["kode_barang"],
                nama_barang=itm["nama_barang"],
                qty=itm["qty"],
                harga_satuan=itm["harga_satuan"],
                subtotal=itm["subtotal"],
            )
            session.add(rd)

            # Auto restock stok
            if itm["barang_id"]:
                brg = session.query(Barang).filter_by(id=itm["barang_id"]).first()
                if brg:
                    brg.stok += itm["qty"]

        # Jika refund kas, buat record pengeluaran
        if req.metode_kembali == "cash":
            session.add(Pengeluaran(
                kategori="Retur Penjualan",
                nominal=total_retur,
                deskripsi=f"Refund tunai retur {no_retur} untuk invoice {t.no_invoice}: {req.alasan}",
                user_id=current_user_id,
            ))

        session.flush()
        return _retur_penjualan_to_schema(retur_obj)


@router.get("/penjualan", response_model=List[ReturPenjualanOut])
def list_retur_penjualan(
    tanggal_mulai: Optional[date] = Query(None),
    tanggal_selesai: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: dict = Depends(get_current_user_payload),
):
    """Daftar riwayat retur penjualan."""
    with db.get_session() as session:
        q = session.query(ReturPenjualan)
        if tanggal_mulai:
            start_dt = datetime.combine(tanggal_mulai, datetime.min.time())
            q = q.filter(ReturPenjualan.tanggal >= start_dt)
        if tanggal_selesai:
            end_dt = datetime.combine(tanggal_selesai, datetime.max.time())
            q = q.filter(ReturPenjualan.tanggal <= end_dt)

        items = q.order_by(ReturPenjualan.tanggal.desc()).offset(offset).limit(limit).all()
        return [_retur_penjualan_to_schema(r) for r in items]


@router.get("/penjualan/{retur_id}", response_model=ReturPenjualanOut)
def get_retur_penjualan(retur_id: int, _: dict = Depends(get_current_user_payload)):
    """Detail satu retur penjualan."""
    with db.get_session() as session:
        r = session.query(ReturPenjualan).filter_by(id=retur_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Data retur penjualan tidak ditemukan")
        return _retur_penjualan_to_schema(r)


# ──────────────────────────────────────────────────────────────────────────────
# RETUR PEMBELIAN (PURCHASE RETURN TO SUPPLIER)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/pembelian", response_model=ReturPembelianOut, status_code=status.HTTP_201_CREATED)
def create_retur_pembelian(
    req: ReturPembelianCreate,
    current_user_id: int = Depends(get_current_user_id),
    _: dict = Depends(require_admin),
):
    """
    Proses retur pembelian ke supplier (Hanya Admin):
    - Memvalidasi stok toko mencukupi untuk dikembalikan
    - Mengurangi stok barang (Barang.stok -= qty)
    - Jika metode 'potong_hutang' & status 'tempo', memotong sisa hutang PO
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="Minimal satu barang harus ditentukan untuk retur")

    with db.get_session() as session:
        p = session.query(Pembelian).filter_by(id=req.pembelian_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Faktur pembelian tidak ditemukan")

        already_returned = {}
        for prev_ret in p.retur:
            for rd in prev_ret.detail:
                bid = rd.barang_id or rd.nama_barang
                already_returned[bid] = already_returned.get(bid, 0) + rd.qty

        po_detail_map = {}
        for d in p.detail:
            bid = d.barang_id or d.nama_barang
            po_detail_map[bid] = d

        items_processed = []
        total_retur = 0.0

        for itm in req.items:
            bid = itm.barang_id
            if bid not in po_detail_map:
                raise HTTPException(
                    status_code=400,
                    detail=f"Barang ID {bid} tidak ada dalam faktur pembelian #{p.no_po}"
                )

            d = po_detail_map[bid]
            prev_qty = already_returned.get(bid, 0)
            remaining_po = max(0, d.qty - prev_qty)

            if itm.qty > remaining_po:
                raise HTTPException(
                    status_code=400,
                    detail=f"Qty retur untuk '{d.nama_barang}' ({itm.qty}) melebihi sisa PO ({remaining_po})"
                )

            # Cek stok fisik di toko
            brg = session.query(Barang).filter_by(id=itm.barang_id).first() if itm.barang_id else None
            if brg and brg.stok < itm.qty:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stok barang '{d.nama_barang}' di toko ({brg.stok}) tidak mencukupi untuk retur {itm.qty}"
                )

            subtotal = itm.qty * d.harga_beli
            total_retur += subtotal
            items_processed.append({
                "barang_id": d.barang_id,
                "kode_barang": d.kode_barang,
                "nama_barang": d.nama_barang,
                "qty": itm.qty,
                "harga_beli": d.harga_beli,
                "subtotal": subtotal,
            })

            already_returned[bid] = prev_qty + itm.qty

        no_retur = generate_retur_pembelian_number(session)

        retur_obj = ReturPembelian(
            no_retur=no_retur,
            pembelian_id=p.id,
            no_po=p.no_po,
            supplier_id=p.supplier_id,
            total_retur=total_retur,
            alasan=req.alasan,
            metode_kembali=req.metode_kembali,
            user_id=current_user_id,
        )
        session.add(retur_obj)
        session.flush()

        for itm in items_processed:
            rd = ReturPembelianDetail(
                retur_id=retur_obj.id,
                barang_id=itm["barang_id"],
                kode_barang=itm["kode_barang"],
                nama_barang=itm["nama_barang"],
                qty=itm["qty"],
                harga_beli=itm["harga_beli"],
                subtotal=itm["subtotal"],
            )
            session.add(rd)

            # Kurangi stok barang karena dikembalikan ke vendor
            if itm["barang_id"]:
                brg = session.query(Barang).filter_by(id=itm["barang_id"]).first()
                if brg:
                    brg.stok = max(0, brg.stok - itm["qty"])

        # Jika potong hutang dan status tempo, kurangi total tempo
        if req.metode_kembali == "potong_hutang" and p.status_bayar == "tempo":
            p.total = max(0.0, p.total - total_retur)
            if p.total <= 0:
                p.status_bayar = "lunas"

        session.flush()
        return _retur_pembelian_to_schema(retur_obj)


@router.get("/pembelian", response_model=List[ReturPembelianOut])
def list_retur_pembelian(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: dict = Depends(require_admin),
):
    """Daftar riwayat retur pembelian (Hanya Admin)."""
    with db.get_session() as session:
        items = (
            session.query(ReturPembelian)
            .order_by(ReturPembelian.tanggal.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_retur_pembelian_to_schema(r) for r in items]
