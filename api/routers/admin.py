"""Admin-only mobile API: user management, suppliers and purchase invoices."""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import os
import io
import bcrypt
from sqlalchemy import or_
from api.deps import require_admin, get_current_user_id, get_current_user_payload
from database.db import db
from database.models import User, Supplier, Pembelian, PembelianDetail, Barang, LogDrawer
from utils.helpers import generate_po_number, generate_supplier_code
from services.backup_service import BackupService
from services.drawer_service import DrawerService
import config

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get('/users')
def list_users(_: dict = Depends(require_admin)):
    with db.get_session() as s:
        rows = s.query(User).order_by(User.id.asc()).all()
        return [{"id":u.id,"username":u.username,"nama_lengkap":u.nama_lengkap,"role":u.role,"aktif":u.aktif,"must_change_password":u.must_change_password} for u in rows]

@router.post('/users', status_code=status.HTTP_201_CREATED)
def create_user(body: dict, _: dict = Depends(require_admin)):
    username = str(body.get('username','')).strip().lower().replace(' ','')
    password = str(body.get('password',''))
    if not username or len(password) < 6:
        raise HTTPException(400, 'Username wajib dan password minimal 6 karakter')
    role = body.get('role','kasir') if body.get('role') in ('admin','kasir') else 'kasir'
    with db.get_session() as s:
        if s.query(User).filter(User.username == username).first():
            raise HTTPException(409, 'Username sudah digunakan')
        u = User(username=username, password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                 role=role, nama_lengkap=body.get('nama_lengkap','').strip() or None,
                 aktif=bool(body.get('aktif',True)))
        s.add(u); s.flush()
        return {"id":u.id,"username":u.username,"nama_lengkap":u.nama_lengkap,"role":u.role,"aktif":u.aktif}

@router.put('/users/{user_id}')
def update_user(user_id:int, body:dict, current_id:int=Depends(get_current_user_id), _:dict=Depends(require_admin)):
    with db.get_session() as s:
        u=s.query(User).filter_by(id=user_id).first()
        if not u: raise HTTPException(404,'User tidak ditemukan')
        if user_id == current_id and body.get('aktif') is False: raise HTTPException(400,'Akun admin yang sedang digunakan tidak dapat dinonaktifkan')
        username = str(body.get('username',u.username)).strip().lower().replace(' ','')
        dup=s.query(User).filter(User.username==username, User.id!=user_id).first()
        if dup: raise HTTPException(409,'Username sudah digunakan')
        u.username=username; u.nama_lengkap=body.get('nama_lengkap',u.nama_lengkap)
        u.role=body.get('role',u.role) if body.get('role') in ('admin','kasir') else u.role
        if 'aktif' in body: u.aktif=bool(body['aktif'])
        if body.get('password'):
            if len(body['password'])<6: raise HTTPException(400,'Password minimal 6 karakter')
            u.password_hash=bcrypt.hashpw(body['password'].encode(),bcrypt.gensalt()).decode()
        s.flush(); return {"id":u.id,"username":u.username,"nama_lengkap":u.nama_lengkap,"role":u.role,"aktif":u.aktif}

@router.delete('/users/{user_id}')
def delete_user(user_id:int, current_id:int=Depends(get_current_user_id), _:dict=Depends(require_admin)):
    # PC version benar-benar menghapus user, tetapi melindungi admin terakhir.
    if user_id == current_id: raise HTTPException(400,'Tidak dapat menghapus akun sendiri')
    with db.get_session() as s:
        u=s.query(User).filter_by(id=user_id).first()
        if not u: raise HTTPException(404,'User tidak ditemukan')
        if (u.role or '').strip().lower() == 'admin':
            admin_count=s.query(User).filter(User.role=='admin').count()
            if admin_count <= 1:
                raise HTTPException(400,'Tidak bisa menghapus admin terakhir. Minimal harus ada 1 admin.')
        s.delete(u)
        s.flush()
        return {"message":"User berhasil dihapus permanen"}

