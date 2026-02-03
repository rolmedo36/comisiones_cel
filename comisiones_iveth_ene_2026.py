import pandas as pd
import sqlite3

# --- CONFIGURACIÓN ---
DB_NAME = 'comisiones.db'
ANIO_PROCESO = 2026  # Actualizado según tu log
MES_PROCESO = 1
ARCHIVO_SALIDA = f'Reporte_Comisiones_{ANIO_PROCESO}_{MES_PROCESO}.xlsx'


def inicializar_base_de_datos(db_path):
    """Crea la tabla de presupuestos si no existe."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS presupuesto_vendedor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor TEXT NOT NULL,
                año INTEGER NOT NULL,
                mes INTEGER NOT NULL,
                presupuesto REAL DEFAULT 0,
                UNIQUE(vendedor, año, mes)
            )
        """)
        conn.commit()
        conn.close()
        print("--- Tabla 'presupuesto_vendedor' verificada/creada ---")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos: {e}")


def obtener_datos(db_path, anio, mes):
    """Carga ventas y presupuestos."""
    try:
        conn = sqlite3.connect(db_path)
        df_ventas = pd.read_sql_query("SELECT * FROM ventas", conn)
        query_metas = "SELECT vendedor, presupuesto FROM presupuesto_vendedor WHERE año = ? AND mes = ?"
        df_metas = pd.read_sql_query(query_metas, conn, params=(anio, mes))
        conn.close()
        return df_ventas, df_metas
    except sqlite3.Error as e:
        print(f"Error en la base de datos al leer: {e}")
        return None, None


def limpiar_y_filtrar(df, anio, mes):
    """Limpia tipos de datos y filtra por periodo."""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)
    df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')

    df['marca_unificada'] = df['marca'].astype(str).str.strip().str.upper().replace(['CXO:B', 'CXO: B'], 'CXO')
    df['familia_comercial'] = df['familia_comercial'].astype(str).str.strip().str.upper()

    mask = (df['fecha'].dt.year == anio) & (df['fecha'].dt.month == mes)
    df_filtrado = df[mask].copy()

    df_filtrado['importe_total'] = df_filtrado['cantidad'] * df_filtrado['precio_publico']
    return df_filtrado


def asignar_tipo_comision(row):
    """Lógica de clasificación. Devuelve un diccionario para asegurar compatibilidad."""
    marca = row['marca_unificada']
    id_art = str(row['id_articulo'])
    familia = row['familia_comercial']

    # SHUMATSU (10%)
    if id_art in ['5356', '1165', '1164']:
        return {'tipo_comision': 'SHUMATSU', 'porcentaje_aplicado': 0.10}

    # CXO (7%)
    if marca == 'CXO':
        return {'tipo_comision': 'CXO', 'porcentaje_aplicado': 0.07}

    # JUGUETE (2%)
    if familia == 'JUGUETE':
        return {'tipo_comision': 'JUGUETE', 'porcentaje_aplicado': 0.02}

    # DUSA (3%)
    if marca == 'DUSA':
        return {'tipo_comision': 'DUSA', 'porcentaje_aplicado': 0.03}

    return {'tipo_comision': 'OTROS', 'porcentaje_aplicado': 0.0}


def calcular_bono_presupuesto(df_ventas, df_metas):
    """Calcula el bono del 1% sobre el total de venta si se cumple > 80%."""
    if df_ventas.empty:
        return pd.DataFrame(columns=['vendedor', 'presupuesto', 'cumplimiento_pct', 'bono_presupuesto'])

    resumen = df_ventas.groupby('vendedor')['importe_total'].sum().reset_index()
    resumen = resumen.merge(df_metas, on='vendedor', how='left').fillna(0)

    def regla_bono(row):
        if row['presupuesto'] > 0 and (row['importe_total'] / row['presupuesto']) > 0.80:
            return row['importe_total'] * 0.01
        return 0.0

    resumen['cumplimiento_pct'] = (resumen['importe_total'] / resumen['presupuesto']).replace(
        [float('inf'), -float('inf')], 0).fillna(0)
    resumen['bono_presupuesto'] = resumen.apply(regla_bono, axis=1)

    return resumen[['vendedor', 'presupuesto', 'cumplimiento_pct', 'bono_presupuesto']]


def generar_excel(df_agrupado, df_resumen, nombre_archivo):
    """Exporta resultados a Excel."""
    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
        df_agrupado.to_excel(writer, sheet_name='Detalle_por_Tipo', index=False)
        df_resumen.to_excel(writer, sheet_name='Resumen_Final_Pago', index=False)

        workbook = writer.book
        fmt_money = workbook.add_format({'num_format': '$#,##0.00'})
        fmt_pct = workbook.add_format({'num_format': '0%'})

        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            ws.set_column('A:Z', 20)
            if sheet_name == 'Detalle_por_Tipo':
                ws.set_column('E:E', 18, fmt_money)
                ws.set_column('F:F', 12, fmt_pct)
                ws.set_column('G:G', 18, fmt_money)
            else:
                ws.set_column('D:D', 18, fmt_money)
                ws.set_column('F:F', 18, fmt_money)
                ws.set_column('G:G', 12, fmt_pct)
                ws.set_column('H:I', 18, fmt_money)


def main():
    print(f"--- Iniciando proceso de comisiones {MES_PROCESO}/{ANIO_PROCESO} ---")
    inicializar_base_de_datos(DB_NAME)

    df_ventas, df_metas = obtener_datos(DB_NAME, ANIO_PROCESO, MES_PROCESO)

    # 1. Validación de datos iniciales
    if df_ventas is None or df_ventas.empty:
        print("Error: No se encontraron datos en la tabla 'ventas'.")
        return

    # 2. Limpieza y filtrado
    df_clean = limpiar_y_filtrar(df_ventas, ANIO_PROCESO, MES_PROCESO)

    if df_clean.empty:
        print(f"Aviso: No hay ventas registradas para el periodo {MES_PROCESO}/{ANIO_PROCESO}.")
        return

    # 3. Clasificación (Solución al ValueError)
    # Aplicamos la función y convertimos el resultado (lista de dicts) directamente en DataFrame
    comisiones_df = pd.DataFrame(df_clean.apply(asignar_tipo_comision, axis=1).tolist(), index=df_clean.index)
    df_clean = pd.concat([df_clean, comisiones_df], axis=1)

    df_clean['comision_producto'] = df_clean['importe_total'] * df_clean['porcentaje_aplicado']

    # 4. Cálculo de Bonos
    df_bonos = calcular_bono_presupuesto(df_clean, df_metas)

    # 5. Agrupaciones
    df_final_tipo = df_clean.groupby(['vendedor', 'ubicacion', 'tipo_comision', 'porcentaje_aplicado']).agg({
        'cantidad': 'sum',
        'importe_total': 'sum',
        'comision_producto': 'sum'
    }).reset_index()

    df_final_resumen = df_final_tipo.groupby(['vendedor', 'ubicacion']).agg({
        'cantidad': 'sum',
        'importe_total': 'sum',
        'comision_producto': 'sum'
    }).reset_index()

    df_final_resumen = df_final_resumen.merge(df_bonos, on='vendedor', how='left')
    df_final_resumen['TOTAL_A_PAGAR'] = df_final_resumen['comision_producto'].fillna(0) + df_final_resumen[
        'bono_presupuesto'].fillna(0)

    # 6. Exportación
    generar_excel(df_final_tipo, df_final_resumen, ARCHIVO_SALIDA)
    print(f"--- Proceso finalizado exitosamente. Archivo: {ARCHIVO_SALIDA} ---")


if __name__ == "__main__":
    main()