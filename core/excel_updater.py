"""
Modul pembaruan file Excel opname.
Mengisi cell I42 (Neraca), E10:E13 (Koin), dan E19:E25 (Kertas).
Sheet 'BA KAS KECIL' dan 'BA BG-CEK' diproteksi penuh dan tidak disentuh.
Mendukung pemrosesan in-memory (BytesIO) untuk Streamlit Cloud.
"""

import io
import openpyxl
from core.solver import calculate_denominations, COIN_DENOMS, NOTE_DENOMS

DIVISION_SHEET_CANDIDATES = {
    "02/01": ["KBT PG 01", "KBT PG01", "KBT PG"],
    "02/04": ["KBT Ceres 04", "KBT Ceres04", "KBT Ceres"],
    "02/25": ["KBT Philips 25", "KBT Philips25", "KBT Philips"],
    "02/26": ["KBT Reckitt 26", "KBT Reckitt26", "KBT Reckitt"],
    "02/35": ["KBT PDA 35", "KBT PDA35", "KBT PDA"],
    "02/42": ["KBT APL 38", "KBT APL38", "KBT APL"],
    "02/A1": ["KBT KAS ", "KBT KAS A1 ", "KBT KAS A1", "KBT KAS"]
}

PROTECTED_SHEETS = {"BA KAS KECIL", "BA BG-CEK", "KAS KECIL", "BG-CEK", "BG/CEK"}


def find_matching_sheet(wb, candidates):
    sheet_names = wb.sheetnames
    # 1. Exact match
    for cand in candidates:
        if cand in sheet_names:
            return cand
    # 2. Case-insensitive / whitespace stripped match
    clean_sheets = {s.strip().lower(): s for s in sheet_names}
    for cand in candidates:
        c_clean = cand.strip().lower()
        if c_clean in clean_sheets:
            return clean_sheets[c_clean]
    return None


def update_workbook_with_data(excel_source, division_data: dict):
    """
    excel_source: str (file_path) atau bytes / BytesIO
    division_data: dict {"02/01": 58349009, ...}
    
    Mengembalikan: (processed_bytes, preview_rows)
    """
    if isinstance(excel_source, str):
        wb = openpyxl.load_workbook(excel_source)
    elif isinstance(excel_source, (bytes, bytearray)):
        wb = openpyxl.load_workbook(io.BytesIO(excel_source))
    else:
        excel_source.seek(0)
        wb = openpyxl.load_workbook(io.BytesIO(excel_source.read()))

    preview_rows = []

    # Iterasi setiap divisi yang terdaftar di sistem
    for div_code, candidates in DIVISION_SHEET_CANDIDATES.items():
        sheet_name = find_matching_sheet(wb, candidates)
        if not sheet_name:
            continue

        # Pastikan tidak menyentuh sheet terproteksi
        if sheet_name in PROTECTED_SHEETS:
            continue

        ws = wb[sheet_name]

        # Ambil nominal dari input data (jika tidak ada di data, set 0)
        ledger_balance = division_data.get(div_code, 0.0)

        # Hitung pecahan
        target_fisik, selisih, coins, notes = calculate_denominations(ledger_balance)

        # 1. Update Cell I42 (Saldo Buku Besar / Neraca)
        ws["I42"].value = int(ledger_balance) if ledger_balance.is_integer() else ledger_balance

        # 2. Update Koin (E10:E13)
        for r, val in coins.items():
            ws.cell(r, 5).value = val

        # 3. Update Kertas (E19:E25)
        for r, val in notes.items():
            ws.cell(r, 5).value = val

        tot_coins = sum((coins[r] or 0) * COIN_DENOMS[r] for r in COIN_DENOMS)
        tot_notes = sum((notes[r] or 0) * NOTE_DENOMS[r] for r in NOTE_DENOMS)

        preview_rows.append({
            "div": div_code,
            "sheet": sheet_name,
            "neraca": int(ledger_balance),
            "koin": tot_coins if tot_coins > 0 else "-",
            "kertas": tot_notes if tot_notes > 0 else "-",
            "fisik": target_fisik,
            "diff": selisih
        })

    # Simpan ke BytesIO
    output_stream = io.BytesIO()
    wb.save(output_stream)
    output_stream.seek(0)

    return output_stream.getvalue(), preview_rows