@router.get('/suppliers')
def list_suppliers(_:dict=Depends(require_admin)):
    with db.get_session() as s:
        rows=s.query(Supplier).filter_by(aktif=True).order_by(Supplier.nama.asc()).all()
        return [{"id":x.id,"kode":x.kode,"nama":x.nama,"kontak":x.kontak,"telepon":x.telepon,"npwp":x.npwp,"alamat":x.alamat} for x in rows]

@router.post('/suppliers', status_code=201)
def create_supplier(body:dict, _:dict=Depends(require_admin)):
    nama=str(body.get('nama','')).strip()
    if not nama: raise HTTPException(400,'Nama supplier wajib diisi')
    with db.get_session() as s:
        x=Supplier(kode=body.get('kode') or generate_supplier_code(s), nama=nama, kontak=body.get('kontak'), telepon=body.get('telepon'), npwp=body.get('npwp'), alamat=body.get('alamat'))
        s.add(x); s.flush(); return {"id":x.id,"kode":x.kode,"nama":x.nama,"kontak":x.kontak,"telepon":x.telepon,"npwp":x.npwp,"alamat":x.alamat}

@router.put('/suppliers/{supplier_id}')
def update_supplier(supplier_id:int, body:dict, _:dict=Depends(require_admin)):
    with db.get_session() as s:
        x=s.query(Supplier).filter_by(id=supplier_id).first()
        if not x: raise HTTPException(404,'Supplier tidak ditemukan')
        for k in ('nama','kontak','telepon','npwp','alamat'):
            if k in body: setattr(x,k,body[k])
        s.flush(); return {"id":x.id,"kode":x.kode,"nama":x.nama,"kontak":x.kontak,"telepon":x.telepon,"npwp":x.npwp,"alamat":x.alamat}

@router.get('/pembelian')
def list_pembelian(limit:int=Query(200,ge=1,le=500), _:dict=Depends(require_admin)):
    with db.get_session() as s:
        rows=s.query(Pembelian).order_by(Pembelian.tanggal.desc()).limit(limit).all()
        return [{"id":p.id,"no_po":p.no_po,"no_faktur":p.no_faktur,"tanggal":p.tanggal.isoformat() if p.tanggal else None,
                 "supplier":p.supplier.nama if p.supplier else 'Umum',"supplier_id":p.supplier_id,"subtotal":p.subtotal,"ppn_nominal":p.ppn_nominal,"total":p.total,"status_bayar":p.status_bayar,"status_barang":p.status_barang} for p in rows]

@router.post('/pembelian', status_code=201)
def create_pembelian(body:dict, user_id:int=Depends(get_current_user_id), _:dict=Depends(require_admin)):
    items=body.get('items') or []
    if not items: raise HTTPException(400,'Minimal satu barang harus dipilih')
    with db.get_session() as s:
        no_po=generate_po_number(s)
        dpp=0
        prepared=[]
        for it in items:
            b=s.query(Barang).filter_by(id=int(it['barang_id']), aktif=True).first()
            if not b: raise HTTPException(404,f"Barang ID {it['barang_id']} tidak ditemukan")
            qty=int(it.get('qty',0)); harga=float(it.get('harga_beli',b.harga_beli or 0))
            if qty<=0: raise HTTPException(400,'Qty harus lebih dari 0')
            sub=qty*harga; dpp+=sub; prepared.append((b,qty,harga,sub))
        ppn_persen=float(body.get('ppn_persen',0)); ppn=dpp*ppn_persen/100; total=dpp+ppn
        p=Pembelian(no_faktur=str(body.get('no_faktur','-')).strip() or '-',no_po=no_po,supplier_id=body.get('supplier_id'),tanggal=datetime.now(),subtotal=dpp,dpp=dpp,ppn_persen=ppn_persen,ppn_nominal=ppn,total=total,status_bayar=body.get('status_bayar','lunas'),metode_bayar=body.get('metode_bayar','transfer'),catatan=body.get('catatan'),user_id=user_id)
        s.add(p); s.flush()
        for b,qty,harga,sub in prepared:
            s.add(PembelianDetail(pembelian_id=p.id,barang_id=b.id,kode_barang=b.kode,nama_barang=b.nama,qty=qty,harga_beli=harga,subtotal=sub))
            b.stok += qty; b.harga_beli=harga
        s.flush(); return {"id":p.id,"no_po":p.no_po,"total":p.total,"message":"Faktur pembelian berhasil disimpan dan stok diperbarui"}


