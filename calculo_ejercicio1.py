import pandas as pd
import sqlite3

# 1. Conexión y carga de datos
try:
    conn = sqlite3.connect('comisiones.db')
    df = pd.read_sql_query("SELECT * FROM ventas", conn)
    conn.close()
except sqlite3.Error as e:
    print(f"Error al abrir la DB: {e}")
    exit()

# 2. Limpieza y Normalización de tipos de datos
df['cantidad_num'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
df['precio_publico_num'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)
df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')

# --- UNIFICACIÓN DE MARCAS ---
df['marca_unificada'] = df['marca'].astype(str).str.strip().str.upper()
df['marca_unificada'] = df['marca_unificada'].replace(['CXO:B', 'CXO: B'], 'CXO')

# 3. Filtrar Periodo: Diciembre 2025
df_dic = df[(df['fecha'].dt.year == 2025) & (df['fecha'].dt.month == 12)].copy()


# 4. Lógica de Clasificación de Comisiones (Etiqueta SHUMATSU al 10%)
def clasificar_comision(row):
    marca = row['marca_unificada']
    id_art = str(row['id_articulo'])

    # IDs específicos para SHUMATSU
    ids_shumatsu = ['5356', '1165', '1164']

    # NUEVA ETIQUETA: SHUMATSU al 10%
    if id_art in ids_shumatsu:
        return 'SHUMATSU', 0.10

    # Regla CXO (Unificada) al 7%
    if marca == 'CXO':
        return 'CXO', 0.07

    # Regla DUSA al 3%
    if marca == 'DUSA':
        return 'DUSA', 0.03

    return 'OTROS', 0.0


# Aplicar clasificación y cálculos monetarios
res = df_dic.apply(lambda r: pd.Series(clasificar_comision(r)), axis=1)
df_dic['tipo_comision'] = res[0]
df_dic['porcentaje_aplicado'] = res[1]
df_dic['importe_total'] = df_dic['cantidad_num'] * df_dic['precio_publico_num']

# 5. AGRUPACIÓN 1: Consolidado por Vendedor, Ubicación y Tipo
df_agrupado = df_dic.groupby(['vendedor', 'ubicacion', 'tipo_comision', 'porcentaje_aplicado']).agg({
    'cantidad_num': 'sum',
    'importe_total': 'sum'
}).reset_index()

df_agrupado = df_agrupado.rename(columns={'cantidad_num': 'cantidad', 'importe_total': 'importe'})
df_agrupado['comision_generada'] = df_agrupado['importe'] * df_agrupado['porcentaje_aplicado']

# 6. AGRUPACIÓN 2: Resumen por Vendedor y Ubicación
df_resumen_final = df_agrupado.groupby(['vendedor', 'ubicacion']).agg({
    'cantidad': 'sum',
    'importe': 'sum',
    'comision_generada': 'sum'
}).reset_index()

# 7. Generación del archivo Excel con formato
nombre_archivo = 'Reporte_Comisiones_Shumatsu_10_Dic_2025.xlsx'

with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
    # Hoja 1: Detalle por tipo
    df_agrupado[['vendedor', 'ubicacion', 'tipo_comision', 'cantidad', 'importe', 'porcentaje_aplicado',
                 'comision_generada']].to_excel(writer, sheet_name='Consolidado_por_Tipo', index=False)

    # Hoja 2: Resumen total
    df_resumen_final.to_excel(writer, sheet_name='Resumen_Vendedor_Ubicacion', index=False)

    # Formatos de celdas
    workbook = writer.book
    fmt_moneda = workbook.add_format({'num_format': '$#,##0.00'})
    fmt_porc = workbook.add_format({'num_format': '0%'})

    # Aplicar formatos a las hojas
    for sheet_name in ['Consolidado_por_Tipo', 'Resumen_Vendedor_Ubicacion']:
        ws = writer.sheets[sheet_name]
        ws.set_column('A:B', 20)
        if sheet_name == 'Consolidado_por_Tipo':
            ws.set_column('E:E', 15, fmt_moneda)
            ws.set_column('F:F', 18, fmt_porc)
            ws.set_column('G:G', 15, fmt_moneda)
        else:
            ws.set_column('D:E', 15, fmt_moneda)

print(f"Reporte final generado exitosamente: {nombre_archivo}")