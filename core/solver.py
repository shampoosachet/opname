"""
Solver modul untuk menentukan pecahan fisik uang koin (E10:E13) dan uang kertas (E19:E25).
Aturan:
1. Pembulatan kelipatan 100 terdekat untuk meminimalkan selisih fisik vs buku besar.
2. Sisa ratusan (< Rp 1.000) dialokasikan ke koin (500 > 1000 > 200 > 100).
3. Jika sisa ratusan = 0, koin = 0 (seluruhnya dicover uang kertas).
4. Sisa ribuan dialokasikan secara proporsional ke pecahan uang kertas.
"""

COIN_DENOMS = {
    10: 1000,
    11: 500,
    12: 200,
    13: 100
}

NOTE_DENOMS = {
    19: 100000,
    20: 50000,
    21: 20000,
    22: 10000,
    23: 5000,
    24: 2000,
    25: 1000
}


def solve_coins(sub_thousand: int) -> dict:
    """
    Menghitung pecahan koin untuk sisa ratusan (< Rp 1.000).
    Hasil berupa dict {row_index: count}
    """
    coins = {10: None, 11: None, 12: None, 13: None}
    rem = sub_thousand % 1000

    if rem == 0:
        return coins

    # Pola deterministik optimal sub-1.000 dengan prioritas: 500 > 200 > 100
    patterns = {
        900: {11: 1, 12: 2},        # 500 + 400
        800: {11: 1, 12: 1, 13: 1}, # 500 + 200 + 100
        700: {11: 1, 12: 1},        # 500 + 200
        600: {11: 1, 13: 1},        # 500 + 100
        500: {11: 1},               # 500
        400: {12: 2},               # 200 x 2
        300: {12: 1, 13: 1},        # 200 + 100
        200: {12: 1},               # 200
        100: {13: 1}                # 100
    }

    if rem in patterns:
        for r, count in patterns[rem].items():
            coins[r] = count

    return coins


def solve_notes(target_notes: int) -> dict:
    """
    Menghitung pecahan kertas untuk target kelipatan 1.000 secara proporsional wajar.
    Hasil berupa dict {row_index: count}
    """
    notes = {19: None, 20: None, 21: None, 22: None, 23: None, 24: None, 25: None}
    if target_notes <= 0:
        return notes

    # Jika nominal kecil (< 50.000)
    if target_notes < 50000:
        rem = target_notes
        if rem >= 20000:
            c20 = rem // 20000
            notes[21] = c20
            rem -= c20 * 20000
        if rem >= 10000:
            notes[22] = 1
            rem -= 10000
        if rem >= 5000:
            notes[23] = 1
            rem -= 5000
        if rem >= 2000:
            c2 = rem // 2000
            notes[24] = c2
            rem -= c2 * 2000
        if rem >= 1000:
            notes[25] = rem // 1000
        return notes

    # Jika nominal sedang (50.000 - 1.000.000)
    if target_notes < 1000000:
        rem = target_notes
        c100 = max(0, (rem - 200000) // 100000) if rem >= 300000 else 0
        rem -= c100 * 100000

        c50 = max(1, rem // 100000) if rem >= 100000 else (1 if rem >= 50000 else 0)
        rem -= c50 * 50000

        c20 = max(1, (rem // 40000)) if rem >= 40000 else (1 if rem >= 20000 else 0)
        rem -= c20 * 20000

        c10 = max(1, (rem // 20000)) if rem >= 20000 else (1 if rem >= 10000 else 0)
        rem -= c10 * 10000

        c5 = max(1, (rem // 10000)) if rem >= 10000 else (1 if rem >= 5000 else 0)
        rem -= c5 * 5000

        c2 = (rem // 2000)
        if c2 > 0 and rem % 2000 == 1000:
            c2 -= 1
        rem -= c2 * 2000

        c1 = rem // 1000

        counts = [c100, c50, c20, c10, c5, c2, c1]
        for idx, row in enumerate([19, 20, 21, 22, 23, 24, 25]):
            notes[row] = counts[idx] if counts[idx] > 0 else None
        return notes

    # Jika nominal besar (> 1.000.000)
    # Target persentase wajar kasir:
    # 100k: ~70%, 50k: ~20%, 20k: ~7%, 10k: ~2%, 5k: ~0.6%, 2k: ~0.15%, 1k: sisa
    target = target_notes

    # Alokasi nominal kecil terlebih dahulu agar tidak kosong
    # 1k: ~10 - 20 lembar
    # 2k: ~15 - 35 lembar
    # 5k: ~20 - 60 lembar
    scale = min(1.5, target / 25000000)
    c5_base = max(4, int(25 * scale))
    c2_base = max(3, int(20 * scale))
    c1_base = max(3, int(10 * scale))

    rem = target - (c5_base * 5000 + c2_base * 2000 + c1_base * 1000)

    # 100k (~70%)
    target_100k = int(target * 0.70)
    c100 = max(1, target_100k // 100000)
    rem -= c100 * 100000

    # 50k (~19%)
    target_50k = int(target * 0.19)
    c50 = max(1, target_50k // 50000)
    rem -= c50 * 50000

    # 20k (~7%)
    target_20k = int(target * 0.07)
    c20 = max(1, target_20k // 20000)
    rem -= c20 * 20000

    # 10k (sisa menuju ribuan)
    c10 = max(1, rem // 10000)
    rem -= c10 * 10000

    # Distribusikan sisa kelipatan 1.000 ke pecahan kecil
    while rem > 0:
        if rem >= 50000:
            c50 += 1
            rem -= 50000
        elif rem >= 20000:
            c20 += 1
            rem -= 20000
        elif rem >= 10000:
            c10 += 1
            rem -= 10000
        elif rem >= 5000:
            c5_base += 1
            rem -= 5000
        elif rem >= 2000:
            c2_base += 1
            rem -= 2000
        else:
            c1_base += 1
            rem -= 1000

    counts = [c100, c50, c20, c10, c5_base, c2_base, c1_base]
    for idx, row in enumerate([19, 20, 21, 22, 23, 24, 25]):
        notes[row] = counts[idx] if counts[idx] > 0 else None

    return notes


def calculate_denominations(ledger_balance: float):
    """
    Fungsi utama kalkulasi:
    Mengembalikan: (target_fisik, selisih, coins_dict, notes_dict)
    """
    if ledger_balance is None or ledger_balance == 0:
        return 0, 0, {r: None for r in COIN_DENOMS}, {r: None for r in NOTE_DENOMS}

    # Pembulatan kelipatan 100 terdekat
    target_fisik = int(round(ledger_balance / 100.0) * 100)
    selisih = target_fisik - ledger_balance

    sub_thousand = target_fisik % 1000
    target_notes = target_fisik - sub_thousand

    coins = solve_coins(sub_thousand)
    notes = solve_notes(target_notes)

    # Verifikasi total fisik
    tot_coins = sum((coins[r] or 0) * COIN_DENOMS[r] for r in COIN_DENOMS)
    tot_notes = sum((notes[r] or 0) * NOTE_DENOMS[r] for r in NOTE_DENOMS)
    tot_cash = tot_coins + tot_notes

    # Jika ada deviasi, sesuaikan pada uang 1.000
    diff_check = target_fisik - tot_cash
    if diff_check != 0:
        notes[25] = (notes[25] or 0) + (diff_check // 1000)

    return target_fisik, selisih, coins, notes
