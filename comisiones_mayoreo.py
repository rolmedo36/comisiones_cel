"""
Cálculo de comisiones de mayoreo desde NetSuite (SQLite) -> Excel ejecutivo.
Requiere: pandas, openpyxl
    pip install pandas openpyxl
"""

import sqlite3
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter
import warnings

# =========================
# CONFIGURACIÓN
# =========================
DB_PATH = "comisiones.db"
TABLE = "ventas_mayoreo"
OUTPUT_EXCEL = "Comisiones_Mayoreo.xlsx"

# Tasas de comisión por tipo de venta (normalizadas a minúsculas)
COMISIONES = {
    "whatsapp": 0.10,  # 10%
    "mayoreo": 0.05,  # 5%
}

# Mapeo de nombres amigables para las hojas
NOMBRES_HOJA = {
    "whatsapp": "Detalle_10pct",
    "mayoreo": "Detalle_5pct",
}

# Paleta ejecutiva
COLOR_PRIMARIO = "1F4E79"  # Azul corporativo oscuro
COLOR_SECUNDARIO = "2E75B6"  # Azul medio
COLOR_ACENTO = "D9E1F2"  # Azul claro (filas alternas)
COLOR_TOTAL = "FFF2CC"  # Amarillo suave (totales)
COLOR_BLANCO = "FFFFFF"
COLOR_VERDE = "548235"  # Para la columna de comisión


# =========================
# 1. EXTRACCIÓN Y CÁLCULO
# =========================
def cargar_ventas(db_path: str, table: str) -> pd.DataFrame:
    """Lee la tabla de ventas desde SQLite y convierte columnas numéricas."""
    conn = sqlite3.connect(db_path)
    try:
        query = f"SELECT * FROM {table}"
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    if df.empty:
        raise ValueError(f"No hay datos en la tabla {table}")

    # Normalizar tipo_venta: minúsculas y sin espacios extra
    df["tipo_venta"] = df["tipo_venta"].astype(str).str.strip().str.lower()

    # ====== CORRECCIÓN: Convertir columnas numéricas ======
    # Convertir cantidad a numérico (coerce convierte errores a NaN)
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")

    # Convertir rate a numérico
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")

    # Reportar valores problemáticos
    cant_nulos = df["cantidad"].isna().sum()
    rate_nulos = df["rate"].isna().sum()

    if cant_nulos > 0:
        warnings.warn(f"⚠️  {cant_nulos} registros tienen 'cantidad' inválida (se ignorarán)")
    if rate_nulos > 0:
        warnings.warn(f"⚠️  {rate_nulos} registros tienen 'rate' inválido (se ignorarán)")

    # Filtrar registros con datos numéricos válidos
    df = df[df["cantidad"].notna() & df["rate"].notna()].copy()

    if df.empty:
        raise ValueError("No hay registros válidos después de filtrar datos numéricos")

    # Calcular vendido y comisión
    df["vendido"] = df["cantidad"] * df["rate"]

    # Mapear tasa según tipo_venta (NaN si no es WhatsApp ni Mayoreo)
    df["tasa"] = df["tipo_venta"].map(COMISIONES)
    df["comision"] = df["vendido"] * df["tasa"]

    # Filtrar solo los tipos de venta relevantes
    df = df[df["tasa"].notna()].copy()

    # Columna legible de tipo de venta
    df["tipo_venta_label"] = df["tipo_venta"].map(
        {"whatsapp": "WhatsApp (10%)", "mayoreo": "Mayoreo (5%)"}
    )

    return df


