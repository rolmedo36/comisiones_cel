"""
Cálculo de comisiones de mayoreo desde NetSuite (SQLite) -> Excel ejecutivo.
Ahora con separación por vendedor.
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

# Campo que identifica al vendedor en la tabla
COLUMNA_VENDEDOR = "vendedor"

# Tasas de comisión por tipo de venta
COMISIONES = {
    "whatsapp": 0.10,  # 10%
    "mayoreo": 0.05,   # 5%
}

# Paleta ejecutiva
COLOR_PRIMARIO = "1F4E79"    # Azul corporativo oscuro
COLOR_SECUNDARIO = "2E75B6"  # Azul medio
COLOR_ACENTO = "D9E1F2"      # Azul claro (filas alternas)
COLOR_TOTAL = "FFF2CC"       # Amarillo suave (totales generales)
COLOR_SUBTOTAL = "E2EFDA"    # Verde suave (subtotales por vendedor)
COLOR_BLANCO = "FFFFFF"
COLOR_VENDEDOR_1 = "D6DCE4"  # Gris claro para alternar vendedores
COLOR_VENDEDOR_2 = "FFFFFF"  # Blanco


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

    # Validar que exista la columna vendedor
    if COLUMNA_VENDEDOR not in df.columns:
        raise ValueError(
            f"La columna '{COLUMNA_VENDEDOR}' no existe en la tabla. "
            f"Columnas disponibles: {list(df.columns)}"
        )

    # Normalizar tipo_venta y vendedor
    df["tipo_venta"] = df["tipo_venta"].astype(str).str.strip().str.lower()
    df[COLUMNA_VENDEDOR] = (
        df[COLUMNA_VENDEDOR]
        .astype(str)
        .str.strip()
        .str.title()  # Pone cada palabra con inicial mayúscula
    )

    # Convertir columnas numéricas
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")

    cant_nulos = df["cantidad"].isna().sum()
    rate_nulos = df["rate"].isna().sum()

    if cant_nulos > 0:
        warnings.warn(f"⚠️  {cant_nulos} registros tienen 'cantidad' inválida (se ignorarán)")
    if rate_nulos > 0:
        warnings.warn(f"⚠️  {rate_nulos} registros tienen 'rate' inválido (se ignorarán)")

    df = df[df["cantidad"].notna() & df["rate"].notna()].copy()

    if df.empty:
        raise ValueError("No hay registros válidos después de filtrar datos numéricos")

    # Calcular vendido y comisión
    df["vendido"] = df["cantidad"] * df["rate"]
    df["tasa"] = df["tipo_venta"].map(COMISIONES)
    df["comision"] = df["vendido"] * df["tasa"]

    # Filtrar solo tipos de venta relevantes
    df = df[df["tasa"].notna()].copy()

    # Etiquetas legibles
    df["tipo_venta_label"] = df["tipo_venta"].map(
        {"whatsapp": "WhatsApp (10%)", "mayoreo": "Mayoreo (5%)"}
    )

    return df


def construir_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen ejecutivo agrupado por Vendedor + Tipo de Venta."""
    resumen = (
        df.groupby([COLUMNA_VENDEDOR, "tipo_venta_label", "tasa"])
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

    # Orden: vendedor alfabético, luego 5% antes que 10%
    resumen = resumen.sort_values(
        [COLUMNA_VENDEDOR, "tasa"], ascending=[True, True]
    ).reset_index(drop=True)

    # Fila de totales generales
    totales = pd.DataFrame([{
        COLUMNA_VENDEDOR: "TOTAL GENERAL",
        "tipo_venta_label": "",
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
def construir_detalle_con_subtotales(df_detalle: pd.DataFrame) -> pd.DataFrame:
    """
    Construye un DataFrame de detalle ordenado por vendedor, con filas
    de SUBTOTAL por vendedor insertadas.
    """
    if df_detalle.empty:
        return df_detalle

    cols_base = [
        "fecha", "transaccion", "cliente", "ubicacion", COLUMNA_VENDEDOR,
        "id_articulo", "articulo", "cantidad", "rate",
        "vendido", "tasa", "comision",
    ]
    df = df_detalle[cols_base].copy()
    df = df.sort_values([COLUMNA_VENDEDOR, "fecha"], ascending=[True, False])

    # Construir filas con subtotales intercalados
    filas_finales = []
    for vendedor, grupo in df.groupby(COLUMNA_VENDEDOR, sort=False):
        # Agregar filas de datos
        for _, row in grupo.iterrows():
            filas_finales.append(row.to_dict())

        # Agregar fila de subtotal
        filas_finales.append({
            "fecha": None,
            "transaccion": None,
            "cliente": None,
            "ubicacion": None,
            COLUMNA_VENDEDOR: f"Subtotal {vendedor}",
            "id_articulo": None,
            "articulo": None,
            "cantidad": None,
            "rate": None,
            "vendido": grupo["vendido"].sum(),
            "tasa": None,
            "comision": grupo["comision"].sum(),
            "_es_subtotal": True,
        })

    df_final = pd.DataFrame(filas_finales)

    # Agregar fila TOTAL GENERAL al final
    df_final = pd.concat([
        df_final,
        pd.DataFrame([{
            "fecha": None,
            "transaccion": None,
            "cliente": None,
            "ubicacion": None,
            COLUMNA_VENDEDOR: "TOTAL GENERAL",
            "id_articulo": None,
            "articulo": None,
            "cantidad": None,
            "rate": None,
            "vendido": df["vendido"].sum(),
            "tasa": None,
            "comision": df["comision"].sum(),
            "_es_total": True,
        }])
    ], ignore_index=True)

    # Marcador para identificar subtotales/totales
    if "_es_subtotal" not in df_final.columns:
        df_final["_es_subtotal"] = False
    if "_es_total" not in df_final.columns:
        df_final["_es_total"] = False

    return df_final


def exportar_excel(df: pd.DataFrame, output_path: str) -> None:
    """Genera el Excel con 3 hojas formateadas."""
    resumen = construir_resumen(df)

    # Detalles con subtotales por vendedor
    detalle_5_raw = df[df["tasa"] == 0.05]
    detalle_10_raw = df[df["tasa"] == 0.10]

    detalle_5 = construir_detalle_con_subtotales(detalle_5_raw)
    detalle_10 = construir_detalle_con_subtotales(detalle_10_raw)

    # Renombrar columnas para presentación
    rename = {
        "fecha": "Fecha",
        "transaccion": "Transacción",
        "cliente": "Cliente",
        "ubicacion": "Ubicación",
        COLUMNA_VENDEDOR: "Vendedor",
        "id_articulo": "ID Artículo",
        "articulo": "Artículo",
        "cantidad": "Cantidad",
        "rate": "Precio Unitario",
        "vendido": "Vendido",
        "tasa": "Tasa",
        "comision": "Comisión",
    }

    rename_resumen = {
        COLUMNA_VENDEDOR: "Vendedor",
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
        detalle_5.drop(columns=["_es_subtotal", "_es_total"], errors="ignore").rename(
            columns=rename
        ).to_excel(writer, sheet_name="Detalle_5pct", index=False, startrow=2)
        detalle_10.drop(columns=["_es_subtotal", "_es_total"], errors="ignore").rename(
            columns=rename
        ).to_excel(writer, sheet_name="Detalle_10pct", index=False, startrow=2)

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

    subtotal_font = Font(name="Calibri", bold=True, color="375623", size=11)
    subtotal_fill = PatternFill(start_color=COLOR_SUBTOTAL, end_color=COLOR_SUBTOTAL, fill_type="solid")

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
        "subtotal_font": subtotal_font,
        "subtotal_fill": subtotal_fill,
        "title_font": title_font,
        "subtitle_font": subtitle_font,
        "thin_border": thin_border,
    }


def _formatear_hoja_resumen(ws, df_original):
    """Formato específico para la hoja de resumen."""
    estilos = _estilos_base()
    start_row = 3

    # Título y subtítulo
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ws.max_column)
    ws.cell(row=1, column=1, value="Resumen de Comisiones - Mayoreo").font = estilos["title_font"]

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ws.max_column)
    from datetime import datetime
    fecha_gen = datetime.now().strftime("%d-%b-%Y %H:%M")
    vendedores = df_original[COLUMNA_VENDEDOR].nunique()
    ws.cell(row=2, column=1, value=f"{vendedores} vendedores  |  Generado: {fecha_gen}").font = estilos["subtitle_font"]

    # Encabezados
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

        # Detectar fila TOTAL GENERAL
        if ws.cell(row=row_idx, column=1).value == "TOTAL GENERAL":
            for col_idx in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = estilos["total_font"]
                cell.fill = estilos["total_fill"]
                cell.border = Border(
                    left=Side(style="medium", color=COLOR_PRIMARIO),
                    right=Side(style="medium", color=COLOR_PRIMARIO),
                    top=Side(style="medium", color=COLOR_PRIMARIO),
                    bottom=Side(style="medium", color=COLOR_PRIMARIO),
                )
        else:
            # Filas alternas por vendedor
            vendedor_actual = ws.cell(row=row_idx, column=1).value
            vendedor_anterior = ws.cell(row=row_idx - 1, column=1).value if row_idx > start_row + 1 else None
            # Cambiar color cuando cambia de vendedor
            if vendedor_anterior is None or vendedor_actual != vendedor_anterior:
                # Detectar paridad del vendedor
                vendedores_unicos = df_original[COLUMNA_VENDEDOR].unique().tolist()
                try:
                    idx_vend = vendedores_unicos.index(vendedor_actual)
                    color = COLOR_VENDEDOR_1 if idx_vend % 2 == 0 else COLOR_VENDEDOR_2
                except ValueError:
                    color = COLOR_ACENTO
            # Aplicar color
            for col_idx in range(1, ws.max_column + 1):
                ws.cell(row=row_idx, column=col_idx).fill = PatternFill(
                    start_color=color, end_color=color, fill_type="solid"
                )

    _aplicar_formato_columnas_resumen(ws)
    _ajustar_ancho(ws)
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = f"A{start_row + 1}"


def _formatear_hoja_detalle(ws, df_original, titulo, subtitulo):
    """Formato específico para hojas de detalle con subtotales."""
    estilos = _estilos_base()
    start_row = 3

    # Título y subtítulo
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ws.max_column)
    ws.cell(row=1, column=1, value=titulo).font = estilos["title_font"]

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ws.max_column)
    from datetime import datetime
    fecha_gen = datetime.now().strftime("%d-%b-%Y %H:%M")
    ws.cell(row=2, column=1, value=f"{subtitulo}  |  Generado: {fecha_gen}").font = estilos["subtitle_font"]

    # Encabezados
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=start_row, column=col_idx)
        cell.font = estilos["header_font"]
        cell.fill = estilos["header_fill"]
        cell.alignment = estilos["header_align"]
        cell.border = estilos["thin_border"]

    # Identificar columnas de interés
    col_vendedor_idx = None
    col_vendido_idx = None
    col_comision_idx = None
    for col_idx in range(1, ws.max_column + 1):
        val = ws.cell(row=start_row, column=col_idx).value
        if val == "Vendedor":
            col_vendedor_idx = col_idx
        elif val == "Vendido":
            col_vendido_idx = col_idx
        elif val == "Comisión":
            col_comision_idx = col_idx

    # Recorrer filas y aplicar estilos diferenciados
    for row_idx in range(start_row + 1, ws.max_row + 1):
        vendedor_val = ws.cell(row=row_idx, column=col_vendedor_idx).value if col_vendedor_idx else ""
        vendedor_str = str(vendedor_val) if vendedor_val is not None else ""

        es_subtotal = vendedor_str.startswith("Subtotal ")
        es_total = vendedor_str == "TOTAL GENERAL"

        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = estilos["thin_border"]

            if es_total:
                cell.font = estilos["total_font"]
                cell.fill = estilos["total_fill"]
                cell.border = Border(
                    left=Side(style="medium", color=COLOR_PRIMARIO),
                    right=Side(style="medium", color=COLOR_PRIMARIO),
                    top=Side(style="medium", color=COLOR_PRIMARIO),
                    bottom=Side(style="medium", color=COLOR_PRIMARIO),
                )
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif es_subtotal:
                cell.font = estilos["subtotal_font"]
                cell.fill = estilos["subtotal_fill"]
                cell.border = Border(
                    left=Side(style="medium", color="548235"),
                    right=Side(style="medium", color="548235"),
                    top=Side(style="medium", color="548235"),
                    bottom=Side(style="medium", color="548235"),
                )
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                # Filas alternas
                if (row_idx - start_row) % 2 == 0:
                    cell.fill = PatternFill(
                        start_color=COLOR_ACENTO, end_color=COLOR_ACENTO, fill_type="solid"
                    )

    _aplicar_formato_columnas_detalle(ws)
    _ajustar_ancho(ws)

    # Auto-filter excluyendo la fila de total general
    last_data_row = ws.max_row - 1 if ws.max_row > start_row + 1 else ws.max_row
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(ws.max_column)}{last_data_row}"
    ws.freeze_panes = f"A{start_row + 1}"


