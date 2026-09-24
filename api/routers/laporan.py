"""
KasirKu API — Laporan Router
Endpoint: dashboard summary, laporan harian
"""

from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query

from database.db import db
from database.models import Transaksi, TransaksiDetail, Barang, Pengeluaran
from api.deps import get_current_user_payload
from api.schemas import DashboardSummaryOut

router = APIRouter(prefix="/api/laporan", tags=["laporan"])


@router.get("/dashboard", response_model=DashboardSummaryOut)
def dashboard_summary(_: dict = Depends(get_current_user_payload)):
    """
    Ringkasan dashboard:
    - Total penjualan & transaksi hari ini
    - Total penjualan & transaksi bulan ini
    - Total pengeluaran hari ini
    - Laba bersih hari ini
    - Jumlah barang stok menipis
    - Top 5 produk terlaris hari ini
    """
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    today_end = datetime(now.year, now.month, now.day, 23, 59, 59)
    month_start = datetime(now.year, now.month, 1, 0, 0, 0)

    with db.get_session() as session:
        # — Hari ini —
        trx_hari_ini = session.query(Transaksi).filter(
            Transaksi.tanggal >= today_start,
            Transaksi.tanggal <= today_end,
            Transaksi.status == "selesai",
        ).all()

        total_hari_ini = sum(t.total for t in trx_hari_ini)
        jumlah_hari_ini = len(trx_hari_ini)

        # — Bulan ini —
        trx_bulan = session.query(Transaksi).filter(
            Transaksi.tanggal >= month_start,
            Transaksi.status == "selesai",
        ).all()
        total_bulan = sum(t.total for t in trx_bulan)
        jumlah_bulan = len(trx_bulan)

        # — Pengeluaran hari ini —
        pengeluaran_hari = session.query(Pengeluaran).filter(
            Pengeluaran.tanggal >= today_start,
            Pengeluaran.tanggal <= today_end,
        ).all()
        total_pengeluaran = sum(p.nominal for p in pengeluaran_hari)

        laba_bersih = total_hari_ini - total_pengeluaran

        # — Stok menipis —
        stok_menipis = session.query(Barang).filter(
            Barang.aktif == True,
            Barang.stok <= Barang.stok_min,
        ).count()

        # — Top 5 produk hari ini —
        top_produk_raw: dict[str, dict] = {}
        for t in trx_hari_ini:
            for d in t.detail:
                key = d.nama_barang
                if key not in top_produk_raw:
                    top_produk_raw[key] = {"nama": key, "qty": 0, "total": 0.0}
                top_produk_raw[key]["qty"] += d.qty
                top_produk_raw[key]["total"] += d.subtotal

        top_produk = sorted(
            top_produk_raw.values(),
            key=lambda x: x["qty"],
            reverse=True,
        )[:5]

        return DashboardSummaryOut(
            total_penjualan_hari_ini=total_hari_ini,
            jumlah_transaksi_hari_ini=jumlah_hari_ini,
            total_penjualan_bulan_ini=total_bulan,
            jumlah_transaksi_bulan_ini=jumlah_bulan,
            total_pengeluaran_hari_ini=total_pengeluaran,
            laba_bersih_hari_ini=laba_bersih,
            stok_menipis_count=stok_menipis,
            top_produk=top_produk,
        )


@router.get("/harian")
def laporan_harian(
    tanggal: Optional[date] = Query(None, description="Format: YYYY-MM-DD. Default: hari ini"),
    _: dict = Depends(get_current_user_payload),
):
    """Laporan detail per tanggal."""
    target = tanggal or date.today()
    start = datetime(target.year, target.month, target.day, 0, 0, 0)
    end = datetime(target.year, target.month, target.day, 23, 59, 59)

    with db.get_session() as session:
        transaksi_list = session.query(Transaksi).filter(
            Transaksi.tanggal >= start,
            Transaksi.tanggal <= end,
            Transaksi.status == "selesai",
        ).order_by(Transaksi.tanggal).all()

        pengeluaran_list = session.query(Pengeluaran).filter(
            Pengeluaran.tanggal >= start,
            Pengeluaran.tanggal <= end,
        ).all()

        total_penjualan = sum(t.total for t in transaksi_list)
        total_pengeluaran = sum(p.nominal for p in pengeluaran_list)

        by_metode: dict[str, float] = {}
        for t in transaksi_list:
            by_metode[t.metode_bayar] = by_metode.get(t.metode_bayar, 0) + t.total

        return {
            "tanggal": str(target),
            "jumlah_transaksi": len(transaksi_list),
            "total_penjualan": total_penjualan,
            "total_pengeluaran": total_pengeluaran,
            "laba_bersih": total_penjualan - total_pengeluaran,
            "penjualan_per_metode": by_metode,
            "transaksi": [
                {
                    "no_invoice": t.no_invoice,
                    "waktu": t.tanggal.strftime("%H:%M"),
                    "kasir": t.kasir.username if t.kasir else "-",
                    "total": t.total,
                    "metode": t.metode_bayar,
                }
                for t in transaksi_list
            ],
            "pengeluaran": [
                {
                    "kategori": p.kategori,
                    "deskripsi": p.deskripsi,
                    "nominal": p.nominal,
                }
                for p in pengeluaran_list
            ],
        }