def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen ejecutivo agrupado por tasa de comisión."""
    resumen = (
        df.groupby(["tipo_venta_label", "tasa"])
        .agg(
            num_transacciones=("transaccion", "nunique"),
            num_ventas=("transaccion", "count"),
            total_vendido=("vendido", "sum"),
            total_comision=("comision", "sum"),
        )
        .reset_index()
    )
    resumen["tasa_pct"] = resumen["tasa"].apply(lambda x: f"{int(x * 100)}%")
    resumen["ticket_promedio"] = resumen["total_vendido"] / resumen["num_ventas"]

    # Orden: 5% primero, 10% después
    resumen = resumen.sort_values("tasa").reset_index(drop=True)

    # Fila de totales
    totales = pd.DataFrame([{
        "tipo_venta_label": "TOTAL GENERAL",
        "tasa": None,
        "tasa_pct": "",
        "num_transacciones": resumen["num_transacciones"].sum(),
        "num_ventas": resumen["num_ventas"].sum(),
        "total_vendido": resumen["total_vendido"].sum(),
        "total_comision": resumen["total_comision"].sum(),
        "ticket_promedio": (
            resumen["total_vendido"].sum() / resumen["num_ventas"].sum()
            if resumen["num_ventas"].sum() > 0 else 0
        ),
    }])
    return pd.concat([resumen, totales], ignore_index=True)


# =========================
# 2. EXPORTACIÓN A EXCEL
# =========================
def exportar_excel(df: pd.DataFrame, output_path: str) -> None:
    """Genera el Excel con 3 hojas formateadas."""
    resumen = construir_resumen(df)

    # DataFrames por hoja de detalle
    cols_detalle = [
        "fecha", "transaccion", "cliente", "ubicacion",
        "id_articulo", "articulo", "cantidad", "rate",
        "vendido", "tasa", "comision",
    ]
    detalle_5 = df[df["tasa"] == 0.05][cols_detalle].copy()
    detalle_10 = df[df["tasa"] == 0.10][cols_detalle].copy()

    # Ordenar por fecha descendente
    for d in (detalle_5, detalle_10):
        d.sort_values("fecha", ascending=False, inplace=True)

    # Renombrar columnas para presentación ejecutiva
    rename = {
        "fecha": "Fecha",
        "transaccion": "Transacción",
        "cliente": "Cliente",
        "ubicacion": "Ubicación",
        "id_articulo": "ID Artículo",
        "articulo": "Artículo",
        "cantidad": "Cantidad",
        "rate": "Precio Unitario",
        "vendido": "Vendido",
        "tasa": "Tasa",
        "comision": "Comisión",
    }

    rename_resumen = {
        "tipo_venta_label": "Tipo de Venta",
        "tasa_pct": "Tasa",
        "num_transacciones": "# Transacciones",
        "num_ventas": "# Ventas",
        "total_vendido": "Total Vendido",
        "total_comision": "Total Comisión",
        "ticket_promedio": "Ticket Promedio",
    }

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        resumen.rename(columns=rename_resumen).to_excel(
            writer, sheet_name="Resumen", index=False, startrow=2
        )
        detalle_5.rename(columns=rename).to_excel(
            writer, sheet_name="Detalle_5pct", index=False, startrow=2
        )
        detalle_10.rename(columns=rename).to_excel(
            writer, sheet_name="Detalle_10pct", index=False, startrow=2
        )

    # Aplicar formato ejecutivo
    _formatear_excel(output_path, resumen, detalle_5, detalle_10)
    print(f"✅ Excel generado: {Path(output_path).resolve()}")


# =========================
# 3. FORMATO EJECUTIVO
# =========================
def _estilos_base():
    """Retorna los estilos reutilizables."""
    header_font = Font(name="Calibri", bold=True, color=COLOR_BLANCO, size=11)
    header_fill = PatternFill(start_color=COLOR_PRIMARIO, end_color=COLOR_PRIMARIO, fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    total_font = Font(name="Calibri", bold=True, color=COLOR_PRIMARIO, size=11)
    total_fill = PatternFill(start_color=COLOR_TOTAL, end_color=COLOR_TOTAL, fill_type="solid")

    title_font = Font(name="Calibri", bold=True, color=COLOR_PRIMARIO, size=16)
    subtitle_font = Font(name="Calibri", italic=True, color=COLOR_SECUNDARIO, size=10)

    thin_border = Border(
        left=Side(style="thin", color="B4C6E7"),
        right=Side(style="thin", color="B4C6E7"),
        top=Side(style="thin", color="B4C6E7"),
        bottom=Side(style="thin", color="B4C6E7"),
    )
    return {
        "header_font": header_font,
        "header_fill": header_fill,
        "header_align": header_align,
        "total_font": total_font,
        "total_fill": total_fill,
        "title_font": title_font,
        "subtitle_font": subtitle_font,
        "thin_border": thin_border,
    }


def _formatear_hoja(ws, df_original, es_resumen=False, titulo="", subtitulo=""):
    """Aplica formato ejecutivo a una hoja."""
    estilos = _estilos_base()
    start_row = 3  # los datos empiezan en fila 3 (encabezados en fila 3)

    # Título y subtítulo
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ws.max_column)
    ws.cell(row=1, column=1, value=titulo).font = estilos["title_font"]
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="left", vertical="center")

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ws.max_column)
    from datetime import datetime
    fecha_gen = datetime.now().strftime("%d-%b-%Y %H:%M")
    ws.cell(row=2, column=1, value=f"{subtitulo}  |  Generado: {fecha_gen}").font = estilos["subtitle_font"]

    # Encabezados (fila 3)
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=start_row, column=col_idx)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = estilos["header_align"]
        cell.border = estilos["thin_border"]

    # Filas de datos
    for row_idx in range(start_row + 1, ws.max_row + 1):
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = estilos["thin_border"]
            cell.alignment = Alignment(horizontal="center", vertical="center")
            # Filas alternas
            if (row_idx - start_row) % 2 == 0:
                cell.fill = PatternFill(
                    start_color=COLOR_ACENTO, end_color=COLOR_ACENTO, fill_type="solid"
                )

    # Fila de totales (solo si es resumen o detalle)
    if es_resumen:
        _aplicar_totales_resumen(ws, df_original, estilos)
    else:
        _aplicar_totales_detalle(ws, df_original, estilos)

    # Formato de números por columna
    _aplicar_formato_columnas(ws, es_resumen)

    # Ajuste de ancho
    _ajustar_ancho(ws)

    # Filtros y paneles congelados
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = f"A{start_row + 1}"


def _aplicar_totales_resumen(ws, df, estilos):
    """Resalta la fila TOTAL GENERAL en el resumen."""
    total_row = None
    for row_idx in range(4, ws.max_row + 1):
        if ws.cell(row=row_idx, column=1).value == "TOTAL GENERAL":
            total_row = row_idx
            break
    if total_row:
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=total_row, column=col_idx)
            cell.font = estilos["total_font"]
            cell.fill = estilos["total_fill"]
            cell.border = Border(
                left=Side(style="medium", color=COLOR_PRIMARIO),
                right=Side(style="medium", color=COLOR_PRIMARIO),
                top=Side(style="medium", color=COLOR_PRIMARIO),
                bottom=Side(style="medium", color=COLOR_PRIMARIO),
            )


def _agregar_fila_totales(ws, df, estilos, col_vendido_idx, col_comision_idx):
    """Agrega una fila de totales al final del detalle."""
    total_row = ws.max_row + 1
    ws.cell(row=total_row, column=1, value="TOTAL").font = estilos["total_font"]
    ws.cell(row=total_row, column=col_vendido_idx, value=df["vendido"].sum())
    ws.cell(row=total_row, column=col_comision_idx, value=df["comision"].sum())

    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=total_row, column=col_idx)
        cell.font = estilos["total_font"]
        cell.fill = estilos["total_fill"]
        cell.border = Border(
            left=Side(style="medium", color=COLOR_PRIMARIO),
            right=Side(style="medium", color=COLOR_PRIMARIO),
            top=Side(style="medium", color=COLOR_PRIMARIO),
            bottom=Side(style="medium", color=COLOR_PRIMARIO),
        )


def _aplicar_totales_detalle(ws, df, estilos):
    """Agrega fila de totales en hojas de detalle."""
    # Identificar columnas Vendido y Comisión por nombre de encabezado
    col_vendido = col_comision = None
    for col_idx in range(1, ws.max_column + 1):
        val = ws.cell(row=3, column=col_idx).value
        if val == "Vendido":
            col_vendido = col_idx
        elif val == "Comisión":
            col_comision = col_idx
    if col_vendido and col_comision:
        _agregar_fila_totales(ws, df, estilos, col_vendido, col_comision)


def _aplicar_formato_columnas(ws, es_resumen):
    """Aplica formato de moneda/porcentaje a columnas específicas."""
    moneda_fmt = '$#,##0.00'
    pct_fmt = '0%'

    for col_idx in range(1, ws.max_column + 1):
        header = ws.cell(row=3, column=col_idx).value
        if header in ("Vendido", "Total Vendido", "Precio Unitario", "Ticket Promedio", "Comisión", "Total Comisión"):
            for row_idx in range(4, ws.max_row + 1):
                ws.cell(row=row_idx, column=col_idx).number_format = moneda_fmt
                # Alineación a la derecha para números
                ws.cell(row=row_idx, column=col_idx).alignment = Alignment(horizontal="right")
        elif header in ("Tasa",) and not es_resumen:
            for row_idx in range(4, ws.max_row + 1):
                ws.cell(row=row_idx, column=col_idx).number_format = pct_fmt
                ws.cell(row=row_idx, column=col_idx).alignment = Alignment(horizontal="center")
        elif header == "Cantidad":
            for row_idx in range(4, ws.max_row + 1):
                ws.cell(row=row_idx, column=col_idx).number_format = '#,##0'
                ws.cell(row=row_idx, column=col_idx).alignment = Alignment(horizontal="center")


def _ajustar_ancho(ws):
    """Ajusta el ancho de columnas al contenido."""
    for col_idx in range(1, ws.max_column + 1):
        max_len = 0
        col_letter = get_column_letter(col_idx)
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=False):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        # Mínimo 10, máximo 40
        adjusted = min(max(max_len + 2, 10), 40)
        ws.column_dimensions[col_letter].width = adjusted


def _formatear_excel(path, resumen, detalle_5, detalle_10):
    """Carga el Excel y aplica formato a cada hoja."""
    wb = load_workbook(path)

    _formatear_hoja(
        wb["Resumen"], resumen, es_resumen=True,
        titulo="Resumen de Comisiones - Mayoreo",
        subtitulo="Consolidado por tipo de venta"
    )
    _formatear_hoja(
        wb["Detalle_5pct"], detalle_5, es_resumen=False,
        titulo="Detalle de Ventas - Mayoreo (5%)",
        subtitulo=f"{len(detalle_5)} registros"
    )
    _formatear_hoja(
        wb["Detalle_10pct"], detalle_10, es_resumen=False,
        titulo="Detalle de Ventas - WhatsApp (10%)",
        subtitulo=f"{len(detalle_10)} registros"
    )

    # Mover Resumen al inicio
    wb.move_sheet("Resumen", offset=-2)

    wb.save(path)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    try:
        df = cargar_ventas(DB_PATH, TABLE)
        print(f"📊 Registros cargados: {len(df)}")
        print(f"   - WhatsApp (10%): {(df['tasa'] == 0.10).sum()}")
        print(f"   - Mayoreo (5%): {(df['tasa'] == 0.05).sum()}")
        exportar_excel(df, OUTPUT_EXCEL)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise