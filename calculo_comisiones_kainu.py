import sqlite3
import pandas as pd


def generar_reporte_comisiones():
    try:
        conn = sqlite3.connect('comisiones_kainu.db')
        df = pd.read_sql_query("SELECT * FROM ventas_kainu", conn)
        conn.close()
    except Exception as e:
        print(f"Error al conectar o leer la base de datos: {e}")
        return

    if df.empty:
        print("La base de datos está vacía.")
        return

    # --- SOLUCIÓN AL TYPEERROR: Conversión a números ---
    # errors='coerce' convertirá cualquier valor no válido en NaN (nulo)
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)

    # Conversión de fechas
    df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')

    # Filtrar por Año 2025 y Mes 12
    df = df[(df['fecha'].dt.year == 2025) & (df['fecha'].dt.month == 12)]

    if df.empty:
        print("No se encontraron registros para Diciembre 2025.")
        return

    # Ahora el cálculo de importe_total no fallará
    df['importe_total'] = df['cantidad'] * df['precio_publico']

    # Lógica de Clasificación
    def clasificar_y_comisionar(row):
        # Aseguramos que el id_articulo sea entero para la comparación
        try:
            id_art = int(float(row['id_articulo']))
        except:
            id_art = 0

        mapeo = {
            23892: ('Consulta Veterinaria', 0.50),
            24727: ('Kainu Pollo 100g', 0.10),
            24302: ('Kainu Pollo 250g', 0.10),
            24725: ('Kainu Res 100g', 0.10),
            24300: ('Kainu Res 250g', 0.10)
        }

        categoria, porcentaje = mapeo.get(id_art, ('Productos (resto)', 0.03))
        return pd.Series([categoria, row['importe_total'] * porcentaje])

    df[['Tipo de Comisión', 'Importe Comisión']] = df.apply(clasificar_y_comisionar, axis=1)

    # Agrupación final
    resumen = df.groupby(['vendedor', 'Tipo de Comisión']).agg({
        'cantidad': 'sum',
        'importe_total': 'sum',
        'Importe Comisión': 'sum'
    }).reset_index()

    resumen.columns = ['Vendedor', 'Tipo de Comisión', 'Cantidad', 'Importe Total', 'Importe Comisión']

    # Exportación a Excel
    nombre_archivo = 'Comisiones_Kainu_Dic_2025.xlsx'
    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
        resumen.to_excel(writer, sheet_name='Desglose', index=False)

        workbook = writer.book
        worksheet = writer.sheets['Desglose']
        fmt_moneda = workbook.add_format({'num_format': '$#,##0.00'})

        worksheet.set_column('A:B', 30)
        worksheet.set_column('C:C', 12)
        worksheet.set_column('D:E', 20, fmt_moneda)

    print(f"Éxito: Reporte generado en '{nombre_archivo}'")


if __name__ == "__main__":
    generar_reporte_comisiones()