# Opname Kasir

Aplikasi otomasi rekonsiliasi kas besar dan penentuan kombinasi pecahan fisik (uang kertas dan koin) berdasarkan data buku besar.

## Fitur Utama

- **Batch Multi-Tanggal**: Mendukung pemrosesan data pivot multi-tanggal dalam satu kali klik.
- **Pencocokan Otomatis**: Memetakan tanggal buku besar ($T$) ke tanggal template fisik opname kasir ($T+1$).
- **Optimasi Pecahan Anti-Slop**:
  - Meminimalkan selisih fisik vs saldo buku besar (kelipatan 100 terdekat).
  - Alokasi koin terbatas murni untuk sisa ratusan sub-1.000 ($< \text{Rp } 1.000$).
  - Kelipatan ribuan ke atas sepenuhnya dicover uang kertas dengan distribusi proporsional wajar.
- **Proteksi Data**: Form Kas Kecil dan BG/CEK dilindungi penuh dan tidak diubah.

## Menjalankan Secara Lokal

1. Pastikan Python 3.9+ sudah terpasang.
2. Pasang dependensi:
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan aplikasi Streamlit:
   ```bash
   streamlit run app.py
   ```

## Deploy ke Streamlit Community Cloud

1. Buat repository baru di [GitHub](https://github.com/new) (misal: `opname-kasir`).
2. Hubungkan folder ini ke repository GitHub:
   ```bash
   git init
   git add .
   git commit -m "Inisialisasi aplikasi Opname Kasir"
   git branch -M main
   git remote add origin https://github.com/<USERNAME-ANDA>/opname-kasir.git
   git push -u origin main
   ```
3. Buka [share.streamlit.io](https://share.streamlit.io).
4. Klik **New app**:
   - **Repository**: `<USERNAME-ANDA>/opname-kasir`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Klik **Deploy**!
