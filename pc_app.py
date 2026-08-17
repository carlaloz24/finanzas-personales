#!/usr/bin/env python3
"""Finanzas PC App — Reads finanzas-data.json from Google Drive and generates monthly Excel files."""

import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter as gcl
except ImportError:
    print("Instalando openpyxl...")
    os.system(f"{sys.executable} -m pip install openpyxl")
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter as gcl

MONTHS = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
          "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
SYNC_FILE = "finanzas-data.json"
SYNC_FOLDER = "Finanzas"
EXCEL_FOLDER = "Excel"

# Styles
BOLD = Font(name="Calibri", size=10, bold=True)
NORM = Font(name="Calibri", size=10)
HDR_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HDR_FILL = PatternFill(start_color="14140F", end_color="14140F", fill_type="solid")
ACCENT_FILL = PatternFill(start_color="F5F5EB", end_color="F5F5EB", fill_type="solid")
POS_FONT = Font(name="Calibri", size=10, bold=True, color="22C55E")
NEG_FONT = Font(name="Calibri", size=10, bold=True, color="EF4444")
INV_FONT = Font(name="Calibri", size=10, bold=True, color="7C6EF6")
THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(bottom=THIN)
EUR = '#,##0.00 "€"'
PCT = "0.0%"


def find_drive_folder():
    """Auto-detect Google Drive local folder."""
    home = Path.home()
    candidates = [
        home / "Google Drive" / "My Drive",
        home / "Google Drive",
        home / "Mi unidad",
        Path("G:/My Drive"),
        Path("G:/Mi unidad"),
    ]
    for p in candidates:
        sync = p / SYNC_FOLDER / SYNC_FILE
        if sync.exists():
            return p / SYNC_FOLDER
    # Check all drives on Windows
    if sys.platform == "win32":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            for sub in ["Google Drive/My Drive", "Google Drive/Mi unidad", "My Drive", "Mi unidad"]:
                p = Path(f"{letter}:/{sub}/{SYNC_FOLDER}/{SYNC_FILE}")
                if p.exists():
                    return p.parent
    return None


