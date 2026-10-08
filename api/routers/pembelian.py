"""Purchase invoice / PO API for administrator mobile and desktop web."""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, date
from api.deps import get_current_user_payload, get_current_user_id
from database.db import db
from database.models import Pembelian, PembelianDetail, Supplier, Barang
from utils.helpers import generate_po_number

router=APIRouter(prefix='/api/pembelian', tags=['pembelian'])

def _out(p, include_detail=False):
    d={"id":p.id,"no_po":p.no_po,"no_faktur":p.no_faktur,"tanggal":p.tanggal.isoformat() if p.tanggal else None,
       "tanggal_jatuh_tempo":p.jatuh_tempo.isoformat() if p.jatuh_tempo else None,
       "supplier_id":p.supplier_id,"supplier":({"id":p.supplier.id,"kode":p.supplier.kode,"nama":p.supplier.nama,"npwp":p.supplier.npwp} if p.supplier else None),
       "subtotal":p.subtotal,"dpp":p.dpp,"ppn_persen":p.ppn_persen,"ppn_nominal":p.ppn_nominal,"pph_persen":p.pph_persen,"pph_nominal":p.pph_nominal,
       "total":p.total,"status_bayar":p.status_bayar,"status_barang":p.status_barang,"metode_bayar":p.metode_bayar,"catatan":p.catatan}
    if include_detail:
        d['detail']=[{"id":x.id,"barang_id":x.barang_id,"kode_barang":x.kode_barang,"nama_barang":x.nama_barang,"qty":x.qty,"harga_beli":x.harga_beli,"subtotal":x.subtotal} for x in p.detail]
    return d

@router.get('')
def list_pembelian(limit:int=Query(200,ge=1,le=500), _:dict=Depends(get_current_user_payload)):
    with db.get_session() as s:
        return [_out(p) for p in s.query(Pembelian).order_by(Pembelian.tanggal.desc()).limit(limit).all()]

@router.get('/supplier/list')
def supplier_list(_:dict=Depends(get_current_user_payload)):
    with db.get_session() as s:
        return [{"id":x.id,"kode":x.kode,"nama":x.nama,"kontak":x.kontak,"telepon":x.telepon,"npwp":x.npwp,"alamat":x.alamat} for x in s.query(Supplier).filter_by(aktif=True).order_by(Supplier.nama).all()]

@router.get('/{pembelian_id}')
def get_pembelian(pembelian_id:int, _:dict=Depends(get_current_user_payload)):
    with db.get_session() as s:
        p=s.query(Pembelian).filter_by(id=pembelian_id).first()
        if not p: raise HTTPException(404,'Faktur pembelian tidak ditemukan')
        return _out(p, True)

@router.post('')
def create_pembelian(body:dict, user_id:int=Depends(get_current_user_id), _:dict=Depends(get_current_user_payload)):
    items=body.get('items') or []
    if not items: raise HTTPException(400,'Minimal satu barang harus dipilih')
    with db.get_session() as s:
        # Validasi duplikat no_faktur dari supplier
        no_faktur = str(body.get('no_faktur','-')).strip() or '-'
        if no_faktur != '-':
            existing_faktur = s.query(Pembelian).filter_by(no_faktur=no_faktur).first()
            if existing_faktur:
                raise HTTPException(
                    400,
                    f"Nomor faktur '{no_faktur}' sudah pernah digunakan di PO {existing_faktur.no_po}. "
                    "Periksa kembali nomor faktur dari supplier."
                )
        dpp=0; prepared=[]
        for it in items:
            b=s.query(Barang).filter_by(id=int(it['barang_id']),aktif=True).first()
            if not b: raise HTTPException(404,f"Barang ID {it['barang_id']} tidak ditemukan")
            qty=int(it.get('qty',0)); harga=float(it.get('harga_beli',b.harga_beli or 0))
            if qty<1 or harga<0: raise HTTPException(400,'Qty/harga tidak valid')
            sub=qty*harga; dpp+=sub; prepared.append((b,qty,harga,sub))
        ppn_persen=float(body.get('ppn_persen',0)); ppn=dpp*ppn_persen/100
        try:
            tgl = datetime.fromisoformat(str(body.get('tanggal'))) if body.get('tanggal') else datetime.now()
        except ValueError:
            tgl = datetime.now()
        try:
            jatuh = datetime.fromisoformat(str(body.get('jatuh_tempo'))) if body.get('jatuh_tempo') else None
        except ValueError:
            jatuh = None
        p=Pembelian(no_faktur=str(body.get('no_faktur','-')).strip() or '-',no_po=generate_po_number(s),supplier_id=body.get('supplier_id'),tanggal=tgl,jatuh_tempo=jatuh,subtotal=dpp,dpp=dpp,ppn_persen=ppn_persen,ppn_nominal=ppn,total=dpp+ppn,status_bayar=body.get('status_bayar','lunas'),metode_bayar=body.get('metode_bayar','transfer'),catatan=body.get('catatan'),user_id=user_id)
        s.add(p); s.flush()
        for b,qty,harga,sub in prepared:
            s.add(PembelianDetail(pembelian_id=p.id,barang_id=b.id,kode_barang=b.kode,nama_barang=b.nama,qty=qty,harga_beli=harga,subtotal=sub))
            b.stok += qty; b.harga_beli=harga
        s.flush(); return _out(p, True)

