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

def crear_tabla_presupuestos_ubicaciones_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS presupuestos_ubicaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ubicacion TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto REAL NOT NULL,
        UNIQUE(ubicacion, mes, anio)
    );
    """)
    conn.commit()
    conn.close()

def crear_tabla_comisiones_por_vendedor_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comisiones_por_vendedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor TEXT NOT NULL,
        ubicacion TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto_ubicacion REAL NOT NULL,
        venta_total_ubicacion REAL NOT NULL,
        porcentaje_cumplimiento_ubicacion REAL NOT NULL,
        venta_total_vendedor REAL NOT NULL,
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

def crear_tabla_comisiones_semanales_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comisiones_semanales_por_vendedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor TEXT NOT NULL,
        ubicacion TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        semana_numero INTEGER NOT NULL,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        dias_incluidos TEXT NOT NULL,
        dias_semana INTEGER NOT NULL,
        presupuesto_diario REAL NOT NULL,
        presupuesto_semana REAL NOT NULL,
        venta_semana REAL NOT NULL,
        comision_semana REAL NOT NULL,
        cumplio_semana BOOLEAN NOT NULL,
        fecha_calculo TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()

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
    df = df.dropna(subset=['fecha', 'cantidad', 'precio_publico', 'vendedor', 'ubicacion'])
    df = df[
        (df['fecha'].dt.year == year) &
        (df['fecha'].dt.month == month)
    ].copy()
    return df

def cargar_presupuestos_por_ubicacion(db_path: str, year: int, month: int) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
    SELECT ubicacion, presupuesto
    FROM presupuestos_ubicaciones
    WHERE mes = ? AND anio = ?;
    """
    df = pd.read_sql_query(query, conn, params=(month, year))
    conn.close()

    df['presupuesto'] = pd.to_numeric(df['presupuesto'], errors='coerce')
    df = df.dropna(subset=['presupuesto'])
    return df
