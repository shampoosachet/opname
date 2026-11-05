"""
Parser modul untuk mengekstrak data tabel pivot per tanggal (clipboard / file).
Mendukung format compact dengan sel tanggal kosong di bawah tanggal utama (forward-fill).
"""

import re
import io
import pandas as pd
from datetime import datetime, timedelta

MONTH_NAMES_ID = {
    1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL",
    5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS",
    9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER"
}


def clean_number(val):
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = re.sub(r"[^\d\.\,\-]", "", s)
    if not s:
        return 0.0
    # Jika menggunakan format Indonesia/Eropa: 58.349.009 atau 58,349,009
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts[-1]) == 3:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif "." in s and "," not in s:
        parts = s.split(".")
        if len(parts[-1]) == 3:
            s = s.replace(".", "")
    elif "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_pivot_text(text: str):
    """
    Membaca data pivot dari teks (clipboard paste).
    Mengembalikan dict {ledger_date: {division_code: total}}
    """
    raw_lines = text.splitlines()
    lines = [line.rstrip("\r\n") for line in raw_lines if line.strip()]
    if not lines:
        return {}

    # Cek apakah delimiter tab ada di teks
    if "\t" in "\n".join(lines):
        sep = "\t"
    elif ";" in "\n".join(lines):
        sep = ";"
    elif "," in "\n".join(lines):
        sep = ","
    else:
        sep = None

    if sep:
        try:
            df = pd.read_csv(io.StringIO("\n".join(lines)), sep=sep, header=None, dtype=str)
        except Exception:
            # Fallback manual split
            data = [l.split(sep) for l in lines]
            df = pd.DataFrame(data)
    else:
        # Regex split jika spasi ganda
        data = [re.split(r"\s{2,}", l.strip()) for l in lines]
        df = pd.DataFrame(data)

    return process_dataframe(df)


def parse_pivot_file(uploaded_file):
    """
    Membaca file upload (Excel atau CSV).
    """
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, dtype=str, header=None)
    else:
        df = pd.read_excel(uploaded_file, dtype=str, header=None)
    return process_dataframe(df)


def process_dataframe(df: pd.DataFrame):
    """
    Memproses DataFrame, mendeteksi kolom:
    Kolom 0: Tanggal (dengan sel kosong di-ffill)
    Kolom 1: Divisi (02/01, dsb)
    Kolom 2: Total
    """
    if df.empty:
        return {}

    # Cari baris header jika ada
    start_row = 0
    for r_idx in range(min(5, len(df))):
        row_vals = [str(v).lower() for v in df.iloc[r_idx].values if pd.notna(v)]
        if any("tgl" in v or "tanggal" in v or "date" in v for v in row_vals):
            start_row = r_idx + 1
            break

    data_df = df.iloc[start_row:].copy().reset_index(drop=True)

    # Kolom mapping
    num_cols = data_df.shape[1]
    if num_cols >= 3:
        col_tgl_idx = 0
        col_div_idx = 1
        col_tot_idx = 2
    elif num_cols == 2:
        col_tgl_idx = None
        col_div_idx = 0
        col_tot_idx = 1
    else:
        return {}

    records = {}
    current_date = "DEFAULT"

    for _, row in data_df.iterrows():
        tgl_raw = row[col_tgl_idx] if col_tgl_idx is not None else None
        div_raw = row[col_div_idx] if pd.notna(row[col_div_idx]) else ""
        tot_raw = row[col_tot_idx] if pd.notna(row[col_tot_idx]) else None

        tgl_str = str(tgl_raw).strip() if pd.notna(tgl_raw) and str(tgl_raw).strip() not in ["nan", "None", ""] else ""
        div_str = str(div_raw).strip()

        # Deteksi jika ada format tanggal
        date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})|(\d{1,2}[-/]\d{1,2}[-/]\d{4})", tgl_str)
        if date_match:
            current_date = date_match.group(0)

        # Abaikan baris header atau kosong
        if not div_str or div_str.lower() in ["nan", "none", "", "divisi"]:
            continue

        num_val = clean_number(tot_raw)

        if current_date not in records:
            records[current_date] = {}

        # Normalisasi kode divisi
        div_norm = div_str
        div_m = re.match(r"^(02)/?0?([0-9A-Za-z]+)", div_str)
        if div_m:
            prefix, code = div_m.groups()
            if len(code) == 1 and code.isdigit():
                code = f"0{code}"
            div_norm = f"{prefix}/{code.upper()}"

        records[current_date][div_norm] = num_val

    return records


def get_opname_date_info(ledger_date_str: str):
    """
    Menghitung tanggal opname (T + 1) dari tanggal ledger.
    Mengembalikan: (opname_date_obj, day_num, month_name, search_pattern)
    """
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(ledger_date_str, fmt)
            break
        except ValueError:
            dt = None

    if not dt:
        return None, None, None, None

    opname_dt = dt + timedelta(days=1)
    day = opname_dt.day
    month = MONTH_NAMES_ID.get(opname_dt.month, "")
    year = opname_dt.year
    pattern = f"{day} {month} {year}"

    return opname_dt, day, month, pattern
