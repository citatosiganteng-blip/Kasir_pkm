# Requirements Document

## Introduction

Fitur **Menu Display Custom** menambahkan tampilan etalase menu berformat grid pada halaman kasir (POS) KasirKu. User dapat sepenuhnya mengelola item menu yang tampil: menambahkan menu baru lengkap dengan foto, nama, dan harga custom; mengedit item yang sudah ada; serta menghapus item tanpa batas. Tampilan grid 3–4 kolom menampilkan setiap item dalam card berisi foto produk, nama menu, dan harga — menyerupai referensi etalase visual kafe/restoran. Fitur ini terpisah dari manajemen barang/stok, sehingga kasir bebas mengatur tampilan menu tanpa harus melalui halaman Barang.

Aplikasi ini adalah desktop app Python dengan PyQt5 dan backend FastAPI. Fitur ini akan berjalan di layer UI (PyQt5) dengan operasi database langsung melalui SQLAlchemy — mengikuti pola yang digunakan di `BarangPage`, `KasirPage`, dan `BarangFormDialog`.

---

## Glossary

- **Menu_Display**: Komponen tampilan grid di halaman kasir yang menampilkan item-item menu dalam bentuk card.
- **Menu_Item**: Satu entri menu yang terdiri dari foto, nama, dan harga yang dikelola user secara manual — berbeda dari model `Barang` yang mengandung stok.
- **Menu_Card**: Satu kartu visual dalam grid yang merepresentasikan satu `Menu_Item`.
- **Menu_Grid**: Layout keseluruhan yang menampung semua `Menu_Card` dalam susunan kolom.
- **Menu_Form_Dialog**: Dialog PyQt5 untuk menambah atau mengedit satu `Menu_Item`.
- **Photo_Manager**: Komponen internal yang menangani pemilihan, penyalinan, dan penghapusan file foto untuk `Menu_Item`.
- **Admin**: Pengguna dengan role `admin` yang berhak mengelola (tambah/edit/hapus) `Menu_Item`.
- **Kasir**: Pengguna dengan role `kasir` yang hanya dapat melihat `Menu_Display` dan mengklik item untuk memasukkannya ke keranjang.
- **MenuItem_Table**: Tabel database baru `menu_items` yang menyimpan data `Menu_Item`.

---

## Requirements

### Requirement 1: Model Data Menu Item

**User Story:** Sebagai admin, saya ingin data menu item tersimpan secara persisten di database, sehingga menu yang sudah dikonfigurasi tidak hilang ketika aplikasi ditutup.

#### Acceptance Criteria

1. THE `Menu_Display` System SHALL menyimpan setiap `Menu_Item` dalam tabel database `menu_items` dengan kolom: `id` (integer primary key auto-increment), `nama` (string, tidak boleh kosong), `harga` (float, tidak boleh nol atau negatif), `foto` (string path relatif, opsional), `urutan` (integer untuk pengurutan tampilan, default 0), `aktif` (boolean, default True), dan `created_at` (datetime).
2. THE `Menu_Display` System SHALL menggunakan SQLAlchemy ORM mengikuti pola model yang ada di `database/models.py`.
3. WHEN aplikasi pertama kali dijalankan dan tabel `menu_items` belum ada, THE `Menu_Display` System SHALL membuat tabel tersebut secara otomatis melalui mekanisme `Base.metadata.create_all` yang sudah ada.
4. THE `Photo_Manager` SHALL menyimpan file foto `Menu_Item` ke direktori `uploads/menu/` di bawah `BASE_DIR`, mengikuti pola `UPLOAD_PRODUK_DIR` di `config.py`.

---

### Requirement 2: Tampilan Grid Menu di Halaman Kasir

**User Story:** Sebagai kasir, saya ingin melihat menu dalam tampilan grid berisi foto, nama, dan harga, sehingga saya dapat dengan cepat menemukan dan memilih item yang dipesan pelanggan.

#### Acceptance Criteria

