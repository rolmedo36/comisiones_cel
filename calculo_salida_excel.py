import pandas as pd
import sqlite3
from datetime import datetime, timedelta

def get_weeks_for_month(year, month):
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    weeks = []
    current_date = start_date

    while current_date <= end_date:
        days_in_week = []
        temp_date = current_date

        while temp_date.weekday() < 6 and temp_date <= end_date:
            days_in_week.append(temp_date.date())
            temp_date += timedelta(days=1)

        if temp_date.weekday() == 6 and temp_date <= end_date:
            days_in_week.append(temp_date.date())
            temp_date += timedelta(days=1)

        if len(days_in_week) < 4:
            while temp_date.weekday() != 6 and temp_date <= end_date:
                days_in_week.append(temp_date.date())
                temp_date += timedelta(days=1)
            if temp_date <= end_date:
                days_in_week.append(temp_date.date())
                temp_date += timedelta(days=1)

        weeks.append(days_in_week)
        current_date = temp_date

    return weeks

def cargar_ventas_desde_db(db_path: str, year: int, month: int) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
    SELECT 
        articulo,
        id_articulo,
        cantidad,
        fecha,
        marca,
        familia_comercial,
        precio_publico,
        tipo_venta,
        transaccion,
        ubicacion,
        vendedor
    FROM ventas;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce')
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce')
    df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')
    df = df.dropna(subset=['fecha', 'cantidad', 'precio_publico', 'vendedor'])
    df = df[
        (df['fecha'].dt.year == year) &
        (df['fecha'].dt.month == month)
    ].copy()
    return df

def cargar_presupuestos_por_vendedor(db_path: str, year: int, month: int) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS presupuestos_ubicaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ubicacion_tienda TEXT NOT NULL,
    mes INTEGER NOT NULL,
    anio INTEGER NOT NULL,
    presupuesto REAL NOT NULL,
    UNIQUE(ubicacion_tienda, mes, anio)
    );
    """)

    conn = sqlite3.connect(db_path)
    query = """
    SELECT vendedor, presupuesto
    FROM presupuesto_vendedor
    WHERE mes = ? AND año = ?;
    """
    df = pd.read_sql_query(query, conn, params=(month, year))
    conn.close()
    return df

def crear_tabla_comisiones_por_vendedor_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comisiones_por_vendedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto_asignado REAL NOT NULL,
        venta_total_vendedor REAL NOT NULL,
        porcentaje_cumplimiento REAL NOT NULL,
        comision_mensual REAL NOT NULL,
        comision_juguetes REAL NOT NULL,
        comision_cxo REAL NOT NULL,
        comision_dusa REAL NOT NULL,
        comision_shumatsu REAL NOT NULL,
        comision_semanal REAL NOT NULL,
        total_comisiones REAL NOT NULL,
        fecha_calculo TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

def calcular_comisiones_por_vendedor(
    db_path: str,
    year: int,
    month: int
):
    ventas = cargar_ventas_desde_db(db_path, year, month)
    presupuestos = cargar_presupuestos_por_vendedor(db_path, year, month)

    if ventas.empty:
        print("⚠️ No hay ventas válidas para este mes.")
        return []

    # Unir ventas con presupuestos
    presupuestos_dict = dict(zip(presupuestos['vendedor'], presupuestos['presupuesto']))
    resultados = []

    for vendedor, grupo in ventas.groupby('vendedor'):
        grupo['venta_total'] = grupo['cantidad'] * grupo['precio_publico']
        venta_total_vendedor = grupo['venta_total'].sum()

        # === Obtener presupuesto del vendedor ===
        presupuesto_vendedor = presupuestos_dict.get(vendedor, 0)

        # === ESQUEMA 1: Comisión por cumplimiento del presupuesto del vendedor ===
        porcentaje_cumplimiento = (venta_total_vendedor / presupuesto_vendedor) * 100 if presupuesto_vendedor > 0 else 0
        if 75 <= porcentaje_cumplimiento < 80:
            comision_mensual = venta_total_vendedor * 0.01
        elif 80 <= porcentaje_cumplimiento < 90:
            comision_mensual = venta_total_vendedor * 0.0125
        elif 90 <= porcentaje_cumplimiento < 110:
            comision_mensual = venta_total_vendedor * 0.02
        elif porcentaje_cumplimiento >= 110:
            comision_mensual = venta_total_vendedor * 0.025
        else:
            comision_mensual = 0

        # === ESQUEMA 2: Comisiones adicionales por vendedor ===
        juguetes = grupo[
            (grupo['familia_comercial'] == 'JUGUETE') &
            (~grupo['marca'].astype(str).str.startswith('CXO', na=False)) &
            (grupo['precio_publico'] * grupo['cantidad'] > 1500)
        ]
        comision_juguetes = juguetes['venta_total'].sum() * 0.01

        cxo = grupo[grupo['marca'].astype(str).str.startswith('CXO', na=False)]
        comision_cxo = cxo['venta_total'].sum() * 0.06

        dusa = grupo[
            (grupo['marca'] == 'DUSA') &
            (grupo['id_articulo'] != '5356')
        ]
        comision_dusa = dusa['venta_total'].sum() * 0.02

        shumatsu = grupo[grupo['id_articulo'] == '5356']
        comision_shumatsu = shumatsu['venta_total'].sum() * 0.06

        # === COMISIÓN SEMANAL: 1% sobre cada semana (por vendedor) ===
        semanas = get_weeks_for_month(year, month)
        comision_semanal = 0.0
        for semana in semanas:
            fi, ff = semana[0], semana[-1]
            ventas_semana = grupo[
                (grupo['fecha'].dt.date >= fi) &
                (grupo['fecha'].dt.date <= ff)
            ]
            total_semana = ventas_semana['venta_total'].sum()
            comision_semanal += total_semana * 0.01

        total_comisiones = (
            comision_mensual + comision_juguetes + comision_cxo +
            comision_dusa + comision_shumatsu + comision_semanal
        )

        resultados.append({
            'vendedor': vendedor,
            'presupuesto_asignado': presupuesto_vendedor,
            'venta_total_vendedor': venta_total_vendedor,
            'porcentaje_cumplimiento': porcentaje_cumplimiento,
            'comision_mensual': comision_mensual,
            'comision_juguetes': comision_juguetes,
            'comision_cxo': comision_cxo,
            'comision_dusa': comision_dusa,
            'comision_shumatsu': comision_shumatsu,
            'comision_semanal': comision_semanal,
            'total_comisiones': total_comisiones
        })

    # === GUARDAR RESULTADOS EN LA BASE DE DATOS ===
    crear_tabla_comisiones_por_vendedor_si_no_existe(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Eliminar registros anteriores para este mes/año
    cursor.execute("""
        DELETE FROM comisiones_por_vendedor 
        WHERE mes = ? AND anio = ?
    """, (month, year))

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for res in resultados:
        cursor.execute("""
        INSERT INTO comisiones_por_vendedor (
            vendedor, mes, anio, presupuesto_ubicacion,
            venta_total_vendedor, porcentaje_cumplimiento_ubicacion,
            comision_mensual, comision_juguetes, comision_cxo,
            comision_dusa, comision_shumatsu, comision_semanal, total_comisiones,
            fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res['vendedor'],
            month,
            year,
            res['presupuesto_asignado'],
            res['venta_total_vendedor'],
            res['porcentaje_cumplimiento'],
            res['comision_mensual'],
            res['comision_juguetes'],
            res['comision_cxo'],
            res['comision_dusa'],
            res['comision_shumatsu'],
            res['comision_semanal'],
            res['total_comisiones'],

        ))

    conn.commit()
    conn.close()

    return resultados

