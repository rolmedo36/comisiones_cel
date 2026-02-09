# calculo_comisiones_unificado.py
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# Lista de vendedores con esquema personal
VENDEDORES_ESQUEMA1_PERSONAL = {
    'ALFONSO  M CARBALLAR',
    'ANGEL DANILO RODRIGUEZ LOPEZ',
    'GERMAN  GUZMAN AGUIRRE'
}

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

def crear_tabla_vendedores_esquema_personal_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendedores_esquema_personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto_vendedor REAL NOT NULL,
        UNIQUE(vendedor, mes, anio)
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

def crear_tabla_comisiones_vendedores_personales_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comisiones_vendedores_personales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto_vendedor REAL NOT NULL,
        venta_total_vendedor REAL NOT NULL,
        porcentaje_cumplimiento_personal REAL NOT NULL,
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
    df['venta_total'] = df['cantidad'] * df['precio_publico']
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

def cargar_vendedores_esquema_personal(db_path: str, year: int, month: int) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    query = """
    SELECT vendedor, presupuesto_vendedor
    FROM vendedores_esquema_personal
    WHERE mes = ? AND anio = ?;
    """
    df = pd.read_sql_query(query, conn, params=(month, year))
    conn.close()

    df['presupuesto_vendedor'] = pd.to_numeric(df['presupuesto_vendedor'], errors='coerce')
    df = df.dropna(subset=['presupuesto_vendedor'])
    return df

def calcular_porcentajes_esquema_personal(porc_cumplimiento: float):
    if 70 <= porc_cumplimiento < 76:
        return {
            'comision_mensual': 0.005,
            'comision_cxo': 0.03,
            'comision_juguetes': 0.005,
            'comision_dusa': 0.01,
            'comision_shumatsu': 0.03
        }
    elif 76 <= porc_cumplimiento < 81:
        return {
            'comision_mensual': 0.01,
            'comision_cxo': 0.045,
            'comision_juguetes': 0.0075,
            'comision_dusa': 0.015,
            'comision_shumatsu': 0.045
        }
    elif 81 <= porc_cumplimiento <= 100:
        return {
            'comision_mensual': 0.02,
            'comision_cxo': 0.06,
            'comision_juguetes': 0.01,
            'comision_dusa': 0.02,
            'comision_shumatsu': 0.06
        }
    elif porc_cumplimiento > 100:
        return {
            'comision_mensual': 0.025,
            'comision_cxo': 0.06,
            'comision_juguetes': 0.01,
            'comision_dusa': 0.02,
            'comision_shumatsu': 0.06
        }
    else:
        return {
            'comision_mensual': 0,
            'comision_cxo': 0,
            'comision_juguetes': 0,
            'comision_dusa': 0,
            'comision_shumatsu': 0
        }

def obtener_porcentaje_comision_ubicacion(porcentaje_cumplimiento: float) -> float:
    """Nueva función: tabla específica para esquema por ubicación"""
    if 75 <= porcentaje_cumplimiento < 80:
        return 0.0075
    elif 80 <= porcentaje_cumplimiento < 90:
        return 0.0125
    elif 90 <= porcentaje_cumplimiento < 110:
        return 0.02
    elif porcentaje_cumplimiento >= 110:
        return 0.025
    else:
        return 0.0