def calcular_comisiones_por_vendedor(db_path: str, year: int, month: int):
    # Crear tablas
    crear_tabla_presupuestos_ubicaciones_si_no_existe(db_path)
    crear_tabla_comisiones_por_vendedor_si_no_existe(db_path)
    crear_tabla_comisiones_semanales_si_no_existe(db_path)

    ventas = cargar_ventas_desde_db(db_path, year, month)
    presupuestos = cargar_presupuestos_por_ubicacion(db_path, year, month)

    if ventas.empty:
        print("⚠️ No hay ventas válidas para este mes.")
        return [], []

    # === Crear diccionario de presupuestos por ubicación (numéricos) ===
    presupuestos_dict = {}
    for _, row in presupuestos.iterrows():
        ub = row['ubicacion']
        pres = row['presupuesto']
        if pd.notna(pres) and pres > 0:
            presupuestos_dict[ub] = float(pres)
        else:
            print(f"⚠️ Presupuesto inválido para ubicación: {ub}")

    # === Verificar que todas las ubicaciones con ventas tengan presupuesto ===
    ubicaciones_ventas = set(ventas['ubicacion'].unique())
    ubicaciones_presupuesto = set(presupuestos_dict.keys())
    if not ubicaciones_ventas.issubset(ubicaciones_presupuesto):
        faltantes = ubicaciones_ventas - ubicaciones_presupuesto
        print(f"❌ ERROR: Faltan presupuestos para las ubicaciones: {faltantes}")
        return [], []

    resultados = []
    detalles_semanales = []
    semanas = get_weeks_for_month(year, month)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === Procesar cada ubicación ===
    for ubicacion, grupo_ubicacion in ventas.groupby('ubicacion'):
        presupuesto_ubicacion = presupuestos_dict[ubicacion]  # ✅ Valor correcto por ubicación
        venta_total_ubicacion = (grupo_ubicacion['cantidad'] * grupo_ubicacion['precio_publico']).sum()
        porc_cumpl = (venta_total_ubicacion / presupuesto_ubicacion) * 100

        # ESQUEMA 1: comisión mensual por ubicación
        if 75 <= porc_cumpl < 80:
            porc_com_mensual = 0.01
        elif 80 <= porc_cumpl < 90:
            porc_com_mensual = 0.0125
        elif 90 <= porc_cumpl < 110:
            porc_com_mensual = 0.02
        elif porc_cumpl >= 110:
            porc_com_mensual = 0.025
        else:
            porc_com_mensual = 0

        # === Procesar cada vendedor en la ubicación ===
        for vendedor, grupo_vendedor in grupo_ubicacion.groupby('vendedor'):
            grupo_vendedor['venta_total'] = grupo_vendedor['cantidad'] * grupo_vendedor['precio_publico']
            venta_total_vendedor = grupo_vendedor['venta_total'].sum()
            comision_mensual = venta_total_vendedor * porc_com_mensual

            # ESQUEMA 2
            juguetes = grupo_vendedor[
                (grupo_vendedor['familia_comercial'] == 'JUGUETE') &
                (~grupo_vendedor['marca'].astype(str).str.startswith('CXO', na=False)) &
                (grupo_vendedor['precio_publico'] > 1500)
            ]
            comision_juguetes = juguetes['venta_total'].sum() * 0.01

            cxo = grupo_vendedor[grupo_vendedor['marca'].astype(str).str.startswith('CXO', na=False)]
            comision_cxo = cxo['venta_total'].sum() * 0.06

            dusa = grupo_vendedor[
                (grupo_vendedor['marca'] == 'DUSA') &
                (grupo_vendedor['id_articulo'] != '5356')
            ]
            comision_dusa = dusa['venta_total'].sum() * 0.02

            shumatsu = grupo_vendedor[grupo_vendedor['id_articulo'] == '5356']
            comision_shumatsu = shumatsu['venta_total'].sum() * 0.06

            # === ✅ CÁLCULO SEMANAL CORRECTO: por ubicación ===
            comision_semanal_total = 0.0
            presupuesto_diario = presupuesto_ubicacion / 30.0  # ✅ ¡ESTO ES CLAVE!

            for i, semana in enumerate(semanas, start=1):
                dias_semana = len(semana)
                presupuesto_semana = presupuesto_diario * dias_semana

                fi, ff = semana[0], semana[-1]
                ventas_semana = grupo_vendedor[
                    (grupo_vendedor['fecha'].dt.date >= fi) &
                    (grupo_vendedor['fecha'].dt.date <= ff)
                ]
                venta_semana = ventas_semana['venta_total'].sum()

                # Solo paga si cumple la meta semanal
                if venta_semana >= presupuesto_semana:
                    comision_semana = venta_semana * 0.01
                else:
                    comision_semana = 0.0

                comision_semanal_total += comision_semana

                dias_str = ', '.join([d.strftime('%d/%m/%Y') for d in semana])
                detalles_semanales.append({
                    'vendedor': vendedor,
                    'ubicacion': ubicacion,
                    'mes': month,
                    'anio': year,
                    'semana_numero': i,
                    'fecha_inicio': fi.strftime('%Y-%m-%d'),
                    'fecha_fin': ff.strftime('%Y-%m-%d'),
                    'dias_incluidos': dias_str,
                    'dias_semana': dias_semana,
                    'presupuesto_diario': presupuesto_diario,          # ✅ Correcto
                    'presupuesto_semana': presupuesto_semana,          # ✅ Correcto
                    'venta_semana': venta_semana,
                    'comision_semana': comision_semana,
                    'cumplio_semana': venta_semana >= presupuesto_semana
                })

            total_comisiones = (
                comision_mensual + comision_juguetes + comision_cxo +
                comision_dusa + comision_shumatsu + comision_semanal_total
            )

            resultados.append({
                'vendedor': vendedor,
                'ubicacion': ubicacion,
                'presupuesto_ubicacion': presupuesto_ubicacion,
                'venta_total_ubicacion': venta_total_ubicacion,
                'porcentaje_cumplimiento_ubicacion': porc_cumpl,
                'venta_total_vendedor': venta_total_vendedor,
                'comision_mensual': comision_mensual,
                'comision_juguetes': comision_juguetes,
                'comision_cxo': comision_cxo,
                'comision_dusa': comision_dusa,
                'comision_shumatsu': comision_shumatsu,
                'comision_semanal': comision_semanal_total,
                'total_comisiones': total_comisiones
            })

    # === Guardar en base de datos ===
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comisiones_por_vendedor WHERE mes = ? AND anio = ?", (month, year))
    cursor.execute("DELETE FROM comisiones_semanales_por_vendedor WHERE mes = ? AND anio = ?", (month, year))

    for res in resultados:
        cursor.execute("""
        INSERT INTO comisiones_por_vendedor (
            vendedor, ubicacion, mes, anio, presupuesto_ubicacion,
            venta_total_ubicacion, porcentaje_cumplimiento_ubicacion,
            venta_total_vendedor, comision_mensual, comision_juguetes,
            comision_cxo, comision_dusa, comision_shumatsu,
            comision_semanal, total_comisiones, fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res['vendedor'], res['ubicacion'], month, year, res['presupuesto_ubicacion'],
            res['venta_total_ubicacion'], res['porcentaje_cumplimiento_ubicacion'],
            res['venta_total_vendedor'], res['comision_mensual'], res['comision_juguetes'],
            res['comision_cxo'], res['comision_dusa'], res['comision_shumatsu'],
            res['comision_semanal'], res['total_comisiones'], ahora
        ))

    for det in detalles_semanales:
        cursor.execute("""
        INSERT INTO comisiones_semanales_por_vendedor (
            vendedor, ubicacion, mes, anio, semana_numero,
            fecha_inicio, fecha_fin, dias_incluidos, dias_semana,
            presupuesto_diario, presupuesto_semana, venta_semana,
            comision_semana, cumplio_semana, fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            det['vendedor'], det['ubicacion'], det['mes'], det['anio'], det['semana_numero'],
            det['fecha_inicio'], det['fecha_fin'], det['dias_incluidos'], det['dias_semana'],
            det['presupuesto_diario'], det['presupuesto_semana'], det['venta_semana'],
            det['comision_semana'], int(det['cumplio_semana']), ahora
        ))

    conn.commit()
    conn.close()

    return resultados, detalles_semanales

