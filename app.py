"""
Aplikasi Web: Opname Kasir
Sistem Rekonsiliasi & Penentuan Pecahan Fisik Kas Besar
Siap deploy ke Streamlit Cloud & GitHub
"""

import os
import io
import glob
import re
import pandas as pd
import streamlit as st

from core.parser import parse_pivot_text, parse_pivot_file, get_opname_date_info
from core.excel_updater import update_workbook_with_data

st.set_page_config(
    page_title="Opname Kasir",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk gaya profesional bebas slop & tipografi finansial
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .font-mono-numbers {
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
    }
    
    /* Header & Title */
    .app-header {
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }
    .app-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    /* Tombol Utama */
    .stButton > button {
        background-color: #0f172a !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        border: 1px solid #0f172a !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton > button:hover {
        background-color: #1e293b !important;
        border-color: #1e293b !important;
    }
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 0.75rem 1rem;
        border-radius: 6px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: #64748b !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.25rem !important;
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    
    /* Dataframe styling */
    .dataframe {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Top Header
st.markdown("""
<div class="app-header">
    <h1 class="app-title">Opname Kasir</h1>
</div>
""", unsafe_allow_html=True)

# Inisialisasi state penyimpanan hasil kalkulasi
if "results" not in st.session_state:
    st.session_state.results = {}
if "processed_files" not in st.session_state:
    st.session_state.processed_files = {}

# Layout Utama Streamlit: Sidebar kiri untuk input, area utama untuk preview & eksekusi
with st.sidebar:
    st.markdown("### 1. Template Excel Opname")
    uploaded_excels = st.file_uploader(
        "Pilih file Excel opname (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=True,
        help="Unggah satu atau beberapa template Excel opname sekaligus."
    )
    
    # Deteksi otomatis file lokal jika tidak ada file yang di-upload
    local_files = []
    if not uploaded_excels:
        for p in glob.glob("OPNAME KASIR * PASURUAN.xlsx"):
            if not p.endswith("_backup.xlsx"):
                local_files.append(p)
        if local_files:
            st.caption(f"Terdeteksi {len(local_files)} file template lokal di folder kerja.")
    
    st.markdown("---")
    st.markdown("### 2. Data Pivot Nominal")
    input_mode = st.radio(
        "Pilih metode input:",
        options=["Paste Clipboard", "Upload File Pivot"],
        horizontal=True,
        label_visibility="collapsed"
    )

    pivot_data = {}
    if input_mode == "Paste Clipboard":
        clipboard_text = st.text_area(
            "Tempel data pivot di sini:",
            height=200,
            placeholder="Tgl\tDivisi\tTotal\n2026-10-02\t02/01\t58,349,009\n\t02/04\t11,794,862...",
            help="Mendukung format compact dengan sel tanggal kosong di bawah tanggal utama."
        )
        if clipboard_text.strip():
            pivot_data = parse_pivot_text(clipboard_text)
    else:
        pivot_file = st.file_uploader(
            "Pilih file CSV atau XLSX data pivot",
            type=["csv", "xlsx", "xls"],
            key="pivot_uploader"
        )
        if pivot_file:
            pivot_data = parse_pivot_file(pivot_file)

    st.markdown("---")
    btn_process = st.button("Kalkulasi Seluruh Batch", use_container_width=True)

# Area Utama: Proses & Pratinjau
if btn_process:
    if not pivot_data:
        st.warning("Silakan masukkan data pivot nominal terlebih dahulu.")
    else:
        # Kumpulkan berkas template yang tersedia (dari upload atau lokal)
        available_files = {}
        if uploaded_excels:
            for uf in uploaded_excels:
                available_files[uf.name] = uf.getvalue()
        elif local_files:
            for lf in local_files:
                with open(lf, "rb") as f:
                    available_files[os.path.basename(lf)] = f.read()

        if not available_files:
            st.error("Tidak ada berkas template Excel yang diunggah atau ditemukan di folder.")
        else:
            new_results = {}
            new_processed = {}

            # Proses setiap tanggal di pivot data
            for ledger_date, div_records in pivot_data.items():
                op_dt, day, month, search_pattern = get_opname_date_info(ledger_date)
                
                # Cari berkas yang cocok dengan tanggal opname
                matched_name = None
                matched_bytes = None

                for fname, fbytes in available_files.items():
                    # Cocokkan nama file: misal '3 OKTOBER' atau '03 OKTOBER'
                    if search_pattern:
                        day_str = str(day)
                        month_str = month.upper()
                        fname_upper = fname.upper()
                        if (f"{day_str} {month_str}" in fname_upper or f"{day:02d} {month_str}" in fname_upper):
                            matched_name = fname
                            matched_bytes = fbytes
                            break

                # Fallback: jika hanya ada 1 tanggal dan 1 file
                if not matched_name and len(pivot_data) == 1 and len(available_files) == 1:
                    matched_name = list(available_files.keys())[0]
                    matched_bytes = list(available_files.values())[0]

                if matched_name and matched_bytes:
                    updated_bytes, preview_rows = update_workbook_with_data(matched_bytes, div_records)
                    
                    label = f"{day} {month} (Data: {ledger_date})" if day else ledger_date
                    new_results[label] = {
                        "file_name": matched_name,
                        "rows": preview_rows,
                        "bytes": updated_bytes,
                        "ledger_date": ledger_date
                    }
                    new_processed[matched_name] = updated_bytes

            st.session_state.results = new_results
            st.session_state.processed_files = new_processed

# Tampilkan Hasil Jika Sudah Diproses
if st.session_state.results:
    # 1. Ringkasan Metrik
    c1, c2, c3 = st.columns(3)
    total_dates = len(st.session_state.results)
    
    all_diffs = []
    for dinfo in st.session_state.results.values():
        for r in dinfo["rows"]:
            all_diffs.append(abs(r["diff"]))
    max_diff = max(all_diffs) if all_diffs else 0

    with c1:
        st.metric("Tanggal Diproses", f"{total_dates} Tanggal")
    with c2:
        st.metric("File Terhubung", f"{len(st.session_state.processed_files)} File")
    with c3:
        st.metric("Selisih Terbesar", f"±Rp {int(max_diff)}")

    st.markdown("### Pratinjau Hasil Per Tanggal")

    # Tab untuk masing-masing tanggal
    tab_labels = list(st.session_state.results.keys())
    tabs = st.tabs(tab_labels)

    for idx, tlabel in enumerate(tab_labels):
        with tabs[idx]:
            item = st.session_state.results[tlabel]
            st.caption(f"File Target: **{item['file_name']}**")

            # Format tabel
            table_data = []
            for r in item["rows"]:
                table_data.append({
                    "Divisi": r["div"],
                    "Sheet": r["sheet"],
                    "Neraca (I42)": f"{r['neraca']:,}".replace(",", "."),
                    "Koin": str(r["koin"]),
                    "Kertas": f"{r['kertas']:,}".replace(",", ".") if isinstance(r["kertas"], int) else str(r["kertas"]),
                    "Total Fisik": f"{r['fisik']:,}".replace(",", "."),
                    "Selisih": f"{r['diff']:+}" if r["diff"] != 0 else "0"
                })

            df_view = pd.DataFrame(table_data)
            st.table(df_view)

            # Tombol Unduh untuk File ini (mendukung Streamlit Cloud)
            st.download_button(
                label=f"Unduh {item['file_name']}",
                data=item["bytes"],
                file_name=item["file_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{idx}"
            )

    st.markdown("---")
    # Tombol Simpan Langsung ke Disk (khusus jika berjalan di lingkungan lokal)
    if os.path.exists("D:\\Downloads\\Kasir"):
        if st.button("Simpan Perubahan ke Seluruh File Excel di Folder Kerja"):
            saved_count = 0
            for fname, fbytes in st.session_state.processed_files.items():
                out_path = os.path.join("D:\\Downloads\\Kasir", fname)
                with open(out_path, "wb") as f:
                    f.write(fbytes)
                saved_count += 1
            st.success(f"Berhasil menyimpan perubahan pada {saved_count} file Excel di folder D:\\Downloads\\Kasir.")
else:
    st.info("Unggah file template opname di panel kiri dan masukkan data pivot nominal untuk memulai kalkulasi.")
