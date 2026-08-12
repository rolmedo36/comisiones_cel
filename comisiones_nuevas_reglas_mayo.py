import sqlite3
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# 1. CONFIGURACIÓN DE REGLAS DE NEGOCIO
# ==============================================================================
CONFIG_COMISIONES = {
    "mes_a_calcular": 7,
    "grupo_pastillas_ids": [5356, 4445, 1165, 1164],
    "marcas_premium": ["CXO", "CXO: B"],
    "marca_dusa": "DUSA",
    "porcentaje_pastillas": 0.06,
    "porcentaje_cxo": 0.06,
    "porcentaje_dusa": 0.02,
    "porcentaje_resto": 0.01
}


def obtener_nombre_comision(id_art, marca):
    try:
        id_art = int(id_art)
    except (ValueError, TypeError):
        pass

    if id_art in CONFIG_COMISIONES["grupo_pastillas_ids"]:
        return "Grupo Pastillas (6%)"
    elif marca in CONFIG_COMISIONES["marcas_premium"]:
        return "CXO (6%)"
    elif marca == CONFIG_COMISIONES["marca_dusa"]:
        return "Marca DUSA (2%)"
    else:
        return "General Resto (1%)"


def calcular_porcentaje_fila(id_art, marca):
    try:
        id_art = int(id_art)
    except (ValueError, TypeError):
        pass

    if id_art in CONFIG_COMISIONES["grupo_pastillas_ids"]:
        return CONFIG_COMISIONES["porcentaje_pastillas"]
    elif marca in CONFIG_COMISIONES["marcas_premium"]:
        return CONFIG_COMISIONES["porcentaje_cxo"]
    elif marca == CONFIG_COMISIONES["marca_dusa"]:
        return CONFIG_COMISIONES["porcentaje_dusa"]
    else:
        return CONFIG_COMISIONES["porcentaje_resto"]