def _aplicar_formato_columnas_resumen(ws):
    """Formato numérico para hoja de resumen."""
    moneda_fmt = '$#,##0.00'
    entero_fmt = '#,##0'

    for col_idx in range(1, ws.max_column + 1):
        header = ws.cell(row=3, column=col_idx).value
        for row_idx in range(4, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            if header in ("Total Vendido", "Total Comisión", "Ticket Promedio"):
                cell.number_format = moneda_fmt
                cell.alignment = Alignment(horizontal="right")
            elif header in ("# Transacciones", "# Ventas"):
                cell.number_format = entero_fmt
                cell.alignment = Alignment(horizontal="center")


def _aplicar_formato_columnas_detalle(ws):
    """Formato numérico para hojas de detalle."""
    moneda_fmt = '$#,##0.00'
    pct_fmt = '0%'

    for col_idx in range(1, ws.max_column + 1):
        header = ws.cell(row=3, column=col_idx).value
        for row_idx in range(4, ws.max_row + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            if header in ("Vendido", "Precio Unitario", "Comisión"):
                cell.number_format = moneda_fmt
                cell.alignment = Alignment(horizontal="right")
            elif header == "Tasa":
                cell.number_format = pct_fmt
                cell.alignment = Alignment(horizontal="center")
            elif header == "Cantidad":
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal="center")


def _ajustar_ancho(ws):
    """Ajusta el ancho de columnas al contenido."""
    for col_idx in range(1, ws.max_column + 1):
        max_len = 0
        col_letter = get_column_letter(col_idx)
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=False):
            for cell in row:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
        adjusted = min(max(max_len + 2, 10), 40)
        ws.column_dimensions[col_letter].width = adjusted