1. THE `Menu_Display` System SHALL menampilkan semua `Menu_Item` dengan `aktif = True` dalam `Menu_Grid` berformat 3 kolom pada lebar layar default, dan secara otomatis menyesuaikan menjadi 4 kolom ketika lebar area konten melebihi 1100 piksel.
2. THE `Menu_Card` SHALL menampilkan tiga elemen secara berurutan dari atas ke bawah: (a) foto produk atau placeholder emoji/warna jika foto tidak tersedia, (b) nama menu rata tengah, dan (c) harga dalam format Rupiah rata tengah.
3. WHEN `Menu_Item` memiliki field `foto` yang merujuk pada file yang ada, THE `Menu_Card` SHALL menampilkan foto tersebut sebagai banner penuh di bagian atas card dengan sudut atas membulat, mengikuti pola `create_rounded_top_pixmap` yang ada di `kasir_page.py`.
4. IF field `foto` pada `Menu_Item` kosong atau file tidak ditemukan, THEN THE `Menu_Card` SHALL menampilkan emoji produk generik dan warna latar belakang pastel sebagai placeholder, mengikuti pola `get_product_icon_and_bg` yang ada.
5. THE `Menu_Grid` SHALL ditampilkan di dalam `QScrollArea` sehingga user dapat menggulir ke bawah ketika jumlah item melebihi area tampilan yang tersedia.
6. THE `Menu_Display` System SHALL merender ulang `Menu_Grid` setiap kali halaman kasir mendapatkan fokus navigasi, memastikan perubahan yang baru disimpan langsung terlihat.
7. WHEN tema aplikasi berubah (terang/gelap), THE `Menu_Display` System SHALL memperbarui warna latar belakang `Menu_Card`, warna teks nama dan harga, serta border card sesuai tema aktif — mengikuti pola `on_theme_changed` yang ada di halaman-halaman lain.

---

### Requirement 3: Tambah Menu Item Baru

**User Story:** Sebagai admin, saya ingin menambahkan item menu baru dengan foto, nama, dan harga custom, sehingga saya dapat mengkonfigurasi etalase menu sesuai kebutuhan toko saya.

#### Acceptance Criteria

1. WHERE pengguna memiliki role `admin`, THE `Menu_Display` System SHALL menampilkan tombol "+ Tambah Menu" di area toolbar atas `Menu_Display`.
2. WHEN admin mengklik tombol "+ Tambah Menu", THE `Menu_Form_Dialog` SHALL terbuka sebagai dialog modal dengan form berisi field: Foto (opsional), Nama Menu (wajib), Harga (wajib, harus lebih dari 0), dan Urutan Tampilan (opsional, integer).
3. THE `Menu_Form_Dialog` SHALL menyediakan tombol "📁 Pilih Foto" yang membuka `QFileDialog` untuk memilih file gambar berformat JPG, PNG, WEBP, atau BMP.
4. WHEN admin memilih file foto, THE `Menu_Form_Dialog` SHALL menampilkan pratinjau foto berukuran 68×68 piksel di dalam dialog, mengikuti pola `_display_photo` pada `BarangFormDialog`.
5. WHEN admin mengklik "Simpan", THE `Menu_Form_Dialog` SHALL memvalidasi bahwa field Nama Menu tidak kosong dan nilai Harga lebih dari 0; jika validasi gagal, THE `Menu_Form_Dialog` SHALL menampilkan pesan kesalahan inline tanpa menutup dialog.
6. WHEN validasi berhasil dan admin mengklik "Simpan", THE `Photo_Manager` SHALL menyalin file foto yang dipilih ke direktori `uploads/menu/` dengan nama unik yang menggunakan format `menu_{nama_slug}_{uuid6}{ext}`, dan THE `Menu_Form_Dialog` SHALL menyimpan `Menu_Item` baru ke database lalu menutup dialog.
7. AFTER `Menu_Form_Dialog` ditutup dengan sukses, THE `Menu_Display` System SHALL memuat ulang `Menu_Grid` sehingga item baru langsung tampil.

---

### Requirement 4: Edit Menu Item

**User Story:** Sebagai admin, saya ingin mengedit item menu yang sudah ada (nama, harga, atau foto), sehingga saya dapat memperbarui informasi menu tanpa harus menghapus dan menambah ulang.

#### Acceptance Criteria

1. WHERE pengguna memiliki role `admin`, THE `Menu_Card` SHALL menampilkan tombol ikon "✏" (edit) yang terlihat saat kartu di-hover.
2. WHEN admin mengklik tombol edit pada `Menu_Card`, THE `Menu_Form_Dialog` SHALL terbuka dengan field-field yang sudah terisi dengan data `Menu_Item` yang bersangkutan.
3. WHEN admin mengganti foto pada dialog edit, THE `Photo_Manager` SHALL menyalin file foto baru ke direktori `uploads/menu/` dan memperbarui path pada record `Menu_Item`; file foto lama TIDAK dihapus secara otomatis untuk mencegah kehilangan data yang tidak disengaja.
4. WHEN admin menghapus foto pada dialog edit menggunakan tombol "🗑 Hapus Foto", THE `Photo_Manager` SHALL mengosongkan field `foto` pada record `Menu_Item` sehingga placeholder ditampilkan pada card.
5. WHEN admin mengklik "Simpan" pada dialog edit, THE `Menu_Form_Dialog` SHALL menyimpan perubahan ke database dan menutup dialog, lalu THE `Menu_Display` System SHALL memuat ulang `Menu_Grid`.

---

### Requirement 5: Hapus Menu Item