def exportar_a_excel(resultados: list, archivo_salida: str):
    df = pd.DataFrame(resultados)
    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Comisiones por Vendedor', index=False)
        # Opcional: Agregar una hoja de resumen
        resumen = df[['vendedor', 'venta_total_vendedor', 'total_comisiones']].copy()
        resumen['% Comisión'] = (resumen['total_comisiones'] / resumen['venta_total_vendedor'] * 100).round(2)
        resumen.to_excel(writer, sheet_name='Resumen', index=False)
    print(f"📄 Reporte guardado en: {archivo_salida}")

# === EJECUCIÓN ===
if __name__ == "__main__":
    DB_PATH = "comisiones.db"
    YEAR = 2026
    MONTH = 1

    print(f"🔍 Calculando comisiones por vendedor para {MONTH}/{YEAR}...")
    resultados = calcular_comisiones_por_vendedor(DB_PATH, YEAR, MONTH)

    print("\n✅ RESULTADOS POR VENDEDOR")
    print("=" * 100)
    for res in resultados:
        print(f"Vendedor: {res['vendedor']}")
        print(f"  - Presupuesto Asignado: ${res['presupuesto_asignado']:,.2f}")
        print(f"  - Venta Total: ${res['venta_total_vendedor']:,.2f}")
        print(f"  - % Cumplimiento: {res['porcentaje_cumplimiento']:.2f}%")
        print(f"  - Comisión Mensual: ${res['comision_mensual']:,.2f}")
        print(f"  - Comisión Juguetes: ${res['comision_juguetes']:,.2f}")
        print(f"  - Comisión CXO: ${res['comision_cxo']:,.2f}")
        print(f"  - Comisión DUSA: ${res['comision_dusa']:,.2f}")
        print(f"  - Comisión Shumatsu: ${res['comision_shumatsu']:,.2f}")
        print(f"  - Comisión Semanal: ${res['comision_semanal']:,.2f}")
        print(f"  - TOTAL COMISIÓN: ${res['total_comisiones']:,.2f}")
        print("-" * 50)

    print(f"\n💾 Resultados guardados en la tabla 'comisiones_por_vendedor' de '{DB_PATH}'.")

    # === EXPORTAR A EXCEL ===
    archivo_excel = f"comisiones_{MONTH}_{YEAR}.xlsx"
    exportar_a_excel(resultados, archivo_excel)