# ───────────────────────── PC PARITY: PURCHASE / BACKUP / CASH DRAWER ─────────────────────────
@router.put('/pembelian/{pembelian_id}/lunas')
def lunasi_pembelian(pembelian_id:int, _:dict=Depends(require_admin)):
    with db.get_session() as s:
        p=s.query(Pembelian).filter_by(id=pembelian_id).first()
        if not p: raise HTTPException(404,'Faktur pembelian tidak ditemukan')
        if p.status_bayar == 'lunas':
            return {"message":"Faktur sudah lunas","status_bayar":p.status_bayar}
        p.status_bayar='lunas'
        s.flush()
        return {"message":"Status pembayaran berhasil diubah menjadi Lunas","status_bayar":p.status_bayar}

@router.get('/backups')
def list_backups(_:dict=Depends(require_admin)):
    svc=BackupService()
    return [{"name":x["name"],"size":x["size"],"created":x["created"].isoformat()} for x in svc.get_backup_list()]

@router.post('/backups')
def create_backup(_:dict=Depends(require_admin)):
    path=BackupService().create_backup()
    if not path: raise HTTPException(500,'Gagal membuat backup database')
    return {"message":"Backup berhasil dibuat","name":Path(path).name}

@router.get('/backups/{name}/download')
def download_backup(name:str, _:dict=Depends(require_admin)):
    safe=Path(name).name
    path=config.BACKUP_DIR / safe
    if not path.exists() or not safe.startswith('kasirku_backup_'):
        raise HTTPException(404,'Backup tidak ditemukan')
    return FileResponse(str(path),filename=safe,media_type='application/octet-stream')

@router.post('/backups/{name}/restore')
def restore_backup(name:str, _:dict=Depends(require_admin)):
    safe=Path(name).name
    path=config.BACKUP_DIR / safe
    if not path.exists() or not safe.startswith('kasirku_backup_'):
        raise HTTPException(404,'Backup tidak ditemukan')
    ok=BackupService().restore_backup(str(path))
    if not ok: raise HTTPException(500,'Gagal melakukan restore database')
    return {"message":"Database berhasil di-restore. Silakan login ulang."}

@router.get('/drawer/log')
def drawer_log(limit:int=Query(100,ge=1,le=500), _:dict=Depends(require_admin)):
    with db.get_session() as s:
        rows=s.query(LogDrawer).order_by(LogDrawer.timestamp.desc()).limit(limit).all()
        return [{"id":x.id,"timestamp":x.timestamp.isoformat() if x.timestamp else None,"user":x.user.username if x.user else '-',"aksi":x.aksi,"keterangan":x.keterangan or ''} for x in rows]

@router.post('/drawer/open')
def drawer_open(user_id:int=Depends(get_current_user_id), _:dict=Depends(require_admin)):
    ok=DrawerService().manual_open(user_id=user_id)
    if not ok: raise HTTPException(500,'Cash drawer gagal dibuka')
    return {"message":"Perintah buka cash drawer telah dikirim"}


@router.post('/qris/upload')
async def upload_qris(file: UploadFile=File(...), _:dict=Depends(require_admin)):
    ext=Path(file.filename or '').suffix.lower()
    if ext not in ('.png','.jpg','.jpeg','.bmp'):
        raise HTTPException(400,'Format QRIS harus PNG/JPG/JPEG/BMP')
    dest=config.UPLOAD_DIR / f'qris_toko{ext}'
    config.UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
    data=await file.read()
    if len(data)>5*1024*1024: raise HTTPException(400,'Ukuran QRIS maksimal 5 MB')
    dest.write_bytes(data)
    db.set_setting('qris_image_path',str(dest))
    return {"message":"QRIS berhasil diupload","path":str(dest)}