# ==============================================================================
# 2. EXTRACCIÓN Y PROCESAMIENTO GENERAL (CORREGIDO)
# ==============================================================================
def generar_matriz_pivot(path_db="comisiones.db", output_excel="ERECTUS_Comisiones_2026.xlsx"):
    conn = sqlite3.connect(path_db)
    mes_formateado = f"{CONFIG_COMISIONES['mes_a_calcular']:02d}"

    query = """
        SELECT id_articulo, cantidad, marca, precio_publico, vendedor, fecha, transaccion, ubicacion
        FROM ventas 
        WHERE substr(fecha, 4, 2) = ?
    """

    df_ventas = pd.read_sql_query(query, conn, params=(mes_formateado,))
    conn.close()

    if df_ventas.empty:
        print(f"Advertencia: No se encontraron registros de ventas para el mes {mes_formateado}.")
        return

    # --------------------------------------------------------------------------
    # SOLUCCIÓN AL EROR: Sanitización explícita de textos (Evita comparar None con str)
    # --------------------------------------------------------------------------
    df_ventas['ubicacion'] = df_ventas['ubicacion'].fillna("UBICACION NO ESPECIFICADA").astype(str)
    df_ventas['transaccion'] = df_ventas['transaccion'].fillna("TRANSACCION NO ESPECIFICADA").astype(str)
    df_ventas['vendedor'] = df_ventas['vendedor'].fillna("VENDEDOR NO ESPECIFICADO").astype(str)
    df_ventas['marca'] = df_ventas['marca'].fillna("SIN MARCA").astype(str)

    # Sanitización de datos numéricos
    df_ventas['cantidad'] = pd.to_numeric(df_ventas['cantidad'], errors='coerce').fillna(0)
    df_ventas['precio_publico'] = pd.to_numeric(df_ventas['precio_publico'], errors='coerce').fillna(0.0)

    # Cálculos dinámicos individuales (Renglón por Renglón)
    df_ventas['monto_venta'] = df_ventas['cantidad'] * df_ventas['precio_publico']
    df_ventas['tipo_comision'] = df_ventas.apply(lambda r: obtener_nombre_comision(r['id_articulo'], r['marca']),
                                                 axis=1)
    df_ventas['porcentaje_comision'] = df_ventas.apply(lambda r: calcular_porcentaje_fila(r['id_articulo'], r['marca']),
                                                       axis=1)
    df_ventas['total_comision'] = df_ventas['monto_venta'] * df_ventas['porcentaje_comision']

    # # Agrupación compacta para la Matriz Resumen
    # df_resumen = df_ventas.groupby(['vendedor', 'tipo_comision']).agg(
    #     VENTA=('monto_venta', 'sum'),
    #     COMISION=('total_comision', 'sum')
    # ).reset_index()
    #
    # # Al haber rellenado los nulos con .fillna(), sorted() ya puede ordenar alfabéticamente sin problemas
    # vendedores = sorted(df_ventas['vendedor'].unique())
    # tipos_comision = sorted(df_resumen['tipo_comision'].unique())
    #

    # Agrega ubicacion
    df_resumen = df_ventas.groupby(['vendedor', 'ubicacion', 'tipo_comision']).agg(
        VENTA=('monto_venta', 'sum'),
        COMISION=('total_comision', 'sum')
    ).reset_index()

    # NO se toca: sigue alimentando las hojas de detalle (una por vendedor)
    vendedores = sorted(df_ventas['vendedor'].unique())

    # NUEVO: combinaciones únicas vendedor + tienda, para las filas de la matriz
    pares_vend_ubic = (
        df_ventas[['vendedor', 'ubicacion']]
        .drop_duplicates()
        .sort_values(['vendedor', 'ubicacion'])
        .values.tolist()
    )

    tipos_comision = sorted(df_resumen['tipo_comision'].unique())

    num_cats = len(tipos_comision)

    # Inicializar libro de openpyxl
    wb = openpyxl.Workbook()

    # Estilos Compartidos (Diseño Corporativo)
    HEADER_FILL = PatternFill(start_color="1C3D5A", end_color="1C3D5A", fill_type="solid")
    SUBHEADER_FILL = PatternFill(start_color="2C5282", end_color="2C5282", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    TOTAL_FILL = PatternFill(start_color="EBF8FF", end_color="EBF8FF", fill_type="solid")

    FONT_TITLE = Font(name="Calibri", size=16, bold=True, color="1C3D5A")
    FONT_SUBTITLE = Font(name="Calibri", size=11, bold=True, color="4A5568")
    FONT_HEADER = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    FONT_DATA = Font(name="Calibri", size=11, color="000000")
    FONT_TOTAL = Font(name="Calibri", size=11, bold=True, color="000000")

    THIN_BORDER = Border(left=Side(style='thin', color='CBD5E0'), right=Side(style='thin', color='CBD5E0'),
                         top=Side(style='thin', color='CBD5E0'), bottom=Side(style='thin', color='CBD5E0'))
    TOTAL_BORDER = Border(top=Side(style='thin', color="1C3D5A"), bottom=Side(style='double', color="1C3D5A"))

    # ==============================================================================
    # 3. HOJA PRINCIPAL: MATRIZ PIVOT RESUMEN
    # ==============================================================================
    ws = wb.active
    ws.title = "Matriz Comisiones"
    ws.views.sheetView[0].showGridLines = True

    ws["A1"] = "MATRIZ DE COMISIONES CONSOLIDADA POR VENDEDOR"
    ws["A1"].font = FONT_TITLE
    ws["A2"] = f"PERIODO DE ENTRADA Y PAGO: MES {mes_formateado} / 2026"
    ws["A2"].font = FONT_SUBTITLE

    col_ventas_inicio = 3
    col_comisiones_inicio = col_ventas_inicio + num_cats
    col_total_pagar = col_comisiones_inicio + num_cats

    ws.cell(row=4, column=1, value="VENDEDOR")
    ws.cell(row=4, column=2, value="UBICACION")
    ws.cell(row=4, column=col_ventas_inicio, value="VENTAS BRUTAS ACUMULADAS")
    ws.cell(row=4, column=col_comisiones_inicio, value="COMISIONES NETAS A PAGAR")
    ws.cell(row=4, column=col_total_pagar, value="TOTAL A PAGAR")

    for i, t in enumerate(tipos_comision):
        ws.cell(row=5, column=col_ventas_inicio + i, value=t)
        ws.cell(row=5, column=col_comisiones_inicio + i, value=t)

    for r in [4, 5]:
        for c in range(1, col_total_pagar + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = FONT_HEADER
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if r == 4:
                cell.fill = HEADER_FILL
            else:
                cell.fill = HEADER_FILL if c in [1, 2, col_total_pagar] else SUBHEADER_FILL

    ws.merge_cells(start_row=4, start_column=1, end_row=5, end_column=1)
    ws.merge_cells(start_row=4, start_column=2, end_row=5, end_column=2)
    ws.merge_cells(start_row=4, start_column=col_ventas_inicio, end_row=4, end_column=col_comisiones_inicio - 1)
    ws.merge_cells(start_row=4, start_column=col_comisiones_inicio, end_row=4, end_column=col_total_pagar - 1)
    ws.merge_cells(start_row=4, start_column=col_total_pagar, end_row=5, end_column=col_total_pagar)

    current_row = 6
    for idx, (v, u) in enumerate(pares_vend_ubic):
        ws.cell(row=current_row, column=1, value=v).alignment = Alignment(horizontal="left", vertical="center")
        ws.cell(row=current_row, column=2, value=u).alignment = Alignment(horizontal="left", vertical="center")

        # Filtro base: ahora considera vendedor Y ubicación
        mask_base = (df_resumen['vendedor'] == v) & (df_resumen['ubicacion'] == u)

        for i, t in enumerate(tipos_comision):
            subset = df_resumen[mask_base & (df_resumen['tipo_comision'] == t)]
            val_venta = subset['VENTA'].values[0] if not subset.empty else 0.0
            ws.cell(row=current_row, column=col_ventas_inicio + i, value=val_venta)

        for i, t in enumerate(tipos_comision):
            subset = df_resumen[mask_base & (df_resumen['tipo_comision'] == t)]
            val_com = subset['COMISION'].values[0] if not subset.empty else 0.0
            ws.cell(row=current_row, column=col_comisiones_inicio + i, value=val_com)

        letra_ini = get_column_letter(col_comisiones_inicio)
        letra_fin = get_column_letter(col_total_pagar - 1)
        ws.cell(row=current_row, column=col_total_pagar,
                value=f"=SUM({letra_ini}{current_row}:{letra_fin}{current_row})")

        for c in range(1, col_total_pagar + 1):
            cell = ws.cell(row=current_row, column=c)
            cell.font = FONT_DATA
            cell.border = THIN_BORDER
            if idx % 2 == 1:
                cell.fill = ZEBRA_FILL
            if c >= col_ventas_inicio:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal="right", vertical="center")
        current_row += 1

    ws.cell(row=current_row, column=1, value="TOTALES").font = FONT_TOTAL
    ws.cell(row=current_row, column=1).alignment = Alignment(horizontal="left", vertical="center")

    for c in range(col_ventas_inicio, col_total_pagar + 1):
        col_let = get_column_letter(c)
        ws.cell(row=current_row, column=c, value=f"=SUM({col_let}6:{col_let}{current_row - 1})")

    for c in range(1, col_total_pagar + 1):
        cell = ws.cell(row=current_row, column=c)
        cell.font = FONT_TOTAL
        cell.fill = TOTAL_FILL
        cell.border = TOTAL_BORDER
        if c >= col_ventas_inicio:
            cell.number_format = '$#,##0.00'
            cell.alignment = Alignment(horizontal="right", vertical="center")

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 24
    ws.column_dimensions['A'].width = 28   # VENDEDOR
    ws.column_dimensions['B'].width = 30   # UBICACION
    ws.freeze_panes = "A6"

    # ==============================================================================
    # 4. HOJAS DETALLADAS POR VENDEDOR (RASTRERABILIDAD CORREGIDA)
    # ==============================================================================
    for v in vendedores:
        df_vendedor = df_ventas[df_ventas['vendedor'] == v].copy()

        # Eliminar caracteres inválidos de Excel para nombres de pestañas y limitar a 30 chars
        nombre_pestaña = str(v).replace(r'[\\*?:/\[\]]', '')[:30].strip()
        if not nombre_pestaña:
            nombre_pestaña = "S_N"

        ws_v = wb.create_sheet(title=nombre_pestaña)
        ws_v.views.sheetView[0].showGridLines = True

        ws_v["A1"] = f"DETALLE DE AUDITORÍA DE COMISIONES - {v.upper()}"
        ws_v["A1"].font = FONT_TITLE
        ws_v["A2"] = f"RASTRERABILIDAD DE REGISTROS - PERIODO MES {mes_formateado} / 2026"
        ws_v["A2"].font = FONT_SUBTITLE

        headers_detalle = [
            "UBICACION", "TRANSACCION", "FECHA", "ID ARTÍCULO", "CANTIDAD", "MARCA",
            "PRECIO PÚBLICO", "MONTO VENTA", "TIPO COMISIÓN",
            "PORCENTAJE", "TOTAL COMISIÓN"
        ]

        for col_idx, text in enumerate(headers_detalle, start=1):
            cell = ws_v.cell(row=4, column=col_idx, value=text)
            cell.font = FONT_HEADER
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = THIN_BORDER

        v_row = 5
        for r_idx, row_data in df_vendedor.iterrows():
            ws_v.cell(row=v_row, column=1, value=row_data['ubicacion']).alignment = Alignment(horizontal="left")
            ws_v.cell(row=v_row, column=2, value=row_data['transaccion']).alignment = Alignment(horizontal="center")
            ws_v.cell(row=v_row, column=3, value=row_data['fecha']).alignment = Alignment(horizontal="center")
            ws_v.cell(row=v_row, column=4, value=row_data['id_articulo']).alignment = Alignment(horizontal="center")
            ws_v.cell(row=v_row, column=5, value=row_data['cantidad'])
            ws_v.cell(row=v_row, column=6, value=row_data['marca']).alignment = Alignment(horizontal="left")
            ws_v.cell(row=v_row, column=7, value=row_data['precio_publico'])

            ws_v.cell(row=v_row, column=8, value=f"=E{v_row}*G{v_row}")
            ws_v.cell(row=v_row, column=9, value=row_data['tipo_comision']).alignment = Alignment(horizontal="left")
            ws_v.cell(row=v_row, column=10, value=row_data['porcentaje_comision'])
            ws_v.cell(row=v_row, column=11, value=f"=H{v_row}*J{v_row}")

            for c_idx in range(1, 12):
                cell = ws_v.cell(row=v_row, column=c_idx)
                cell.font = FONT_DATA
                cell.border = THIN_BORDER
                if (v_row - 5) % 2 == 1:
                    cell.fill = ZEBRA_FILL

                if c_idx in [5]:
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [7, 8, 11]:
                    cell.number_format = '$#,##0.00'
                    cell.alignment = Alignment(horizontal="right")
                elif c_idx in [10]:
                    cell.number_format = '0.0%'
                    cell.alignment = Alignment(horizontal="right")

            v_row += 1

        ws_v.cell(row=v_row, column=1, value="TOTALES ACUMULADOS").font = FONT_TOTAL
        ws_v.cell(row=v_row, column=1).alignment = Alignment(horizontal="left", vertical="center")

        for c_idx in [5, 8, 11]:
            col_let = get_column_letter(c_idx)
            ws_v.cell(row=v_row, column=c_idx, value=f"=SUM({col_let}5:{col_let}{v_row - 1})")

        for c_idx in range(1, 12):
            cell = ws_v.cell(row=v_row, column=c_idx)
            cell.font = FONT_TOTAL
            cell.fill = TOTAL_FILL
            cell.border = TOTAL_BORDER
            if c_idx in [5]:
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal="right")
            elif c_idx in [6, 8, 11]:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal="right")

        for col in ws_v.columns:
            col_letter = get_column_letter(col[0].column)
            ws_v.column_dimensions[col_letter].width = 22
        ws_v.freeze_panes = "A5"

    wb.save(output_excel)
    print(f"Reporte unificado y protegido contra nulos generado exitosamente: '{output_excel}'")


if __name__ == "__main__":
    generar_matriz_pivot()