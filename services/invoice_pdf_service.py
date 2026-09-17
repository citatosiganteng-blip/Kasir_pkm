"""
KasirKu Invoice & PDF Service
Menyediakan pembuatan Faktur Penjualan A4, Faktur Pembelian (PO), Faktur Pajak,
dan ekspor laporan pajak ke Excel & PDF.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from database.db import db
from database.models import Transaksi, Pembelian, ReturPenjualan, ReturPembelian
from utils.helpers import format_rupiah, format_tanggal, format_datetime, terbilang
import config


class InvoicePdfService:
    """Service untuk render dan cetak Faktur A4 / PDF"""

    @classmethod
    def get_store_info(cls) -> dict:
        """Ambil data toko & pengaturan perpajakan dari database"""
        return {
            "name": db.get_setting("store_name", config._STORE_NAME_DEFAULT),
            "address": db.get_setting("store_address", config._STORE_ADDRESS_DEFAULT),
            "phone": db.get_setting("store_phone", config._STORE_PHONE_DEFAULT),
            "tagline": db.get_setting("store_tagline", config._STORE_TAGLINE_DEFAULT),
            "is_pkp": db.get_setting("tax_is_pkp", "0") == "1",
            "npwp": db.get_setting("tax_npwp", "-"),
            "nama_pkp": db.get_setting("tax_nama_pkp", ""),
            "bank_name": db.get_setting("store_bank_name", "BCA"),
            "bank_account": db.get_setting("store_bank_account", "-"),
            "bank_holder": db.get_setting("store_bank_holder", "-"),
        }

    @classmethod
    def generate_sales_invoice_html(cls, transaksi: Transaksi, store_info: dict = None) -> str:
        """Render template HTML Faktur Penjualan (A4) komersial & pajak"""
        store = store_info or cls.get_store_info()

        # Pelanggan
        customer_name = transaksi.nama_pelanggan or (transaksi.pelanggan.nama if transaksi.pelanggan else "Pelanggan Umum")
        customer_phone = transaksi.telepon_pelanggan or (transaksi.pelanggan.telepon if transaksi.pelanggan else "-")
        customer_addr = transaksi.alamat_pelanggan or (transaksi.pelanggan.alamat if transaksi.pelanggan else "-")
        customer_npwp = transaksi.npwp_pelanggan or (transaksi.pelanggan.npwp if transaksi.pelanggan else "-")

        tgl_trx = format_datetime(transaksi.tanggal)
        jatuh_tempo_str = format_tanggal(transaksi.jatuh_tempo) if transaksi.jatuh_tempo else "Tunai / Langsung"
        status_bayar_badge = (
            '<span style="background:#10B981; color:#fff; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">LUNAS</span>'
            if (transaksi.status_bayar or "lunas") == "lunas"
            else '<span style="background:#F59E0B; color:#fff; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">TEMPO / PIUTANG</span>'
        )

        dpp_val = transaksi.dpp if (transaksi.dpp and transaksi.dpp > 0) else transaksi.total
        ppn_val = transaksi.ppn_nominal or 0
        pph_val = transaksi.pph_nominal or 0

        # Baris barang
        item_rows = []
        for i, item in enumerate(transaksi.detail, 1):
            disc_text = f"{item.diskon:.0f}%" if item.diskon > 0 else "-"
            item_rows.append(f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px; text-align: center; color:#64748B;">{i}</td>
                <td style="padding: 8px; color:#1E293B; font-weight:600;">{item.nama_barang}</td>
                <td style="padding: 8px; text-align: center; color:#475569;">{item.kode_barang or '-'}</td>
                <td style="padding: 8px; text-align: center; color:#1E293B;">{item.qty}</td>
                <td style="padding: 8px; text-align: right; color:#475569;">{format_rupiah(item.harga)}</td>
                <td style="padding: 8px; text-align: center; color:#64748B;">{disc_text}</td>
                <td style="padding: 8px; text-align: right; color:#1E293B; font-weight:600;">{format_rupiah(item.subtotal)}</td>
            </tr>
            """)
        items_html = "".join(item_rows)

        terbilang_str = terbilang(transaksi.total)
        kasir_name = transaksi.kasir.nama_lengkap or transaksi.kasir.username if transaksi.kasir else "Kasir"

        # Tampilkan faktur pajak jika PKP atau ada nomor faktur pajak
        tax_info_box = ""
        if store["is_pkp"] or transaksi.no_faktur_pajak:
            nsfp = transaksi.no_faktur_pajak or "-"
            tax_info_box = f"""
            <div style="margin-top: 10px; padding: 8px 12px; background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 6px; font-size: 11px;">
                <b>🏛️ INFORMASI FAKTUR PAJAK / PKP:</b><br/>
                No. Seri Faktur Pajak: <b>{nsfp}</b> | NPWP Penjual: <b>{store['npwp']}</b> | NPWP Pembeli: <b>{customer_npwp}</b>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Faktur Penjualan - {transaksi.no_invoice}</title>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #1E293B;
                    margin: 0;
                    padding: 20px;
                    font-size: 12px;
                    line-height: 1.4;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .header-tbl td {{
                    vertical-align: top;
                }}
                .inv-title {{
                    font-size: 22px;
                    font-weight: 800;
                    color: #1E3A8A;
                    letter-spacing: 0.5px;
                }}
                .items-table {{
                    margin-top: 16px;
                    margin-bottom: 16px;
                    border: 1px solid #CBD5E1;
                }}
                .items-table th {{
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    font-weight: 700;
                    padding: 9px 8px;
                    font-size: 11px;
                    text-align: left;
                }}
                .summary-table td {{
                    padding: 5px 8px;
                }}
            </style>
        </head>
        <body>
            <!-- KOP TOKO & INFO FAKTUR -->
            <table class="header-tbl" style="margin-bottom: 16px;">
                <tr>
                    <td style="width: 58%;">
                        <div style="font-size: 20px; font-weight: 800; color: #0F172A;">{store['name']}</div>
                        <div style="color: #475569; font-size: 12px; margin-top: 3px;">{store['address']}</div>
                        <div style="color: #475569; font-size: 12px;">Telp: {store['phone']}</div>
                        {f'<div style="color: #475569; font-size: 12px;">NPWP: {store["npwp"]}</div>' if store['is_pkp'] else ''}
                    </td>
                    <td style="width: 42%; text-align: right;">
                        <div class="inv-title">FAKTUR PENJUALAN</div>
                        <div style="font-size: 13px; font-weight: 700; color: #3B82F6; margin-top: 4px;">#{transaksi.no_invoice}</div>
                        <div style="margin-top: 4px;">Status: {status_bayar_badge}</div>
                    </td>
                </tr>
            </table>

            <hr style="border: none; border-top: 2px solid #E2E8F0; margin-bottom: 14px;" />

            <!-- INFO PELANGGAN & DETAIL TRANSAKSI -->
            <table style="margin-bottom: 14px;">
                <tr>
                    <td style="width: 50%; vertical-align: top; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
                        <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Kepada Yth:</div>
                        <div style="font-size: 14px; font-weight: 700; color: #0F172A; margin-top: 2px;">{customer_name}</div>
                        <div style="color: #475569; font-size: 11px; margin-top: 2px;">Alamat: {customer_addr}</div>
                        <div style="color: #475569; font-size: 11px;">Telp: {customer_phone}</div>
                        <div style="color: #475569; font-size: 11px;">NPWP: {customer_npwp}</div>
                    </td>
                    <td style="width: 4%;"></td>
                    <td style="width: 46%; vertical-align: top; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
                        <table style="width: 100%; font-size: 11px;">
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Tanggal Faktur</td>
                                <td style="text-align: right; font-weight: 600;">{tgl_trx}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Jatuh Tempo</td>
                                <td style="text-align: right; font-weight: 600; color:#DC2626;">{jatuh_tempo_str}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Metode Bayar</td>
                                <td style="text-align: right; font-weight: 600;">{transaksi.metode_bayar.upper()}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Kasir / Sales</td>
                                <td style="text-align: right; font-weight: 600;">{kasir_name}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            {tax_info_box}

            <!-- TABEL DAFTAR BARANG -->
            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width: 5%; text-align: center;">No</th>
                        <th style="width: 40%;">Nama Barang / Jasa</th>
                        <th style="width: 15%; text-align: center;">Kode</th>
                        <th style="width: 8%; text-align: center;">Qty</th>
                        <th style="width: 14%; text-align: right;">Harga Satuan</th>
                        <th style="width: 8%; text-align: center;">Disc</th>
                        <th style="width: 15%; text-align: right;">Subtotal (DPP)</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <!-- BAGIAN TERBILANG & RINGKASAN TOTAL -->
            <table style="margin-top: 10px;">
                <tr>
                    <td style="width: 55%; vertical-align: top;">
                        <div style="background: #F1F5F9; border-left: 4px solid #3B82F6; padding: 10px 14px; border-radius: 4px;">
                            <div style="font-size: 11px; font-weight: 700; color: #475569;">TERBILANG:</div>
                            <div style="font-style: italic; font-weight: 600; color: #1E293B; margin-top: 2px; font-size: 12px;">"{terbilang_str}"</div>
                        </div>

                        <div style="margin-top: 14px; font-size: 11px; color: #475569; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 10px; border-radius: 6px;">
                            <b>💳 Pembayaran Ditransfer Ke:</b><br/>
                            Bank: <b>{store['bank_name']}</b> | Rekening: <b>{store['bank_account']}</b><br/>
                            Atas Nama: <b>{store['bank_holder']}</b>
                        </div>

                        {f'<div style="margin-top: 8px; font-size: 11px; color: #64748B;">Catatan: {transaksi.catatan}</div>' if transaksi.catatan else ''}
                    </td>
                    <td style="width: 5%;"></td>
                    <td style="width: 40%; vertical-align: top;">
                        <table class="summary-table" style="font-size: 12px; width: 100%;">
                            <tr>
                                <td style="color: #64748B;">Subtotal (DPP):</td>
                                <td style="text-align: right; font-weight: 600;">{format_rupiah(dpp_val)}</td>
                            </tr>
                            {f'''<tr>
                                <td style="color: #64748B;">Diskon Transaksi:</td>
                                <td style="text-align: right; color:#DC2626;">-{format_rupiah(transaksi.diskon_total)}</td>
                            </tr>''' if transaksi.diskon_total > 0 else ''}
                            {f'''<tr>
                                <td style="color: #64748B;">PPN ({transaksi.ppn_persen:.0f}%):</td>
                                <td style="text-align: right; font-weight: 600;">{format_rupiah(ppn_val)}</td>
                            </tr>''' if ppn_val > 0 else ''}
                            {f'''<tr>
                                <td style="color: #64748B;">PPh ({transaksi.pph_persen:.1f}%):</td>
                                <td style="text-align: right; color:#DC2626;">-{format_rupiah(pph_val)}</td>
                            </tr>''' if pph_val > 0 else ''}
                            <tr style="border-top: 2px solid #0F172A; background: #EFF6FF;">
                                <td style="font-weight: 800; font-size: 14px; color: #1E3A8A; padding: 8px;">TOTAL AKHIR:</td>
                                <td style="text-align: right; font-weight: 800; font-size: 15px; color: #1D4ED8; padding: 8px;">{format_rupiah(transaksi.total)}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B;">Jumlah Dibayar:</td>
                                <td style="text-align: right; font-weight: 600;">{format_rupiah(transaksi.bayar)}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B;">Kembalian / Sisa:</td>
                                <td style="text-align: right; font-weight: 600;">{format_rupiah(transaksi.kembalian)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- TANDA TANGAN -->
            <table style="margin-top: 40px; text-align: center; font-size: 11px;">
                <tr>
                    <td style="width: 35%;">
                        <div>Tanda Terima / Pembeli</div>
                        <div style="height: 60px;"></div>
                        <div style="font-weight: 700; border-top: 1px dotted #94A3B8; display: inline-block; padding-top: 4px; min-width: 140px;">
                            ( {customer_name} )
                        </div>
                    </td>
                    <td style="width: 30%;"></td>
                    <td style="width: 35%;">
                        <div>Hormat Kami,</div>
                        <div style="font-weight: 600; color: #64748B;">{store['name']}</div>
                        <div style="height: 44px;"></div>
                        <div style="font-weight: 700; border-top: 1px dotted #94A3B8; display: inline-block; padding-top: 4px; min-width: 140px;">
                            ( {kasir_name} )
                        </div>
                    </td>
                </tr>
            </table>

            <div style="text-align: center; margin-top: 30px; font-size: 10px; color: #94A3B8;">
                {store['tagline']} — Dokumen ini dicetak otomatis dari {config.APP_NAME} POS
            </div>
        </body>
        </html>
        """
        return html

    @classmethod
    def generate_purchase_order_html(cls, pembelian: Pembelian, store_info: dict = None) -> str:
        """Render template HTML Faktur Pembelian / Purchase Order (PO A4)"""
        store = store_info or cls.get_store_info()

        supplier_name = pembelian.supplier.nama if pembelian.supplier else "Supplier Umum"
        supplier_kontak = pembelian.supplier.kontak if pembelian.supplier else "-"
        supplier_phone = pembelian.supplier.telepon if pembelian.supplier else "-"
        supplier_addr = pembelian.supplier.alamat if pembelian.supplier else "-"
        supplier_npwp = pembelian.supplier.npwp if pembelian.supplier else "-"

        tgl_po = format_datetime(pembelian.tanggal)
        jatuh_tempo_str = format_tanggal(pembelian.jatuh_tempo) if pembelian.jatuh_tempo else "Tunai"

        status_bayar_badge = (
            '<span style="background:#10B981; color:#fff; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">LUNAS</span>'
            if pembelian.status_bayar == "lunas"
            else '<span style="background:#EF4444; color:#fff; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">TEMPO / HUTANG</span>'
        )

        item_rows = []
        for i, item in enumerate(pembelian.detail, 1):
            item_rows.append(f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px; text-align: center; color:#64748B;">{i}</td>
                <td style="padding: 8px; color:#1E293B; font-weight:600;">{item.nama_barang}</td>
                <td style="padding: 8px; text-align: center; color:#475569;">{item.kode_barang or '-'}</td>
                <td style="padding: 8px; text-align: center; color:#1E293B; font-weight:600;">{item.qty}</td>
                <td style="padding: 8px; text-align: right; color:#475569;">{format_rupiah(item.harga_beli)}</td>
                <td style="padding: 8px; text-align: right; color:#1E293B; font-weight:600;">{format_rupiah(item.subtotal)}</td>
            </tr>
            """)
        items_html = "".join(item_rows)

        user_name = pembelian.user.nama_lengkap or pembelian.user.username if pembelian.user else "Admin"
        terbilang_str = terbilang(pembelian.total)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Faktur Pembelian - {pembelian.no_po}</title>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #1E293B;
                    margin: 0;
                    padding: 20px;
                    font-size: 12px;
                    line-height: 1.4;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .header-tbl td {{
                    vertical-align: top;
                }}
                .inv-title {{
                    font-size: 22px;
                    font-weight: 800;
                    color: #047857;
                    letter-spacing: 0.5px;
                }}
                .items-table {{
                    margin-top: 16px;
                    margin-bottom: 16px;
                    border: 1px solid #CBD5E1;
                }}
                .items-table th {{
                    background-color: #047857;
                    color: #FFFFFF;
                    font-weight: 700;
                    padding: 9px 8px;
                    font-size: 11px;
                    text-align: left;
                }}
                .summary-table td {{
                    padding: 5px 8px;
                }}
            </style>
        </head>
        <body>
            <!-- KOP TOKO & INFO PO -->
            <table class="header-tbl" style="margin-bottom: 16px;">
                <tr>
                    <td style="width: 58%;">
                        <div style="font-size: 20px; font-weight: 800; color: #0F172A;">{store['name']}</div>
                        <div style="color: #475569; font-size: 12px; margin-top: 3px;">{store['address']}</div>
                        <div style="color: #475569; font-size: 12px;">Telp: {store['phone']}</div>
                    </td>
                    <td style="width: 42%; text-align: right;">
                        <div class="inv-title">FAKTUR PEMBELIAN / PO</div>
                        <div style="font-size: 13px; font-weight: 700; color: #059669; margin-top: 4px;">No PO: #{pembelian.no_po}</div>
                        <div style="font-size: 12px; color: #64748B;">No Faktur Vendor: <b>{pembelian.no_faktur}</b></div>
                        <div style="margin-top: 4px;">Status: {status_bayar_badge}</div>
                    </td>
                </tr>
            </table>

            <hr style="border: none; border-top: 2px solid #E2E8F0; margin-bottom: 14px;" />

            <!-- INFO VENDOR & DETAIL PO -->
            <table style="margin-bottom: 14px;">
                <tr>
                    <td style="width: 50%; vertical-align: top; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
                        <div style="font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase;">Vendor / Supplier:</div>
                        <div style="font-size: 14px; font-weight: 700; color: #0F172A; margin-top: 2px;">{supplier_name}</div>
                        <div style="color: #475569; font-size: 11px; margin-top: 2px;">Kontak: {supplier_kontak} ({supplier_phone})</div>
                        <div style="color: #475569; font-size: 11px;">Alamat: {supplier_addr}</div>
                        <div style="color: #475569; font-size: 11px;">NPWP: {supplier_npwp}</div>
                    </td>
                    <td style="width: 4%;"></td>
                    <td style="width: 46%; vertical-align: top; background: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
                        <table style="width: 100%; font-size: 11px;">
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Tanggal Masuk</td>
                                <td style="text-align: right; font-weight: 600;">{tgl_po}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Jatuh Tempo</td>
                                <td style="text-align: right; font-weight: 600; color:#DC2626;">{jatuh_tempo_str}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Metode Pembayaran</td>
                                <td style="text-align: right; font-weight: 600;">{pembelian.metode_bayar.upper()}</td>
                            </tr>
                            <tr>
                                <td style="color: #64748B; padding: 2px 0;">Dibuat Oleh</td>
                                <td style="text-align: right; font-weight: 600;">{user_name}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- TABEL BARANG MASUK -->
            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width: 5%; text-align: center;">No</th>
                        <th style="width: 45%;">Nama Barang</th>
                        <th style="width: 15%; text-align: center;">Kode</th>
                        <th style="width: 10%; text-align: center;">Qty Masuk</th>
                        <th style="width: 12%; text-align: right;">Harga Beli</th>
                        <th style="width: 13%; text-align: right;">Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <!-- RINGKASAN & PAJAK MASUKAN -->
            <table style="margin-top: 10px;">
                <tr>
                    <td style="width: 55%; vertical-align: top;">
                        <div style="background: #F1F5F9; border-left: 4px solid #10B981; padding: 10px 14px; border-radius: 4px;">
                            <div style="font-size: 11px; font-weight: 700; color: #475569;">TERBILANG:</div>
                            <div style="font-style: italic; font-weight: 600; color: #1E293B; margin-top: 2px; font-size: 12px;">"{terbilang_str}"</div>
                        </div>
                        {f'<div style="margin-top: 10px; font-size: 11px; color: #64748B;">Catatan: {pembelian.catatan}</div>' if pembelian.catatan else ''}
                    </td>
                    <td style="width: 5%;"></td>
                    <td style="width: 40%; vertical-align: top;">
                        <table class="summary-table" style="font-size: 12px; width: 100%;">
                            <tr>
                                <td style="color: #64748B;">DPP Pembelian:</td>
                                <td style="text-align: right; font-weight: 600;">{format_rupiah(pembelian.dpp or pembelian.subtotal)}</td>
                            </tr>
                            {f'''<tr>
                                <td style="color: #64748B;">PPN Masukan ({pembelian.ppn_persen:.0f}%):</td>
                                <td style="text-align: right; font-weight: 600;">{format_rupiah(pembelian.ppn_nominal)}</td>
                            </tr>''' if (pembelian.ppn_nominal or 0) > 0 else ''}
                            {f'''<tr>
                                <td style="color: #64748B;">PPh ({pembelian.pph_persen:.1f}%):</td>
                                <td style="text-align: right; color:#DC2626;">-{format_rupiah(pembelian.pph_nominal)}</td>
                            </tr>''' if (pembelian.pph_nominal or 0) > 0 else ''}
                            <tr style="border-top: 2px solid #0F172A; background: #ECFDF5;">
                                <td style="font-weight: 800; font-size: 14px; color: #065F46; padding: 8px;">TOTAL PEMBELIAN:</td>
                                <td style="text-align: right; font-weight: 800; font-size: 15px; color: #047857; padding: 8px;">{format_rupiah(pembelian.total)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- TANDA TANGAN -->
            <table style="margin-top: 40px; text-align: center; font-size: 11px;">
                <tr>
                    <td style="width: 35%;">
                        <div>Pengirim / Supplier</div>
                        <div style="height: 60px;"></div>
                        <div style="font-weight: 700; border-top: 1px dotted #94A3B8; display: inline-block; padding-top: 4px; min-width: 140px;">
                            ( {supplier_name} )
                        </div>
                    </td>
                    <td style="width: 30%;"></td>
                    <td style="width: 35%;">
                        <div>Diterima Oleh (Gudang/Admin)</div>
                        <div style="height: 60px;"></div>
                        <div style="font-weight: 700; border-top: 1px dotted #94A3B8; display: inline-block; padding-top: 4px; min-width: 140px;">
                            ( {user_name} )
                        </div>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html

    @classmethod
    def generate_sales_return_html(cls, retur: ReturPenjualan, store_info: dict = None) -> str:
        """Render template HTML Nota Retur Penjualan (A4) formal"""
        store = store_info or cls.get_store_info()
        trx = retur.transaksi

        # Pelanggan
        customer_name = "-"
        customer_phone = "-"
        customer_addr = "-"
        if trx:
            customer_name = trx.nama_pelanggan or (trx.pelanggan.nama if trx.pelanggan else "Pelanggan Umum")
            customer_phone = trx.telepon_pelanggan or (trx.pelanggan.telepon if trx.pelanggan else "-")
            customer_addr = trx.alamat_pelanggan or (trx.pelanggan.alamat if trx.pelanggan else "-")

        tgl_retur = format_datetime(retur.tanggal)
        tgl_trx = format_datetime(trx.tanggal) if trx else "-"

        metode_map = {
            "cash": ("REFUND KAS / TUNAI", "#10B981"),
            "potong_piutang": ("POTONG PIUTANG", "#3B82F6"),
            "tukar_barang": ("TUKAR BARANG", "#8B5CF6")
        }
        metode_label, badge_color = metode_map.get(retur.metode_kembali, (str(retur.metode_kembali or '').upper(), "#64748B"))
        metode_badge = f'<span style="background:{badge_color}; color:#fff; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:11px;">{metode_label}</span>'

        item_rows = []
        for i, item in enumerate(retur.detail, 1):
            item_rows.append(f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 8px; text-align: center; color:#64748B;">{i}</td>
                <td style="padding: 8px; color:#1E293B; font-weight:600;">{item.nama_barang}</td>
                <td style="padding: 8px; text-align: center; color:#475569;">{item.kode_barang or '-'}</td>
                <td style="padding: 8px; text-align: center; color:#DC2626; font-weight:bold;">{item.qty}</td>
                <td style="padding: 8px; text-align: right; color:#475569;">{format_rupiah(item.harga_satuan)}</td>
                <td style="padding: 8px; text-align: right; color:#1E293B; font-weight:600;">{format_rupiah(item.subtotal)}</td>
            </tr>
            """)
        items_html = "".join(item_rows)

        petugas_name = retur.user.nama_lengkap or retur.user.username if retur.user else "Petugas Kasir"
        terbilang_str = terbilang(retur.total_retur)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Nota Retur Penjualan - {retur.no_retur}</title>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    color: #1E293B;
                    margin: 0;
                    padding: 20px;
                    font-size: 12px;
                    line-height: 1.4;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .header-tbl td {{
                    vertical-align: top;
                }}
                .retur-title {{
                    font-size: 22px;
                    font-weight: 800;
                    color: #DC2626;
                    letter-spacing: 0.5px;
                }}
                .store-title {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #1E293B;
                }}
                .meta-table td {{
                    padding: 3px 0;
                }}
                .meta-label {{
                    color: #64748B;
                    width: 140px;
                }}
                .meta-value {{
                    color: #0F172A;
                    font-weight: 600;
                }}
                .item-table th {{
                    background: #FEF2F2;
                    color: #991B1B;
                    font-weight: 700;
                    padding: 8px;
                    text-align: left;
                    border-bottom: 2px solid #FCA5A5;
                }}
                .summary-table td {{
                    padding: 4px 6px;
                }}
            </style>
        </head>
        <body>
            <!-- KOP DOKUMEN -->
            <table class="header-tbl" style="border-bottom: 2px solid #DC2626; padding-bottom: 12px; margin-bottom: 16px;">
                <tr>
                    <td style="width: 55%;">
                        <div class="store-title">{store['name']}</div>
                        <div style="color: #64748B; font-size: 11px; margin-top: 2px;">{store['tagline']}</div>
                        <div style="color: #475569; margin-top: 4px;">{store['address']}</div>
                        <div style="color: #475569;">Telp: {store['phone']}</div>
                    </td>
                    <td style="width: 45%; text-align: right;">
                        <div class="retur-title">NOTA RETUR PENJUALAN</div>
                        <div style="font-size: 13px; font-weight: 600; color: #475569; margin-top: 2px;">No. Retur: <span style="color:#DC2626;">{retur.no_retur}</span></div>
                        <div style="margin-top: 6px;">
                            {metode_badge}
                        </div>
                    </td>
                </tr>
            </table>

            <!-- INFO PELANGGAN & TRANSAKSI ASAL -->
            <table style="margin-bottom: 16px;">
                <tr>
                    <td style="width: 50%; vertical-align: top; padding-right: 15px;">
                        <div style="font-weight: 700; font-size: 12px; color: #991B1B; border-bottom: 1px solid #FCA5A5; padding-bottom: 4px; margin-bottom: 6px;">
                            INFORMASI KONSUMEN / PEMBELI:
                        </div>
                        <table class="meta-table">
                            <tr><td class="meta-label">Nama Pelanggan</td><td class="meta-value">: {customer_name}</td></tr>
                            <tr><td class="meta-label">No. Telepon</td><td class="meta-value">: {customer_phone}</td></tr>
                            <tr><td class="meta-label">Alamat</td><td class="meta-value">: {customer_addr}</td></tr>
                        </table>
                    </td>
                    <td style="width: 50%; vertical-align: top; padding-left: 15px;">
                        <div style="font-weight: 700; font-size: 12px; color: #991B1B; border-bottom: 1px solid #FCA5A5; padding-bottom: 4px; margin-bottom: 6px;">
                            REFERENSI TRANSAKSI ASAL:
                        </div>
                        <table class="meta-table">
                            <tr><td class="meta-label">No. Faktur Asal</td><td class="meta-value">: {retur.no_invoice}</td></tr>
                            <tr><td class="meta-label">Tanggal Transaksi</td><td class="meta-value">: {tgl_trx}</td></tr>
                            <tr><td class="meta-label">Tanggal Retur</td><td class="meta-value">: {tgl_retur}</td></tr>
                            <tr><td class="meta-label">Petugas Retur</td><td class="meta-value">: {petugas_name}</td></tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- DAFTAR BARANG YANG DIRETUR -->
            <table class="item-table" style="margin-top: 10px;">
                <thead>
                    <tr>
                        <th style="width: 5%; text-align: center;">No</th>
                        <th style="width: 45%;">Nama Barang / Produk</th>
                        <th style="width: 15%; text-align: center;">Kode</th>
                        <th style="width: 10%; text-align: center;">Qty Retur</th>
                        <th style="width: 12%; text-align: right;">Harga Satuan</th>
                        <th style="width: 13%; text-align: right;">Nilai Retur</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <!-- RINGKASAN & ALASAN -->
            <table style="margin-top: 15px;">
                <tr>
                    <td style="width: 55%; vertical-align: top;">
                        <div style="background: #FEF2F2; border-left: 4px solid #DC2626; padding: 10px 14px; border-radius: 4px;">
                            <div style="font-size: 11px; font-weight: 700; color: #991B1B;">ALASAN PENGEMBALIAN / RETUR:</div>
                            <div style="font-style: italic; font-weight: 600; color: #1E293B; margin-top: 2px; font-size: 12px;">
                                "{retur.alasan or 'Barang rusak / cacat / salah beli'}"
                            </div>
                            <div style="font-size: 11px; font-weight: 700; color: #991B1B; margin-top: 8px;">TERBILANG:</div>
                            <div style="font-style: italic; font-weight: 600; color: #1E293B; margin-top: 2px; font-size: 12px;">
                                "{terbilang_str}"
                            </div>
                        </div>
                    </td>
                    <td style="width: 5%;"></td>
                    <td style="width: 40%; vertical-align: top;">
                        <table class="summary-table" style="font-size: 12px; width: 100%;">
                            <tr style="border-top: 2px solid #991B1B; background: #FEF2F2;">
                                <td style="font-weight: 800; font-size: 13px; color: #991B1B; padding: 10px;">TOTAL NILAI RETUR:</td>
                                <td style="text-align: right; font-weight: 800; font-size: 15px; color: #DC2626; padding: 10px;">{format_rupiah(retur.total_retur)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- TANDA TANGAN -->
            <table style="margin-top: 40px; text-align: center; font-size: 11px;">
                <tr>
                    <td style="width: 35%;">
                        <div>Konsumen / Pembeli</div>
                        <div style="height: 60px;"></div>
                        <div style="font-weight: 700; border-top: 1px dotted #94A3B8; display: inline-block; padding-top: 4px; min-width: 140px;">
                            ( {customer_name} )
                        </div>
                    </td>
                    <td style="width: 30%;"></td>
                    <td style="width: 35%;">
                        <div>Petugas Kasir / Gudang</div>
                        <div style="height: 60px;"></div>
                        <div style="font-weight: 700; border-top: 1px dotted #94A3B8; display: inline-block; padding-top: 4px; min-width: 140px;">
                            ( {petugas_name} )
                        </div>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html

    @classmethod
    def save_html_to_pdf(cls, html_content: str, output_path: str | Path) -> bool:
        """Konversi HTML menjadi file PDF A4 menggunakan PyQt5 QPrinter"""
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtGui import QTextDocument
            from PyQt5.QtPrintSupport import QPrinter

            app = QApplication.instance()
            if app is None:
                app = QApplication([sys.argv[0]])

            doc = QTextDocument()
            doc.setHtml(html_content)

            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(str(output_path))
            printer.setPageSize(QPrinter.A4)
            # Standar margin 15mm
            printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)

            doc.print_(printer)
            return True
        except Exception as e:
            print(f"[InvoicePdfService] Gagal simpan PDF: {e}")
            return False

    @classmethod
    def export_tax_report_to_excel(cls, start_date: datetime, end_date: datetime, output_path: str | Path) -> bool:
        """Generate file Excel Rekapitulasi Pajak (PPN Masukan, Keluaran, & Kurang/Lebih Bayar)"""
        try:
            wb = Workbook()

            # Style helper
            header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            sub_fill = PatternFill(start_color="047857", end_color="047857", fill_type="solid")
            tot_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            bold_font = Font(name="Calibri", size=11, bold=True)
            thin_border = Border(
                left=Side(style='thin', color="CBD5E1"),
                right=Side(style='thin', color="CBD5E1"),
                top=Side(style='thin', color="CBD5E1"),
                bottom=Side(style='thin', color="CBD5E1")
            )

            # Query Transaksi Penjualan (Pajak Keluaran)
            with db.get_session() as session:
                sales = session.query(Transaksi).filter(
                    Transaksi.tanggal >= start_date,
                    Transaksi.tanggal <= end_date,
                    Transaksi.status == "selesai"
                ).order_by(Transaksi.tanggal.asc()).all()

                purchases = session.query(Pembelian).filter(
                    Pembelian.tanggal >= start_date,
                    Pembelian.tanggal <= end_date
                ).order_by(Pembelian.tanggal.asc()).all()

                # ── SHEET 1: RINGKASAN SPT MASA PAJAK ─────────────────────────
                ws1 = wb.active
                ws1.title = "Rekap SPT Pajak Masa"

                ws1.merge_cells("A1:E1")
                ws1["A1"] = f"REKAPITULASI PAJAK PERTAMBAHAN NILAI (PPN & PPh)"
                ws1["A1"].font = Font(size=14, bold=True, color="1E3A8A")

                ws1.merge_cells("A2:E2")
                ws1["A2"] = f"Periode: {format_tanggal(start_date)} s/d {format_tanggal(end_date)}"
                ws1["A2"].font = Font(size=11, italic=True)

                tot_dpp_sales = sum((t.dpp or t.total) for t in sales)
                tot_ppn_keluaran = sum((t.ppn_nominal or 0) for t in sales)
                tot_pph_sales = sum((t.pph_nominal or 0) for t in sales)

                tot_dpp_buy = sum((p.dpp or p.subtotal) for p in purchases)
                tot_ppn_masukan = sum((p.ppn_nominal or 0) for p in purchases)
                tot_pph_buy = sum((p.pph_nominal or 0) for p in purchases)

                selisih_ppn = tot_ppn_keluaran - tot_ppn_masukan

                rekap_data = [
                    ("No", "Uraian Komponen Pajak", "Dasar Pengenaan Pajak (DPP)", "Jumlah PPN", "Keterangan"),
                    ("1", "Pajak Keluaran (Penjualan / Sales)", tot_dpp_sales, tot_ppn_keluaran, f"{len(sales)} transaksi"),
                    ("2", "Pajak Masukan (Pembelian / Purchases)", tot_dpp_buy, tot_ppn_masukan, f"{len(purchases)} faktur"),
                    ("", "SELISIH PPN (Kurang / Lebih Bayar)", "", selisih_ppn, "Kurang Bayar" if selisih_ppn > 0 else "Lebih Bayar"),
                    ("", "Total PPh Terpotong / Terpungut", "", tot_pph_sales + tot_pph_buy, "PPh"),
                ]

                for row_idx, row_vals in enumerate(rekap_data, 5):
                    for col_idx, val in enumerate(row_vals, 1):
                        cell = ws1.cell(row=row_idx, column=col_idx, value=val)
                        cell.border = thin_border
                        if row_idx == 5:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal="center")
                        elif row_idx in [8, 9]:
                            cell.font = bold_font
                            cell.fill = tot_fill
                            if isinstance(val, (int, float)):
                                cell.number_format = "#,##0"
                        else:
                            if isinstance(val, (int, float)):
                                cell.number_format = "#,##0"

                ws1.column_dimensions["A"].width = 6
                ws1.column_dimensions["B"].width = 38
                ws1.column_dimensions["C"].width = 28
                ws1.column_dimensions["D"].width = 24
                ws1.column_dimensions["E"].width = 20

                # ── SHEET 2: PAJAK KELUARAN (PENJUALAN) ───────────────────────
                ws2 = wb.create_sheet("Pajak Keluaran (Sales)")
                ws2.append(["No", "No Invoice", "No Faktur Pajak", "Tanggal", "Nama Pelanggan", "NPWP", "DPP", "PPN (Keluaran)", "PPh", "Total"])
                for col in range(1, 11):
                    c = ws2.cell(row=1, column=col)
                    c.fill = header_fill
                    c.font = header_font
                    c.alignment = Alignment(horizontal="center")

                for i, t in enumerate(sales, 1):
                    dpp = t.dpp if (t.dpp and t.dpp > 0) else t.total
                    cust_name = t.nama_pelanggan or (t.pelanggan.nama if t.pelanggan else "Umum")
                    cust_npwp = t.npwp_pelanggan or (t.pelanggan.npwp if t.pelanggan else "-")
                    row = [
                        i, t.no_invoice, t.no_faktur_pajak or "-", format_datetime(t.tanggal),
                        cust_name, cust_npwp, dpp, t.ppn_nominal or 0, t.pph_nominal or 0, t.total
                    ]
                    ws2.append(row)
                    for c_idx in range(1, 11):
                        cell = ws2.cell(row=i + 1, column=c_idx)
                        cell.border = thin_border
                        if c_idx in [7, 8, 9, 10]:
                            cell.number_format = "#,##0"

                # ── SHEET 3: PAJAK MASUKAN (PEMBELIAN) ────────────────────────
                ws3 = wb.create_sheet("Pajak Masukan (Purchases)")
                ws3.append(["No", "No PO", "No Faktur Vendor", "Tanggal", "Nama Supplier", "NPWP Supplier", "DPP", "PPN (Masukan)", "PPh", "Total Pembelian"])
                for col in range(1, 11):
                    c = ws3.cell(row=1, column=col)
                    c.fill = sub_fill
                    c.font = header_font
                    c.alignment = Alignment(horizontal="center")

                for i, p in enumerate(purchases, 1):
                    dpp = p.dpp if (p.dpp and p.dpp > 0) else p.subtotal
                    sup_name = p.supplier.nama if p.supplier else "Umum"
                    sup_npwp = p.supplier.npwp if p.supplier else "-"
                    row = [
                        i, p.no_po, p.no_faktur, format_datetime(p.tanggal),
                        sup_name, sup_npwp, dpp, p.ppn_nominal or 0, p.pph_nominal or 0, p.total
                    ]
                    ws3.append(row)
                    for c_idx in range(1, 11):
                        cell = ws3.cell(row=i + 1, column=c_idx)
                        cell.border = thin_border
                        if c_idx in [7, 8, 9, 10]:
                            cell.number_format = "#,##0"

                # Auto width sheets
                for sheet in [ws2, ws3]:
                    for col in sheet.columns:
                        max_len = max(len(str(cell.value or '')) for cell in col)
                        col_letter = col[0].column_letter
                        sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

            wb.save(output_path)
            return True
        except Exception as e:
            print(f"[InvoicePdfService] Gagal ekspor Excel pajak: {e}")
            return False