def calcular_comisiones_por_vendedor2(
    db_path: str,
    year: int,
    month: int
):
    # Crear tablas si no existen
    crear_tabla_presupuestos_ubicaciones_si_no_existe(db_path)
    crear_tabla_comisiones_por_vendedor_si_no_existe(db_path)
    crear_tabla_comisiones_semanales_si_no_existe(db_path)

    ventas = cargar_ventas_desde_db(db_path, year, month)
    presupuestos = cargar_presupuestos_por_ubicacion(db_path, year, month)

    if ventas.empty:
        print("⚠️ No hay ventas válidas para este mes.")
        return []

    presupuestos_dict = dict(zip(presupuestos['ubicacion'], presupuestos['presupuesto']))
    resultados = []
    detalles_semanales = []

    semanas = get_weeks_for_month(year, month)
    presupuesto_global_mensual = presupuestos['presupuesto'].sum() if not presupuestos.empty else 0
    presupuesto_diario = presupuesto_global_mensual / 30 if presupuesto_global_mensual > 0 else 0

    # === Cálculo por ubicación ===
    for ubicacion, grupo_ubicacion in ventas.groupby('ubicacion'):
        presupuesto_ubicacion = presupuestos_dict.get(ubicacion, 0)
        venta_total_ubicacion = (grupo_ubicacion['cantidad'] * grupo_ubicacion['precio_publico']).sum()
        porc_cumpl = (venta_total_ubicacion / presupuesto_ubicacion) * 100 if presupuesto_ubicacion > 0 else 0

        if 75 <= porc_cumpl < 80:
            porc_com_mensual = 0.01
        elif 80 <= porc_cumpl < 90:
            porc_com_mensual = 0.0125
        elif 90 <= porc_cumpl < 110:
            porc_com_mensual = 0.02
        elif porc_cumpl >= 110:
            porc_com_mensual = 0.025
        else:
            porc_com_mensual = 0

        # === Por vendedor ===
        for vendedor, grupo_vendedor in grupo_ubicacion.groupby('vendedor'):
            grupo_vendedor['venta_total'] = grupo_vendedor['cantidad'] * grupo_vendedor['precio_publico']
            venta_total_vendedor = grupo_vendedor['venta_total'].sum()

            comision_mensual = venta_total_vendedor * porc_com_mensual

            # Esquemas 2
            juguetes = grupo_vendedor[
                (grupo_vendedor['familia_comercial'] == 'JUGUETE') &
                (~grupo_vendedor['marca'].astype(str).str.startswith('CXO', na=False)) &
                (grupo_vendedor['precio_publico'] > 1500)
            ]
            comision_juguetes = juguetes['venta_total'].sum() * 0.01

            cxo = grupo_vendedor[grupo_vendedor['marca'].astype(str).str.startswith('CXO', na=False)]
            comision_cxo = cxo['venta_total'].sum() * 0.06

            dusa = grupo_vendedor[
                (grupo_vendedor['marca'] == 'DUSA') &
                (grupo_vendedor['id_articulo'] != '5356')
            ]
            comision_dusa = dusa['venta_total'].sum() * 0.02

            shumatsu = grupo_vendedor[grupo_vendedor['id_articulo'] == '5356']
            comision_shumatsu = shumatsu['venta_total'].sum() * 0.06

            # === Cálculo semanal condicional ===
            comision_semanal_total = 0.0
            for i, semana in enumerate(semanas, start=1):
                dias_semana = len(semana)
                presupuesto_semana = presupuesto_diario * dias_semana

                fi, ff = semana[0], semana[-1]
                ventas_semana = grupo_vendedor[
                    (grupo_vendedor['fecha'].dt.date >= fi) &
                    (grupo_vendedor['fecha'].dt.date <= ff)
                    ]
                venta_semana = ventas_semana['venta_total'].sum()

                # 🔸 NUEVA REGLA: solo si venta >= presupuesto_semana
                if venta_semana >= presupuesto_semana:
                    comision_semana = venta_semana * 0.01
                else:
                    comision_semana = 0.0

                comision_semanal_total += comision_semana

                # Guardar detalle semanal
                dias_str = ', '.join([d.strftime('%d/%m/%Y') for d in semana])
                detalles_semanales.append({
                    'vendedor': vendedor,
                    'ubicacion': ubicacion,
                    'mes': month,
                    'anio': year,
                    'semana_numero': i,
                    'fecha_inicio': fi.strftime('%Y-%m-%d'),
                    'fecha_fin': ff.strftime('%Y-%m-%d'),
                    'dias_incluidos': dias_str,
                    'dias_semana': dias_semana,
                    'presupuesto_diario': presupuesto_diario,
                    'presupuesto_semana': presupuesto_semana,
                    'venta_semana': venta_semana,
                    'comision_semana': comision_semana,
                    'cumplio_semana': venta_semana >= presupuesto_semana  # opcional, para diagnóstico
                })

            total_comisiones = (
                comision_mensual + comision_juguetes + comision_cxo +
                comision_dusa + comision_shumatsu + comision_semanal_total
            )

            resultados.append({
                'vendedor': vendedor,
                'ubicacion': ubicacion,
                'presupuesto_ubicacion': presupuesto_ubicacion,
                'venta_total_ubicacion': venta_total_ubicacion,
                'porcentaje_cumplimiento_ubicacion': porc_cumpl,
                'venta_total_vendedor': venta_total_vendedor,
                'comision_mensual': comision_mensual,
                'comision_juguetes': comision_juguetes,
                'comision_cxo': comision_cxo,
                'comision_dusa': comision_dusa,
                'comision_shumatsu': comision_shumatsu,
                'comision_semanal': comision_semanal_total,
                'total_comisiones': total_comisiones
            })

    # === Guardar en base de datos ===
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM comisiones_por_vendedor WHERE mes = ? AND anio = ?", (month, year))
    cursor.execute("DELETE FROM comisiones_semanales_por_vendedor WHERE mes = ? AND anio = ?", (month, year))

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for res in resultados:
        cursor.execute("""
        INSERT INTO comisiones_por_vendedor (
            vendedor, ubicacion, mes, anio, presupuesto_ubicacion,
            venta_total_ubicacion, porcentaje_cumplimiento_ubicacion,
            venta_total_vendedor, comision_mensual, comision_juguetes,
            comision_cxo, comision_dusa, comision_shumatsu,
            comision_semanal, total_comisiones, fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res['vendedor'], res['ubicacion'], month, year, res['presupuesto_ubicacion'],
            res['venta_total_ubicacion'], res['porcentaje_cumplimiento_ubicacion'],
            res['venta_total_vendedor'], res['comision_mensual'], res['comision_juguetes'],
            res['comision_cxo'], res['comision_dusa'], res['comision_shumatsu'],
            res['comision_semanal'], res['total_comisiones'], ahora
        ))

    for det in detalles_semanales:
        cursor.execute("""
        INSERT INTO comisiones_semanales_por_vendedor (
            vendedor, ubicacion, mes, anio, semana_numero,
            fecha_inicio, fecha_fin, dias_incluidos, dias_semana,
            presupuesto_diario, presupuesto_semana, venta_semana,
            comision_semana, cumplio_semana, fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            det['vendedor'], det['ubicacion'], det['mes'], det['anio'], det['semana_numero'],
            det['fecha_inicio'], det['fecha_fin'], det['dias_incluidos'], det['dias_semana'],
            det['presupuesto_diario'], det['presupuesto_semana'], det['venta_semana'],
            det['comision_semana'], int(det['cumplio_semana']), ahora  # SQLite usa 1/0 para boolean
        ))

    conn.commit()
    conn.close()

    return resultados, detalles_semanales