def _formatear_excel(path, resumen, detalle_5, detalle_10):
    """Carga el Excel y aplica formato a cada hoja."""
    wb = load_workbook(path)

    _formatear_hoja_resumen(wb["Resumen"], resumen)

    _formatear_hoja_detalle(
        wb["Detalle_5pct"], detalle_5,
        titulo="Detalle de Ventas - Mayoreo (5%)",
        subtitulo=f"{(detalle_10['_es_subtotal'] == False).sum() if '_es_subtotal' in detalle_10.columns else 0} registros"
    )

    _formatear_hoja_detalle(
        wb["Detalle_10pct"], detalle_10,
        titulo="Detalle de Ventas - WhatsApp (10%)",
        subtitulo=f"{(detalle_10['_es_subtotal'] == False).sum() if '_es_subtotal' in detalle_10.columns else 0} registros"
    )

    wb.move_sheet("Resumen", offset=-2)
    wb.save(path)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    try:
        df = cargar_ventas(DB_PATH, TABLE)
        print(f"📊 Registros cargados: {len(df)}")
        print(f"👥 Vendedores: {df[COLUMNA_VENDEDOR].nunique()} -> {df[COLUMNA_VENDEDOR].unique().tolist()}")
        print(f"   - WhatsApp (10%): {(df['tasa'] == 0.10).sum()}")
        print(f"   - Mayoreo (5%): {(df['tasa'] == 0.05).sum()}")
        exportar_excel(df, OUTPUT_EXCEL)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise