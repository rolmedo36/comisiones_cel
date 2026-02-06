import sqlite3
import pandas as pd
import unicodedata


def limpiar_texto(texto):
    """Función para quitar acentos y pasar a mayúsculas"""
    if not texto: return ""
    texto = str(texto).upper()
    # Elimina acentos (ej: Ó -> O)
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                   if unicodedata.category(c) != 'Mn')


def generar_reporte_comisiones_final():
    print("=== Sistema de Comisiones Kainu (Versión Final Robusta) ===")

    try:
        anio_req = int(input("Año (YYYY): "))
        mes_req = int(input("Mes (1-12): "))
    except ValueError:
        print("Error: Ingrese números válidos.")
        return

    try:
        conn = sqlite3.connect('comisiones_kainu.db')
        df = pd.read_sql_query("SELECT * FROM ventas_kainu", conn)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        return

    if df.empty:
        print("La base de datos está vacía.")
        return

    # 1. Limpieza de datos y normalización
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)
    df['id_articulo'] = pd.to_numeric(df['id_articulo'], errors='coerce').fillna(0).astype(int)
    df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')

    # Filtrado por periodo
    df_p = df[(df['fecha_dt'].dt.year == anio_req) & (df['fecha_dt'].dt.month == mes_req)].copy()
    if df_p.empty:
        print(f"Sin datos para {mes_req}/{anio_req}")
        return

    df_p['Importe Total'] = df_p['cantidad'] * df_p['precio_publico']

    # --- LÓGICA DE REGLAS ROBUSTA ---
    def calcular_comision_final(row):
        id_art = row['id_articulo']
        nombre_limpio = limpiar_texto(row['articulo'])
        tipo_limpio = limpiar_texto(row['tipo'])

        # 1. EXCLUSIÓN LOGÍSTICA (0%)
        if "RECOLECCION" in nombre_limpio or "UBER" in nombre_limpio:
            return 'Logística (No comisionable)', 0.00

        # 2. PRODUCTOS KAINU (10%)
        elif id_art in [24727, 24302, 24725, 24300]:
            return 'Productos Kainu', 0.10

        # 3. CONSULTA VETERINARIA (50%)
        elif id_art == 23892:
            return 'Consulta Veterinaria', 0.50

        # 4. REGLA PARA SERVICES (3%)
        elif tipo_limpio == "SERVICES":
            return 'Servicios (Generales)', 0.03

        # 5. el resto
        else:
            return 'Productos/Otros', 0.03

    # Aplicar lógica
    resultados = df_p.apply(calcular_comision_final, axis=1)
    df_p['Tipo de Comisión'] = [r[0] for r in resultados]
    df_p['%'] = [r[1] for r in resultados]
    df_p['Importe Comisión'] = df_p['Importe Total'] * df_p['%']

    # --- EXPORTACIÓN ---
    nombre_archivo = f'Reporte_Comisiones_{mes_req}_{anio_req}.xlsx'

    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
        # Hoja 1: Resumen de pago
        pago = df_p.groupby('vendedor')['Importe Comisión'].sum().reset_index()
        pago.columns = ['Vendedor', 'TOTAL A PAGAR']
        pago.to_excel(writer, sheet_name='PAGO_TOTAL', index=False)

        # Hoja 2: Desglose por vendedor y tipo
        desglose = df_p[df_p['%'] > 0].groupby(['vendedor', 'Tipo de Comisión']).agg({
            'cantidad': 'sum', 'Importe Total': 'sum', 'Importe Comisión': 'sum'
        }).reset_index()
        desglose.to_excel(writer, sheet_name='DESGLOSE', index=False)

        # Hoja 3: Validación detallada
        cols_val = ['fecha', 'vendedor', 'articulo', 'tipo', 'cantidad', 'precio_publico',
                    'Importe Total', 'Tipo de Comisión', '%', 'Importe Comisión']
        if 'transaccion' in df_p.columns: cols_val.insert(0, 'transaccion')
        df_p[cols_val].to_excel(writer, sheet_name='VALIDACION', index=False)

        # Formatos de Excel
        workbook = writer.book
        moneda = workbook.add_format({'num_format': '$#,##0.00'})
        pct = workbook.add_format({'num_format': '0%'})

        for sheet in writer.sheets.values():
            sheet.set_column('A:Z', 18)
        writer.sheets['PAGO_TOTAL'].set_column('B:B', 20, moneda)
        writer.sheets['VALIDACION'].set_column('I:I', 10, pct)
        writer.sheets['VALIDACION'].set_column('G:G', 15, moneda)
        writer.sheets['VALIDACION'].set_column('K:K', 15, moneda)

    print(f"\n¡Reporte Generado con éxito! Archivo: {nombre_archivo}")


if __name__ == "__main__":
    generar_reporte_comisiones_final()