def exportar_a_excel(resultados: list, detalles_semanales: list, archivo_salida: str):
    df_resultados = pd.DataFrame(resultados)
    df_semanal = pd.DataFrame(detalles_semanales)

    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df_resultados.to_excel(writer, sheet_name='Comisiones por Vendedor', index=False)
        df_semanal.to_excel(writer, sheet_name='Desglose Semanal', index=False)

        # Resumen por ubicación
        if not df_resultados.empty:
            resumen_ubic = df_resultados.groupby('ubicacion').agg({
                'venta_total_ubicacion': 'first',
                'porcentaje_cumplimiento_ubicacion': 'first',
                'total_comisiones': 'sum'
            }).reset_index()
            resumen_ubic.to_excel(writer, sheet_name='Resumen por Ubicación', index=False)

        # Resumen por vendedor
        if not df_resultados.empty:
            resumen_vend = df_resultados[['vendedor', 'ubicacion', 'venta_total_vendedor', 'total_comisiones']].copy()
            resumen_vend.to_excel(writer, sheet_name='Resumen por Vendedor', index=False)

    print(f"📄 Reporte detallado guardado en: {archivo_salida}")

# === EJECUCIÓN ===
if __name__ == "__main__":
    DB_PATH = "comisiones.db"
    YEAR = 2025
    MONTH = 10

    print(f"🔍 Calculando comisiones con desglose semanal para {MONTH}/{YEAR}...")
    resultados, detalles = calcular_comisiones_por_vendedor(DB_PATH, YEAR, MONTH)

    print("\n✅ RESULTADOS POR VENDEDOR")
    print("=" * 120)
    for res in resultados:
        print(f"Vendedor: {res['vendedor']} | Ubicación: {res['ubicacion']}")
        print(f"  - TOTAL COMISIÓN: ${res['total_comisiones']:,.2f}")
        print("-" * 80)

    # === EXPORTAR A EXCEL ===
    archivo_excel = f"comisiones_{MONTH}_{YEAR}_detallado.xlsx"
    exportar_a_excel(resultados, detalles, archivo_excel)