def calcular_comisiones_unificadas(db_path: str, year: int, month: int):
    crear_tabla_presupuestos_ubicaciones_si_no_existe(db_path)
    crear_tabla_vendedores_esquema_personal_si_no_existe(db_path)
    crear_tabla_comisiones_por_vendedor_si_no_existe(db_path)
    crear_tabla_comisiones_semanales_si_no_existe(db_path)
    crear_tabla_comisiones_vendedores_personales_si_no_existe(db_path)

    ventas = cargar_ventas_desde_db(db_path, year, month)
    if ventas.empty:
        print("⚠️ No hay ventas válidas para este mes.")
        return [], [], []

    presupuestos = cargar_presupuestos_por_ubicacion(db_path, year, month)
    vendedores_personal = cargar_vendedores_esquema_personal(db_path, year, month)

    presupuestos_ubicacion = {row['ubicacion']: float(row['presupuesto']) for _, row in presupuestos.iterrows()}
    presupuestos_vendedor = {row['vendedor']: float(row['presupuesto_vendedor']) for _, row in vendedores_personal.iterrows()}

    # Validar que todas las ubicaciones tengan presupuesto
    ubicaciones_con_ventas = set(ventas['ubicacion'].unique())
    ubicaciones_con_presupuesto = set(presupuestos_ubicacion.keys())
    faltantes = ubicaciones_con_ventas - ubicaciones_con_presupuesto
    if faltantes:
        print(f"❌ ERROR: Faltan presupuestos para ubicaciones: {faltantes}")
        return [], [], []

    resultados = []
    detalles_semanales = []
    resultados_personales = []
    semanas = get_weeks_for_month(year, month)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pre-calcular venta total por ubicación
    venta_total_por_ubicacion = ventas.groupby('ubicacion')['venta_total'].sum().to_dict()

    for vendedor, grupo_vendedor in ventas.groupby('vendedor'):
        grupo_vendedor = grupo_vendedor.copy()
        grupo_vendedor = grupo_vendedor.dropna(subset=['cantidad', 'precio_publico'])
        grupo_vendedor['venta_total'] = grupo_vendedor['cantidad'] * grupo_vendedor['precio_publico']

        es_esquema_personal = vendedor in VENDEDORES_ESQUEMA1_PERSONAL or vendedor in presupuestos_vendedor

        if es_esquema_personal:
            if vendedor not in presupuestos_vendedor:
                print(f"⚠️ {vendedor} está en lista personal pero sin presupuesto — usando por ubicación")
                es_esquema_personal = False

        if es_esquema_personal:
            # Esquema personal: usar su propio presupuesto
            presupuesto_vendedor_valor = presupuestos_vendedor[vendedor]
            venta_total_vendedor_global = grupo_vendedor['venta_total'].sum()
            porc_cumplimiento = (venta_total_vendedor_global / presupuesto_vendedor_valor) * 100
            porcentajes = calcular_porcentajes_esquema_personal(porc_cumplimiento)

            for ubicacion_local, grupo_ubic in grupo_vendedor.groupby('ubicacion'):
                venta_en_ubic = grupo_ubic['venta_total'].sum()

                juguetes = grupo_ubic[
                    (grupo_ubic['familia_comercial'] == 'JUGUETE') &
                    (~grupo_ubic['marca'].astype(str).str.startswith('CXO', na=False)) &
                    (grupo_ubic['precio_publico'] > 1500)
                ]
                comision_juguetes = juguetes['venta_total'].sum() * porcentajes['comision_juguetes']

                cxo_ventas = grupo_ubic[grupo_ubic['marca'].astype(str).str.startswith('CXO', na=False)]
                comision_cxo = cxo_ventas['venta_total'].sum() * porcentajes['comision_cxo']

                dusa = grupo_ubic[
                    (grupo_ubic['marca'] == 'DUSA') &
                    (grupo_ubic['id_articulo'] != '5356')
                ]
                comision_dusa = dusa['venta_total'].sum() * porcentajes['comision_dusa']

                shumatsu = grupo_ubic[grupo_ubic['id_articulo'] == '5356']
                comision_shumatsu = shumatsu['venta_total'].sum() * porcentajes['comision_shumatsu']

                comision_mensual = venta_en_ubic * porcentajes['comision_mensual']

                # Cálculo semanal
                comision_semanal = 0.0
                presupuesto_ubicacion_valor = presupuestos_ubicacion[ubicacion_local]
                presupuesto_diario = presupuesto_ubicacion_valor / 30.0

                for i, semana in enumerate(semanas, start=1):
                    dias_semana = len(semana)
                    presupuesto_semana = presupuesto_diario * dias_semana
                    fi, ff = semana[0], semana[-1]
                    ventas_semana = grupo_ubic[
                        (grupo_ubic['fecha'].dt.date >= fi) &
                        (grupo_ubic['fecha'].dt.date <= ff)
                    ]
                    venta_semana = ventas_semana['venta_total'].sum()
                    comision_semana_valor = venta_semana * 0.01 if venta_semana >= presupuesto_semana else 0.0
                    if venta_semana >= presupuesto_semana:
                        comision_semanal += comision_semana_valor

                    dias_str = ', '.join([d.strftime('%d/%m/%Y') for d in semana])
                    detalles_semanales.append({
                        'vendedor': vendedor,
                        'ubicacion': ubicacion_local,
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
                        'comision_semana': comision_semana_valor,
                        'cumplio_semana': venta_semana >= presupuesto_semana
                    })

                resultados_personales.append({
                    'vendedor': vendedor,
                    'ubicacion': ubicacion_local,
                    'presupuesto_vendedor': presupuesto_vendedor_valor,
                    'venta_total_vendedor': venta_en_ubic,
                    'venta_total_vendedor_global': venta_total_vendedor_global,
                    'porcentaje_cumplimiento_personal': porc_cumplimiento,
                    'comision_mensual': comision_mensual,
                    'comision_juguetes': comision_juguetes,
                    'comision_cxo': comision_cxo,
                    'comision_dusa': comision_dusa,
                    'comision_shumatsu': comision_shumatsu,
                    'comision_semanal': comision_semanal,
                    'total_comisiones': (
                        comision_mensual + comision_juguetes + comision_cxo +
                        comision_dusa + comision_shumatsu + comision_semanal
                    )
                })

        else:
            # === Esquema por ubicación (con nueva tabla de porcentajes) ===
            for ubicacion_local, grupo_ubic in grupo_vendedor.groupby('ubicacion'):
                # Venta total de la UBICACIÓN (todos los vendedores)
                venta_total_ubicacion = venta_total_por_ubicacion[ubicacion_local]
                presupuesto_ubicacion_valor = presupuestos_ubicacion[ubicacion_local]
                porc_cumpl_ubicacion = (venta_total_ubicacion / presupuesto_ubicacion_valor) * 100

                # ✅ NUEVO: Usar tabla específica para comisión
                porc_com_mensual = obtener_porcentaje_comision_ubicacion(porc_cumpl_ubicacion)

                # Venta del vendedor en esta ubicación
                venta_vendedor_en_ubic = grupo_ubic['venta_total'].sum()

                # Comisión mensual = venta del vendedor × % de la tienda
                comision_mensual = venta_vendedor_en_ubic * porc_com_mensual

                # Comisiones adicionales (juguetes, CXO, etc.)
                cxo_ventas = grupo_ubic[grupo_ubic['marca'].astype(str).str.startswith('CXO', na=False)]
                comision_cxo = cxo_ventas['venta_total'].sum() * 0.06

                juguetes = grupo_ubic[
                    (grupo_ubic['familia_comercial'] == 'JUGUETE') &
                    (~grupo_ubic['marca'].astype(str).str.startswith('CXO', na=False)) &
                    (grupo_ubic['precio_publico'] > 1500)
                ]
                comision_juguetes = juguetes['venta_total'].sum() * 0.01

                dusa = grupo_ubic[
                    (grupo_ubic['marca'] == 'DUSA') &
                    (grupo_ubic['id_articulo'] != '5356')
                ]
                comision_dusa = dusa['venta_total'].sum() * 0.02

                shumatsu = grupo_ubic[grupo_ubic['id_articulo'] == '5356']
                comision_shumatsu = shumatsu['venta_total'].sum() * 0.06

                # Cálculo semanal
                comision_semanal = 0.0
                presupuesto_diario = presupuesto_ubicacion_valor / 30.0

                for i, semana in enumerate(semanas, start=1):
                    dias_semana = len(semana)
                    presupuesto_semana = presupuesto_diario * dias_semana
                    fi, ff = semana[0], semana[-1]
                    ventas_semana = grupo_ubic[
                        (grupo_ubic['fecha'].dt.date >= fi) &
                        (grupo_ubic['fecha'].dt.date <= ff)
                    ]
                    venta_semana = ventas_semana['venta_total'].sum()
                    comision_semana_valor = venta_semana * 0.01 if venta_semana >= presupuesto_semana else 0.0
                    if venta_semana >= presupuesto_semana:
                        comision_semanal += comision_semana_valor

                    dias_str = ', '.join([d.strftime('%d/%m/%Y') for d in semana])
                    detalles_semanales.append({
                        'vendedor': vendedor,
                        'ubicacion': ubicacion_local,
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
                        'comision_semana': comision_semana_valor,
                        'cumplio_semana': venta_semana >= presupuesto_semana
                    })

                resultados.append({
                    'vendedor': vendedor,
                    'ubicacion': ubicacion_local,
                    'presupuesto_ubicacion': presupuesto_ubicacion_valor,
                    'venta_total_ubicacion': venta_total_ubicacion,
                    'porcentaje_cumplimiento_ubicacion': porc_cumpl_ubicacion,
                    'venta_total_vendedor': venta_vendedor_en_ubic,
                    'comision_mensual': comision_mensual,
                    'comision_juguetes': comision_juguetes,
                    'comision_cxo': comision_cxo,
                    'comision_dusa': comision_dusa,
                    'comision_shumatsu': comision_shumatsu,
                    'comision_semanal': comision_semanal,
                    'total_comisiones': (
                        comision_mensual + comision_juguetes + comision_cxo +
                        comision_dusa + comision_shumatsu + comision_semanal
                    )
                })

    # Guardar en base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comisiones_por_vendedor WHERE mes = ? AND anio = ?", (month, year))
    cursor.execute("DELETE FROM comisiones_semanales_por_vendedor WHERE mes = ? AND anio = ?", (month, year))
    cursor.execute("DELETE FROM comisiones_vendedores_personales WHERE mes = ? AND anio = ?", (month, year))

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

    for res_p in resultados_personales:
        cursor.execute("""
        INSERT INTO comisiones_vendedores_personales (
            vendedor, mes, anio, presupuesto_vendedor,
            venta_total_vendedor, porcentaje_cumplimiento_personal,
            comision_mensual, comision_juguetes, comision_cxo,
            comision_dusa, comision_shumatsu, comision_semanal,
            total_comisiones, fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res_p['vendedor'], month, year, res_p['presupuesto_vendedor'],
            res_p['venta_total_vendedor'], res_p['porcentaje_cumplimiento_personal'],
            res_p['comision_mensual'], res_p['comision_juguetes'], res_p['comision_cxo'],
            res_p['comision_dusa'], res_p['comision_shumatsu'], res_p['comision_semanal'],
            res_p['total_comisiones'], ahora
        ))

    conn.commit()
    conn.close()

    return resultados, detalles_semanales, resultados_personales

def exportar_a_excel(resultados, detalles, personales, archivo_salida: str, db_path: str, year: int, month: int):
    df_resultados = pd.DataFrame(resultados)
    df_semanal = pd.DataFrame(detalles)
    df_personal = pd.DataFrame(personales)

    # Hoja de Validación de Datos
    conn = sqlite3.connect(db_path)
    query = f"""
    SELECT 
        ubicacion,
        SUM(cantidad * precio_publico) AS venta_total
    FROM ventas
    WHERE substr(fecha, 7, 4) = '{year}' AND substr(fecha, 4, 2) = '{month:02d}'
    GROUP BY ubicacion;
    """
    df_validacion_ubic = pd.read_sql_query(query, conn)
    conn.close()

    total_ventas_mes = df_validacion_ubic['venta_total'].sum()
    num_transacciones = 0
    conn = sqlite3.connect(db_path)
    query_trans = f"""
    SELECT COUNT(DISTINCT transaccion) AS n
    FROM ventas
    WHERE substr(fecha, 7, 4) = '{year}' AND substr(fecha, 4, 2) = '{month:02d}';
    """
    df_trans = pd.read_sql_query(query_trans, conn)
    conn.close()
    num_transacciones = df_trans['n'].iloc[0] if not df_trans.empty else 0
    ticket_promedio_global = total_ventas_mes / num_transacciones if num_transacciones > 0 else 0

    df_validacion = pd.DataFrame({
        'Concepto': [
            'Total Ventas del Mes',
            'Número de Transacciones Únicas',
            'Ticket Promedio Global'
        ],
        'Valor': [
            total_ventas_mes,
            num_transacciones,
            ticket_promedio_global
        ]
    })

    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df_resultados.to_excel(writer, sheet_name='Comisiones por Vendedor', index=False)
        df_semanal.to_excel(writer, sheet_name='Desglose Semanal', index=False)
        if not df_personal.empty:
            df_personal.to_excel(writer, sheet_name='Comisiones Personales', index=False)

        # Resumen por Vendedor Total
        resumen_total = []
        for res in resultados:
            resumen_total.append({
                'vendedor': res['vendedor'],
                'ubicacion': res['ubicacion'],
                'esquema': 'ubicacion',
                'comision_ventas_fijas': (
                    res['comision_mensual'] +
                    res['comision_juguetes'] +
                    res['comision_cxo'] +
                    res['comision_dusa'] +
                    res['comision_shumatsu']
                ),
                'comision_semanal': res['comision_semanal'],
                'total_comisiones': res['total_comisiones']
            })

        for res in personales:
            resumen_total.append({
                'vendedor': res['vendedor'],
                'ubicacion': res['ubicacion'],
                'esquema': 'personal',
                'comision_ventas_fijas': (
                    res['comision_mensual'] +
                    res['comision_juguetes'] +
                    res['comision_cxo'] +
                    res['comision_dusa'] +
                    res['comision_shumatsu']
                ),
                'comision_semanal': res['comision_semanal'],
                'total_comisiones': res['total_comisiones']
            })

        df_resumen_total = pd.DataFrame(resumen_total)
        if not df_resumen_total.empty:
            df_resumen_total = df_resumen_total.sort_values(['vendedor', 'ubicacion']).reset_index(drop=True)
            df_resumen_total.to_excel(writer, sheet_name='Resumen por Vendedor Total', index=False)

        # Resumen por Ubicación
        if not df_resultados.empty:
            resumen_ubic = df_resultados.groupby('ubicacion').agg({
                'venta_total_ubicacion': 'first',
                'porcentaje_cumplimiento_ubicacion': 'mean',
                'total_comisiones': 'sum'
            }).reset_index()
            resumen_ubic.to_excel(writer, sheet_name='Resumen por Ubicación', index=False)

        # Hoja de Validación
        df_validacion.to_excel(writer, sheet_name='Validación de Datos', index=False)
        df_validacion_ubic.to_excel(writer, sheet_name='Ventas por Ubicación (Validación)', index=False)

    print(f"✅ Reporte guardado en: {archivo_salida}")

if __name__ == "__main__":
    DB_PATH = "comisiones.db"
    YEAR = 2026
    MONTH = 1

    print(f"🔍 Calculando comisiones UNIFICADAS para {MONTH}/{YEAR}...")
    resultados, detalles, personales = calcular_comisiones_unificadas(DB_PATH, YEAR, MONTH)

    archivo_excel = f"comisiones_unificadas_{MONTH}_{YEAR}.xlsx"
    exportar_a_excel(resultados, detalles, personales, archivo_excel, DB_PATH, YEAR, MONTH)