**User Story:** Sebagai admin, saya ingin menghapus item menu yang tidak lagi relevan, sehingga etalase menu hanya menampilkan item yang tersedia saat ini.

#### Acceptance Criteria

1. WHERE pengguna memiliki role `admin`, THE `Menu_Card` SHALL menampilkan tombol ikon "🗑" (hapus) yang terlihat saat kartu di-hover.
2. WHEN admin mengklik tombol hapus, THE `Menu_Display` System SHALL menampilkan dialog konfirmasi yang menyebutkan nama item yang akan dihapus sebelum menjalankan penghapusan.
3. WHEN admin mengkonfirmasi penghapusan, THE `Menu_Display` System SHALL mengubah field `aktif` menjadi `False` pada record `Menu_Item` yang bersangkutan (soft delete), bukan menghapus row dari database.
4. AFTER penghapusan dikonfirmasi, THE `Menu_Display` System SHALL memuat ulang `Menu_Grid` sehingga item yang dihapus tidak lagi tampil.
5. IF admin membatalkan dialog konfirmasi, THEN THE `Menu_Display` System SHALL menutup dialog tanpa melakukan perubahan apapun pada database.

---

### Requirement 6: Klik Item Menu untuk Menambah ke Keranjang

**User Story:** Sebagai kasir, saya ingin mengklik item menu di grid untuk langsung menambahkannya ke keranjang transaksi, sehingga proses input pesanan menjadi lebih cepat.

#### Acceptance Criteria

1. WHEN kasir mengklik sebuah `Menu_Card`, THE `Menu_Display` System SHALL memancarkan sinyal yang meneruskan data `Menu_Item` (id barang yang terhubung jika ada, nama, dan harga) ke komponen keranjang pada `KasirPage`.
2. IF `Menu_Item` tidak memiliki referensi ke `Barang` yang aktif di tabel `barang`, THEN THE `Menu_Display` System SHALL menambahkan item tersebut ke keranjang sebagai item adhoc dengan nama dan harga dari `Menu_Item`, tanpa pengurangan stok.
3. WHILE `Menu_Item` memiliki referensi ke `Barang` dengan `stok = 0`, THE `Menu_Card` SHALL menampilkan overlay atau label "Habis" dan WHEN kasir mengklik card tersebut, THE `Menu_Display` System SHALL menampilkan pesan bahwa stok barang tersebut kosong tanpa menambahkan item ke keranjang.

---

### Requirement 7: Hapus Semua Menu Sekaligus

**User Story:** Sebagai admin, saya ingin menghapus semua item menu yang ada sekaligus, sehingga saya dapat memulai dengan konfigurasi menu yang sepenuhnya baru tanpa harus menghapus satu per satu.

#### Acceptance Criteria

1. WHERE pengguna memiliki role `admin`, THE `Menu_Display` System SHALL menampilkan tombol "🗑 Hapus Semua" di area toolbar atas `Menu_Display`.
2. WHEN admin mengklik "🗑 Hapus Semua", THE `Menu_Display` System SHALL menampilkan dialog konfirmasi dengan teks yang secara eksplisit menyebutkan jumlah item yang akan dihapus dan bahwa aksi ini akan menonaktifkan semua item sekaligus.
3. WHEN admin mengkonfirmasi "Hapus Semua", THE `Menu_Display` System SHALL mengubah field `aktif` menjadi `False` pada semua record `Menu_Item` dalam satu operasi database, lalu memuat ulang `Menu_Grid` sehingga grid tampil kosong.
4. IF admin membatalkan dialog konfirmasi "Hapus Semua", THEN THE `Menu_Display` System SHALL menutup dialog tanpa melakukan perubahan apapun.

---

### Requirement 8: Pencarian dan Filter Menu

**User Story:** Sebagai kasir, saya ingin mencari menu berdasarkan nama saat etalase memiliki banyak item, sehingga saya dapat menemukan item yang diinginkan pelanggan dengan cepat.

#### Acceptance Criteria

1. THE `Menu_Display` System SHALL menyediakan field pencarian teks di atas `Menu_Grid` yang memfilter `Menu_Card` yang ditampilkan secara real-time berdasarkan kecocokan substring (tidak peka huruf besar/kecil) pada field `nama` dari `Menu_Item`.
2. WHEN field pencarian berubah, THE `Menu_Display` System SHALL menerapkan filter dalam waktu tidak lebih dari 300 milidetik menggunakan `QTimer` single-shot, mengikuti pola yang ada di `BarangPage`.
3. IF tidak ada `Menu_Item` yang cocok dengan query pencarian, THEN THE `Menu_Display` System SHALL menampilkan teks "Tidak ada menu yang cocok dengan pencarian" di tengah area grid sebagai ganti grid kosong.