def read_sync_data(json_path):
    """Read and validate the sync JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("app") != "finanzas-personales":
        raise ValueError("Archivo no es de Finanzas Personales")
    return data


def get_months_with_data(data):
    """Get set of (year, month) tuples that have any transactions or values."""
    months = set()
    for tx in data.get("transactions", []):
        if tx.get("deleted"):
            continue
        months.add((tx.get("year"), tx.get("month")))
    for v in data.get("values", []):
        vid = v.get("id", "")
        if "-" in vid:
            parts = vid.split("-")
            try:
                months.add((int(parts[0]), int(parts[1])))
            except (ValueError, IndexError):
                pass
    return sorted(months)


def W(ws, r, c, val=None, font=None, nf=None, fill=None, align="left", border=None):
    """Write a cell."""
    cell = ws.cell(row=r, column=c, value=val)
    cell.font = font or NORM
    cell.alignment = Alignment(horizontal=align, vertical="center")
    if nf:
        cell.number_format = nf
    if fill:
        cell.fill = fill
    if border:
        cell.border = border
    return cell


def generate_month_excel(year, month, data, output_path):
    """Generate a complete Excel file for one month."""
    config = data.get("config", {})
    banks = config.get("banks", [])
    inv_types = config.get("inv_types", [])
    platforms = config.get("platforms", [])
    inc_cats = config.get("inc_categories", [])
    exp_cats = config.get("exp_categories", [])

    # Filter transactions for this month (exclude deleted)
    txs = [t for t in data.get("transactions", [])
           if t.get("year") == year and t.get("month") == month and not t.get("deleted")]
    ingresos = sorted([t for t in txs if t.get("type") == "ingreso"], key=lambda t: t.get("date", ""))
    gastos = sorted([t for t in txs if t.get("type") == "gasto"], key=lambda t: t.get("date", ""))
    inversiones = sorted([t for t in txs if t.get("type") == "inversion"], key=lambda t: t.get("date", ""))

    # Get values for this month
    val_id = f"{year}-{month}"
    values = next((v for v in data.get("values", []) if v.get("id") == val_id), {})

    # Get budget for this month
    budget = next((b for b in data.get("budgets", []) if b.get("id") == "main"), {})

    wb = openpyxl.Workbook()
    month_name = MONTHS[month] if 0 <= month < 12 else f"Mes {month}"

    # ═══ SHEET: Resumen ═══
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_properties.tabColor = "14140F"

    W(ws, 1, 1, f"{month_name.upper()} {year}", font=Font(name="Calibri", size=14, bold=True))
    W(ws, 2, 1, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", font=Font(name="Calibri", size=9, color="999999"))

    total_inc = sum(t.get("amount", 0) for t in ingresos)
    total_gas = sum(t.get("amount", 0) for t in gastos)
    total_inv = sum(t.get("amount", 0) for t in inversiones)
    balance = total_inc - total_gas
    tasa = (balance / total_inc * 100) if total_inc > 0 else 0

    # KPIs
    row = 4
    for lbl, val, fmt, ft in [
        ("Ingresos", total_inc, EUR, POS_FONT),
        ("Gastos", total_gas, EUR, NEG_FONT),
        ("Inversiones", total_inv, EUR, INV_FONT),
        ("Balance", balance, EUR, POS_FONT if balance >= 0 else NEG_FONT),
        ("Tasa de ahorro", tasa / 100, PCT, BOLD),
    ]:
        W(ws, row, 1, lbl, font=BOLD)
        W(ws, row, 2, val, font=ft, nf=fmt, align="right")
        row += 1

    # Liquidez
    row += 1
    W(ws, row, 1, "LIQUIDEZ", font=HDR_FONT, fill=HDR_FILL)
    W(ws, row, 2, "Saldo", font=HDR_FONT, fill=HDR_FILL, align="right")
    row += 1
    total_liq = 0
    bancos = values.get("bancos", {})
    for bank in banks:
        v = bancos.get(bank, 0)
        total_liq += v or 0
        W(ws, row, 1, bank, border=BORDER)
        W(ws, row, 2, v or 0, nf=EUR, align="right", border=BORDER)
        row += 1
    W(ws, row, 1, "TOTAL LIQUIDEZ", font=BOLD)
    W(ws, row, 2, total_liq, font=BOLD, nf=EUR, align="right")

    # Inversiones
    row += 2
    W(ws, row, 1, "INVERSIONES", font=HDR_FONT, fill=HDR_FILL)
    W(ws, row, 2, "Aportado", font=HDR_FONT, fill=HDR_FILL, align="right")
    W(ws, row, 3, "Valor real", font=HDR_FONT, fill=HDR_FILL, align="right")
    W(ws, row, 4, "Rent.", font=HDR_FONT, fill=HDR_FILL, align="right")
    row += 1
    inv_ap = values.get("inv_aportado", {})
    inv_re = values.get("inv_valor_real", {})
    total_ap = 0
    total_re = 0
    for inv in inv_types:
        ap = inv_ap.get(inv, 0) or 0
        re = inv_re.get(inv, 0) or 0
        total_ap += ap
        total_re += re
        rent = ((re - ap) / ap) if ap > 0 else 0
        W(ws, row, 1, inv, border=BORDER)
        W(ws, row, 2, ap, nf=EUR, align="right", border=BORDER)
        W(ws, row, 3, re, nf=EUR, align="right", border=BORDER)
        W(ws, row, 4, rent, nf=PCT, align="right", border=BORDER)
        row += 1
    total_rent = ((total_re - total_ap) / total_ap) if total_ap > 0 else 0
    W(ws, row, 1, "TOTAL", font=BOLD)
    W(ws, row, 2, total_ap, font=BOLD, nf=EUR, align="right")
    W(ws, row, 3, total_re, font=BOLD, nf=EUR, align="right")
    W(ws, row, 4, total_rent, font=BOLD, nf=PCT, align="right")

    # Patrimonio
    row += 2
    patrimonio = total_liq + total_re
    W(ws, row, 1, "PATRIMONIO NETO", font=Font(name="Calibri", size=12, bold=True))
    W(ws, row, 2, patrimonio, font=Font(name="Calibri", size=12, bold=True), nf=EUR, align="right")

    # Desglose gastos por categoria
    row += 2
    W(ws, row, 1, "GASTOS POR CATEGORIA", font=HDR_FONT, fill=HDR_FILL)
    W(ws, row, 2, "Importe", font=HDR_FONT, fill=HDR_FILL, align="right")
    if budget.get("gastos"):
        W(ws, row, 3, "Presupuesto", font=HDR_FONT, fill=HDR_FILL, align="right")
    row += 1
    gas_by_cat = {}
    for t in gastos:
        cat = t.get("category", "Otros")
        gas_by_cat[cat] = gas_by_cat.get(cat, 0) + t.get("amount", 0)
    for cat in exp_cats:
        amt = gas_by_cat.get(cat, 0)
        W(ws, row, 1, cat, border=BORDER)
        W(ws, row, 2, amt, nf=EUR, align="right", border=BORDER,
          font=NEG_FONT if amt > 0 else NORM)
        pres = budget.get("gastos", {}).get(cat, 0)
        if pres:
            W(ws, row, 3, pres, nf=EUR, align="right", border=BORDER)
        row += 1

    # Desglose ingresos por categoria
    row += 1
    W(ws, row, 1, "INGRESOS POR CATEGORIA", font=HDR_FONT, fill=HDR_FILL)
    W(ws, row, 2, "Importe", font=HDR_FONT, fill=HDR_FILL, align="right")
    row += 1
    inc_by_cat = {}
    for t in ingresos:
        cat = t.get("category", "Otros")
        inc_by_cat[cat] = inc_by_cat.get(cat, 0) + t.get("amount", 0)
    for cat in inc_cats:
        amt = inc_by_cat.get(cat, 0)
        W(ws, row, 1, cat, border=BORDER)
        W(ws, row, 2, amt, nf=EUR, align="right", border=BORDER,
          font=POS_FONT if amt > 0 else NORM)
        row += 1

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 12

    # ═══ SHEET: Ingresos ═══
    if ingresos:
        ws_inc = wb.create_sheet("Ingresos")
        ws_inc.sheet_properties.tabColor = "22C55E"
        headers = ["Fecha", "Banco", "Categoria", "Descripcion", "Importe"]
        for c, h in enumerate(headers, 1):
            W(ws_inc, 1, c, h, font=HDR_FONT, fill=HDR_FILL)
        for i, tx in enumerate(ingresos):
            r = i + 2
            W(ws_inc, r, 1, tx.get("date", ""), border=BORDER)
            W(ws_inc, r, 2, tx.get("bank", ""), border=BORDER)
            W(ws_inc, r, 3, tx.get("category", ""), border=BORDER)
            W(ws_inc, r, 4, tx.get("description", ""), border=BORDER)
            W(ws_inc, r, 5, tx.get("amount", 0), nf=EUR, align="right", border=BORDER, font=POS_FONT)
        r = len(ingresos) + 2
        W(ws_inc, r, 4, "TOTAL", font=BOLD)
        W(ws_inc, r, 5, total_inc, font=BOLD, nf=EUR, align="right")
        for c, w in [(1, 12), (2, 18), (3, 18), (4, 28), (5, 14)]:
            ws_inc.column_dimensions[gcl(c)].width = w

    # ═══ SHEET: Gastos ═══
    if gastos:
        ws_gas = wb.create_sheet("Gastos")
        ws_gas.sheet_properties.tabColor = "EF4444"
        headers = ["Fecha", "Banco", "Categoria", "Descripcion", "Importe"]
        for c, h in enumerate(headers, 1):
            W(ws_gas, 1, c, h, font=HDR_FONT, fill=HDR_FILL)
        for i, tx in enumerate(gastos):
            r = i + 2
            W(ws_gas, r, 1, tx.get("date", ""), border=BORDER)
            W(ws_gas, r, 2, tx.get("bank", ""), border=BORDER)
            W(ws_gas, r, 3, tx.get("category", ""), border=BORDER)
            W(ws_gas, r, 4, tx.get("description", ""), border=BORDER)
            W(ws_gas, r, 5, tx.get("amount", 0), nf=EUR, align="right", border=BORDER, font=NEG_FONT)
        r = len(gastos) + 2
        W(ws_gas, r, 4, "TOTAL", font=BOLD)
        W(ws_gas, r, 5, total_gas, font=BOLD, nf=EUR, align="right")
        for c, w in [(1, 12), (2, 18), (3, 18), (4, 28), (5, 14)]:
            ws_gas.column_dimensions[gcl(c)].width = w

    # ═══ SHEET: Inversiones ═══
    if inversiones:
        ws_inv = wb.create_sheet("Inversiones")
        ws_inv.sheet_properties.tabColor = "7C6EF6"
        headers = ["Fecha", "Plataforma", "Tipo", "Descripcion", "Importe"]
        for c, h in enumerate(headers, 1):
            W(ws_inv, 1, c, h, font=HDR_FONT, fill=HDR_FILL)
        for i, tx in enumerate(inversiones):
            r = i + 2
            W(ws_inv, r, 1, tx.get("date", ""), border=BORDER)
            W(ws_inv, r, 2, tx.get("platform", ""), border=BORDER)
            W(ws_inv, r, 3, tx.get("category", tx.get("tipo_inv", "")), border=BORDER)
            W(ws_inv, r, 4, tx.get("description", ""), border=BORDER)
            W(ws_inv, r, 5, tx.get("amount", 0), nf=EUR, align="right", border=BORDER, font=INV_FONT)
        r = len(inversiones) + 2
        W(ws_inv, r, 4, "TOTAL", font=BOLD)
        W(ws_inv, r, 5, total_inv, font=BOLD, nf=EUR, align="right")
        for c, w in [(1, 12), (2, 18), (3, 30), (4, 28), (5, 14)]:
            ws_inv.column_dimensions[gcl(c)].width = w

    wb.save(output_path)
    return True


def generate_annual_summary(year, data, output_path):
    """Generate an annual summary Excel with all months."""
    config = data.get("config", {})
    banks = config.get("banks", [])
    inv_types = config.get("inv_types", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen Anual"

    W(ws, 1, 1, f"RESUMEN ANUAL {year}", font=Font(name="Calibri", size=14, bold=True))

    # Headers
    W(ws, 3, 1, "MES", font=HDR_FONT, fill=HDR_FILL)
    for lbl, c in [("Ingresos", 2), ("Gastos", 3), ("Inversiones", 4),
                    ("Balance", 5), ("Ahorro %", 6), ("Patrimonio", 7)]:
        W(ws, 3, c, lbl, font=HDR_FONT, fill=HDR_FILL, align="right")

    totals = [0] * 5
    for m in range(12):
        row = 4 + m
        txs = [t for t in data.get("transactions", [])
               if t.get("year") == year and t.get("month") == m and not t.get("deleted")]
        inc = sum(t["amount"] for t in txs if t.get("type") == "ingreso")
        gas = sum(t["amount"] for t in txs if t.get("type") == "gasto")
        inv = sum(t["amount"] for t in txs if t.get("type") == "inversion")
        bal = inc - gas
        ahorro = (bal / inc) if inc > 0 else 0

        vals = next((v for v in data.get("values", []) if v.get("id") == f"{year}-{m}"), {})
        liq = sum((vals.get("bancos", {}).get(b, 0) or 0) for b in banks)
        inv_real = sum((vals.get("inv_valor_real", {}).get(t, 0) or 0) for t in inv_types)
        pat = liq + inv_real

        totals[0] += inc
        totals[1] += gas
        totals[2] += inv

        has_data = inc > 0 or gas > 0 or inv > 0 or pat > 0
        W(ws, row, 1, MONTHS[m], font=BOLD if has_data else NORM, border=BORDER)
        W(ws, row, 2, inc, nf=EUR, align="right", border=BORDER, font=POS_FONT if inc > 0 else NORM)
        W(ws, row, 3, gas, nf=EUR, align="right", border=BORDER, font=NEG_FONT if gas > 0 else NORM)
        W(ws, row, 4, inv, nf=EUR, align="right", border=BORDER, font=INV_FONT if inv > 0 else NORM)
        W(ws, row, 5, bal, nf=EUR, align="right", border=BORDER,
          font=POS_FONT if bal >= 0 else NEG_FONT)
        W(ws, row, 6, ahorro, nf=PCT, align="right", border=BORDER)
        W(ws, row, 7, pat, nf=EUR, align="right", border=BORDER, font=BOLD if pat > 0 else NORM)

    # Totals row
    row = 16
    total_bal = totals[0] - totals[1]
    total_ahorro = (total_bal / totals[0]) if totals[0] > 0 else 0
    W(ws, row, 1, "TOTAL", font=BOLD, fill=ACCENT_FILL)
    W(ws, row, 2, totals[0], font=BOLD, nf=EUR, align="right", fill=ACCENT_FILL)
    W(ws, row, 3, totals[1], font=BOLD, nf=EUR, align="right", fill=ACCENT_FILL)
    W(ws, row, 4, totals[2], font=BOLD, nf=EUR, align="right", fill=ACCENT_FILL)
    W(ws, row, 5, total_bal, font=BOLD, nf=EUR, align="right", fill=ACCENT_FILL)
    W(ws, row, 6, total_ahorro, font=BOLD, nf=PCT, align="right", fill=ACCENT_FILL)

    for c, w in [(1, 14), (2, 16), (3, 16), (4, 16), (5, 16), (6, 12), (7, 16)]:
        ws.column_dimensions[gcl(c)].width = w

    # Patrimonio evolution sheet
    ws2 = wb.create_sheet("Patrimonio")
    W(ws2, 1, 1, f"EVOLUCION PATRIMONIO {year}", font=Font(name="Calibri", size=14, bold=True))
    W(ws2, 3, 1, "MES", font=HDR_FONT, fill=HDR_FILL)
    W(ws2, 3, 2, "Liquidez", font=HDR_FONT, fill=HDR_FILL, align="right")
    W(ws2, 3, 3, "Inversiones", font=HDR_FONT, fill=HDR_FILL, align="right")
    W(ws2, 3, 4, "Patrimonio", font=HDR_FONT, fill=HDR_FILL, align="right")

    for m in range(12):
        row = 4 + m
        vals = next((v for v in data.get("values", []) if v.get("id") == f"{year}-{m}"), {})
        liq = sum((vals.get("bancos", {}).get(b, 0) or 0) for b in banks)
        inv_real = sum((vals.get("inv_valor_real", {}).get(t, 0) or 0) for t in inv_types)
        pat = liq + inv_real

        W(ws2, row, 1, MONTHS[m], border=BORDER)
        W(ws2, row, 2, liq, nf=EUR, align="right", border=BORDER)
        W(ws2, row, 3, inv_real, nf=EUR, align="right", border=BORDER, font=INV_FONT if inv_real > 0 else NORM)
        W(ws2, row, 4, pat, nf=EUR, align="right", border=BORDER, font=BOLD if pat > 0 else NORM)

    for c, w in [(1, 14), (2, 16), (3, 16), (4, 16)]:
        ws2.column_dimensions[gcl(c)].width = w

    wb.save(output_path)
    return True


def check_and_generate(drive_path):
    """Check for changes and generate/update Excel files."""
    json_path = drive_path / SYNC_FILE
    if not json_path.exists():
        print(f"No se encuentra {SYNC_FILE} en {drive_path}")
        return 0

    excel_dir = drive_path / EXCEL_FOLDER
    excel_dir.mkdir(exist_ok=True)

    data = read_sync_data(json_path)
    json_mtime = json_path.stat().st_mtime
    months = get_months_with_data(data)
    generated = 0

    for year, month in months:
        if year is None or month is None:
            continue
        month_name = MONTHS[month] if 0 <= month < 12 else f"Mes_{month}"
        filename = f"Finanzas_{year}_{month_name}.xlsx"
        filepath = excel_dir / filename

        needs_update = not filepath.exists() or filepath.stat().st_mtime < json_mtime
        if needs_update:
            try:
                generate_month_excel(year, month, data, filepath)
                print(f"  Generado: {filename}")
                generated += 1
            except Exception as e:
                print(f"  Error generando {filename}: {e}")

    # Generate annual summaries
    years = set(y for y, m in months if y is not None)
    for year in sorted(years):
        filename = f"Finanzas_{year}_Resumen.xlsx"
        filepath = excel_dir / filename
        needs_update = not filepath.exists() or filepath.stat().st_mtime < json_mtime
        if needs_update:
            try:
                generate_annual_summary(year, data, filepath)
                print(f"  Generado: {filename}")
                generated += 1
            except Exception as e:
                print(f"  Error generando {filename}: {e}")

    return generated


def run_gui():
    """Simple tkinter GUI."""
    try:
        import tkinter as tk
        from tkinter import filedialog, scrolledtext
    except ImportError:
        print("tkinter no disponible. Ejecutando en modo consola.")
        run_console()
        return

    drive_path = find_drive_folder()

    root = tk.Tk()
    root.title("Finanzas — Generador de Excel")
    root.geometry("550x400")
    root.configure(bg="#f5f5eb")

    frame = tk.Frame(root, bg="#f5f5eb", padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Finanzas — Excel", font=("Calibri", 18, "bold"),
             bg="#f5f5eb", fg="#14140f").pack(anchor="w")

    tk.Label(frame, text="Genera archivos Excel desde Google Drive",
             font=("Calibri", 11), bg="#f5f5eb", fg="#6e6e64").pack(anchor="w", pady=(0, 12))

    # Path selector
    path_frame = tk.Frame(frame, bg="#f5f5eb")
    path_frame.pack(fill=tk.X, pady=(0, 8))

    tk.Label(path_frame, text="Carpeta Finanzas:", font=("Calibri", 10, "bold"),
             bg="#f5f5eb", fg="#14140f").pack(side=tk.LEFT)

    path_var = tk.StringVar(value=str(drive_path) if drive_path else "No encontrada")
    path_entry = tk.Entry(path_frame, textvariable=path_var, font=("Calibri", 10),
                          bg="white", fg="#14140f", width=35)
    path_entry.pack(side=tk.LEFT, padx=(8, 4))

    def browse():
        d = filedialog.askdirectory(title="Selecciona la carpeta Finanzas en Google Drive")
        if d:
            path_var.set(d)

    tk.Button(path_frame, text="...", command=browse, font=("Calibri", 10),
              bg="#14140f", fg="white", width=3).pack(side=tk.LEFT)

    # Log
    log = scrolledtext.ScrolledText(frame, height=12, font=("Consolas", 9),
                                     bg="white", fg="#14140f", wrap=tk.WORD)
    log.pack(fill=tk.BOTH, expand=True, pady=(8, 8))

    def log_msg(msg):
        log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        log.see(tk.END)
        root.update_idletasks()

    def do_generate():
        p = Path(path_var.get())
        if not p.exists():
            log_msg(f"ERROR: Carpeta no encontrada: {p}")
            return
        json_path = p / SYNC_FILE
        if not json_path.exists():
            log_msg(f"ERROR: No se encuentra {SYNC_FILE} en {p}")
            return

        log_msg("Leyendo datos...")
        try:
            data = read_sync_data(json_path)
        except Exception as e:
            log_msg(f"ERROR: {e}")
            return

        months = get_months_with_data(data)
        log_msg(f"Encontrados {len(months)} meses con datos")

        excel_dir = p / EXCEL_FOLDER
        excel_dir.mkdir(exist_ok=True)
        json_mtime = json_path.stat().st_mtime
        generated = 0

        for year, month in months:
            if year is None or month is None:
                continue
            month_name = MONTHS[month] if 0 <= month < 12 else f"Mes_{month}"
            filename = f"Finanzas_{year}_{month_name}.xlsx"
            filepath = excel_dir / filename
            needs_update = not filepath.exists() or filepath.stat().st_mtime < json_mtime
            if needs_update:
                try:
                    generate_month_excel(year, month, data, filepath)
                    log_msg(f"Generado: {filename}")
                    generated += 1
                except Exception as e:
                    log_msg(f"Error: {filename} — {e}")

        years = set(y for y, m in months if y is not None)
        for year in sorted(years):
            filename = f"Finanzas_{year}_Resumen.xlsx"
            filepath = excel_dir / filename
            needs_update = not filepath.exists() or filepath.stat().st_mtime < json_mtime
            if needs_update:
                try:
                    generate_annual_summary(year, data, filepath)
                    log_msg(f"Generado: {filename}")
                    generated += 1
                except Exception as e:
                    log_msg(f"Error: {filename} — {e}")

        if generated == 0:
            log_msg("Todos los Excel estan actualizados")
        else:
            log_msg(f"Completado: {generated} archivo{'s' if generated != 1 else ''} generado{'s' if generated != 1 else ''}")

    watching = [False]
    watch_after_id = [None]

    def do_watch():
        if watching[0]:
            watching[0] = False
            if watch_after_id[0]:
                root.after_cancel(watch_after_id[0])
                watch_after_id[0] = None
            watch_btn.config(text="Vigilar cambios", bg="#14140f")
            log_msg("Vigilancia detenida")
            return

        watching[0] = True
        watch_btn.config(text="Detener vigilancia", bg="#ef4444")
        log_msg("Vigilando cambios cada 30 segundos...")

        last_mtime = [0]

        def check():
            if not watching[0]:
                return
            p = Path(path_var.get())
            json_path = p / SYNC_FILE
            if json_path.exists():
                mtime = json_path.stat().st_mtime
                if mtime > last_mtime[0]:
                    last_mtime[0] = mtime
                    if mtime > 0:
                        log_msg("Cambio detectado, regenerando...")
                        do_generate()
            watch_after_id[0] = root.after(30000, check)

        check()

    # Buttons
    btn_frame = tk.Frame(frame, bg="#f5f5eb")
    btn_frame.pack(fill=tk.X)

    tk.Button(btn_frame, text="Generar Excel", command=do_generate,
              font=("Calibri", 11, "bold"), bg="#beff50", fg="#14140f",
              padx=16, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=(0, 8))

    watch_btn = tk.Button(btn_frame, text="Vigilar cambios", command=do_watch,
                          font=("Calibri", 11, "bold"), bg="#14140f", fg="white",
                          padx=16, pady=6, cursor="hand2")
    watch_btn.pack(side=tk.LEFT)

    if drive_path:
        log_msg(f"Carpeta detectada: {drive_path}")
    else:
        log_msg("Carpeta Google Drive no detectada. Seleccionala manualmente.")

    root.mainloop()


def run_console():
    """Console mode — generate once."""
    drive_path = find_drive_folder()
    if not drive_path:
        print("No se encontro la carpeta Finanzas en Google Drive.")
        path = input("Introduce la ruta manualmente: ").strip()
        if not path:
            return
        drive_path = Path(path)

    print(f"Carpeta: {drive_path}")
    n = check_and_generate(drive_path)
    if n == 0:
        print("Todos los Excel estan actualizados.")
    else:
        print(f"Generados {n} archivos Excel.")


if __name__ == "__main__":
    if "--console" in sys.argv:
        run_console()
    else:
        run_gui()
