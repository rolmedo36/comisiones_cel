# calculo_comisiones_unificado.py
import pandas as pd
import sqlite3
from datetime import datetime, timedelta, date
from typing import List

# Lista de vendedores que usan Esquema 1 personalizado
VENDEDORES_ESQUEMA1_PERSONAL = {
    'ALFONSO  M CARBALLAR',
    'ANGEL DANILO RODRIGUEZ LOPEZ',
    'GERMAN  GUZMAN AGUIRRE'
}

def get_weeks_for_month(year: int, month: int) -> List[List[date]]:
    """
    Genera semanas para cálculo de comisiones según reglas de negocio:

    1. Semana 1:
       - Si 1ro es Dom, Lun o Mar → Días 1 al 8
       - Si 1ro es Mié, Jue, Vie o Sáb → Días 1 hasta el próximo Domingo
    2. Semanas 2+: Bloques de 7 días (Lunes a Domingo)
    3. Última semana:
       - Si tiene < 5 días → se fusiona con la semana anterior
       - Si tiene >= 5 días → se queda como está
    4. Solo días del mes actual

    Args:
        year (int): Año
        month (int): Mes (1-12)

    Returns:
        List[List[date]]: Lista de semanas
    """
    # 1. Obtener último día del mes
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)

    last_day_of_month = (next_month_first - timedelta(days=1)).day
    first_day = date(year, month, 1)

    weeks = []

    # 2. Generar Semana 1
    week_1 = []
    weekday_of_first = first_day.weekday()  # 0=Lun, 1=Mar, 2=Mie, 3=Jue, 4=Vie, 5=Sab, 6=Dom

    # Si es Miércoles(2), Jueves(3), Viernes(4) o Sábado(5) → hasta el próximo Domingo
    if weekday_of_first in [2, 3, 4, 5]:
        days_until_sunday = 6 - weekday_of_first
        end_day_week1 = 1 + days_until_sunday
    else:
        # Domingo(6), Lunes(0) o Martes(1) → días 1 al 8
        end_day_week1 = 8

    # Asegurar no pasar del último día del mes
    end_day_week1 = min(end_day_week1, last_day_of_month)

    for day in range(1, end_day_week1 + 1):
        week_1.append(date(year, month, day))
    weeks.append(week_1)

    # 3. Generar Semanas 2+ (bloques de 7 días)
    current_day = end_day_week1 + 1

    while current_day <= last_day_of_month:
        week_days = []

        # Agregar hasta 7 días o hasta fin de mes
        for i in range(7):
            day_num = current_day + i
            if day_num > last_day_of_month:
                break
            week_days.append(date(year, month, day_num))

        if week_days:
            weeks.append(week_days)
            current_day += len(week_days)
        else:
            break

    # 4. Aplicar regla de fusión: si última semana < 5 días, fusionar con la anterior
    if len(weeks) > 1 and len(weeks[-1]) < 4:
        last_week = weeks.pop()  # Remover última semana
        weeks[-1].extend(last_week)  # Fusionar con la semana anterior

    return weeks

def get_weeks_for_month_resp(year, month):
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

        if temp_date.weekday() == 6:
            days_in_week.append(temp_date.date())
            temp_date += timedelta(days=1)

        if len(days_in_week) < 4:
            while temp_date.weekday() != 6:
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
        venta_total_ubicacion REAL NOT NULL,   -- ✅ Ahora es: ventas del vendedor EN esa ubicación
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
        vendedor,
        id_pos
    FROM ventas
    WHERE 1=1
        -- AND ubicacion = 'Arcos-C';
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce')
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce')
    df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')
    if 'id_pos' in df.columns:
        df['id_pos'] = df['id_pos'].str.extract(r'-T(.*?)-D')

    # Filtrar solo el mes/año solicitado
    df = df[
        (df['fecha'].dt.year == year) &
        (df['fecha'].dt.month == month)
    ].copy()

    # Eliminar filas con datos inválidos
    df = df.dropna(subset=['fecha', 'cantidad', 'precio_publico', 'vendedor', 'ubicacion'])
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

def calcular_comisiones_unificadas(db_path: str, year: int, month: int):
    # 1. Asegurar tablas
    crear_tabla_presupuestos_ubicaciones_si_no_existe(db_path)
    crear_tabla_vendedores_esquema_personal_si_no_existe(db_path)
    crear_tabla_comisiones_por_vendedor_si_no_existe(db_path)
    crear_tabla_comisiones_semanales_si_no_existe(db_path)
    crear_tabla_comisiones_vendedores_personales_si_no_existe(db_path)

    # 2. Carga de datos
    ventas = cargar_ventas_desde_db(db_path, year, month)
    if ventas.empty:
        print("⚠️ No hay ventas válidas.")
        return [], [], []

    presupuestos = cargar_presupuestos_por_ubicacion(db_path, year, month)
    vendedores_personal = cargar_vendedores_esquema_personal(db_path, year, month)

    presupuestos_ubicacion = {row['ubicacion']: float(row['presupuesto']) for _, row in presupuestos.iterrows()}
    presupuestos_vendedor = {row['vendedor']: float(row['presupuesto_vendedor']) for _, row in
                             vendedores_personal.iterrows()}

    semanas = get_weeks_for_month(year, month)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    resultados = []
    detalles_semanales = []
    resultados_personales = []

    # === PASO 1: CÁLCULO INDIVIDUAL ===
    for (vendedor, ubicacion), grupo in ventas.groupby(['vendedor', 'ubicacion']):
        grupo = grupo.copy()
        grupo['venta_total'] = pd.to_numeric(grupo['cantidad'], errors='coerce').fillna(0) * \
                               pd.to_numeric(grupo['precio_publico'], errors='coerce').fillna(0)

        venta_total_v = grupo['venta_total'].sum()
        if venta_total_v <= 0: continue

        presu_ubi_val = presupuestos_ubicacion.get(ubicacion, 0)
        if presu_ubi_val == 0: continue

        porc_cumpl_ubi = (venta_total_v / presu_ubi_val) * 100

        # Inicialización
        esquema_personal = False
        porcentajes = {}
        porc_com_mensual = 0.0

        if vendedor in VENDEDORES_ESQUEMA1_PERSONAL or vendedor in presupuestos_vendedor:
            if vendedor in presupuestos_vendedor:
                esquema_personal = True
                presu_v_val = presupuestos_vendedor[vendedor]
                porc_cumpl_p = (venta_total_v / presu_v_val) * 100
                porcentajes = calcular_porcentajes_esquema_personal(porc_cumpl_p)

        if not esquema_personal:
            if 75 <= porc_cumpl_ubi < 80:
                porc_com_mensual = 0.01
            elif 80 <= porc_cumpl_ubi < 90:
                porc_com_mensual = 0.0125
            elif 90 <= porc_cumpl_ubi < 110:
                porc_com_mensual = 0.02
            elif porc_cumpl_ubi >= 110:
                porc_com_mensual = 0.025

        # Marcas
        com_juguetes = grupo[(grupo['familia_comercial'] == 'JUGUETE') & (
            ~grupo['marca'].astype(str).str.startswith('CXO', na=False)) & (grupo['precio_publico'] > 1500)][
                           'venta_total'].sum() * (
                           porcentajes.get('comision_juguetes', 0.01) if esquema_personal else 0.01)
        com_cxo = grupo[grupo['marca'].astype(str).str.startswith('CXO', na=False)]['venta_total'].sum() * (
            porcentajes.get('comision_cxo', 0.06) if esquema_personal else 0.06)
        com_dusa = grupo[(grupo['marca'] == 'DUSA') & (grupo['id_articulo'] != '5356')]['venta_total'].sum() * (
            porcentajes.get('comision_dusa', 0.02) if esquema_personal else 0.02)
        com_shumatsu = grupo[grupo['id_articulo'] == '5356']['venta_total'].sum() * (
            porcentajes.get('comision_shumatsu', 0.06) if esquema_personal else 0.06)
        com_mensual = venta_total_v * (
            porcentajes.get('comision_mensual', porc_com_mensual) if esquema_personal else porc_com_mensual)

        res_vendedor = {
            'vendedor': vendedor, 'ubicacion': ubicacion, 'mes': month, 'anio': year,
            'presupuesto_ubicacion': presu_ubi_val, 'venta_total_ubicacion': venta_total_v,
            'porcentaje_cumplimiento_ubicacion': porc_cumpl_ubi, 'venta_total_vendedor': venta_total_v,
            'comision_mensual': com_mensual, 'comision_juguetes': com_juguetes,
            'comision_cxo': com_cxo, 'comision_dusa': com_dusa, 'comision_shumatsu': com_shumatsu,
            'comision_semanal': 0.0,
            'total_comisiones': com_mensual + com_juguetes + com_cxo + com_dusa + com_shumatsu,
            'fecha_calculo': ahora
        }
        resultados.append(res_vendedor)

        if esquema_personal:
            # AQUÍ: Mantenemos 'ubicacion' para el Excel, se filtrará solo al guardar en DB
            res_p = res_vendedor.copy()
            res_p['presupuesto_vendedor'] = presu_v_val
            res_p['porcentaje_cumplimiento_personal'] = porc_cumpl_p
            res_p['venta_total_vendedor_global'] = venta_total_v
            resultados_personales.append(res_p)

    # === PASO 2: BONO SEMANAL TIENDA ===
    for ubi, presu_total in presupuestos_ubicacion.items():
        presu_diario = presu_total / 30.0
        v_tienda = ventas[ventas['ubicacion'] == ubi].copy()
        v_tienda['venta_total'] = pd.to_numeric(v_tienda['cantidad'], errors='coerce').fillna(0) * \
                                  pd.to_numeric(v_tienda['precio_publico'], errors='coerce').fillna(0)

        for i, sem in enumerate(semanas, start=1):
            presu_sem = presu_diario * len(sem)
            v_sem = v_tienda[(v_tienda['fecha'].dt.date >= sem[0]) & (v_tienda['fecha'].dt.date <= sem[-1])][
                'venta_total'].sum()
            cumple = v_sem >= presu_sem
            detalles_semanales.append({
                'vendedor': f"BONO TIENDA {ubi}", 'ubicacion': ubi, 'mes': month, 'anio': year, 'semana_numero': i,
                'fecha_inicio': sem[0].strftime('%Y-%m-%d'), 'fecha_fin': sem[-1].strftime('%Y-%m-%d'),
                'dias_incluidos': ', '.join([d.strftime('%d/%m') for d in sem]), 'dias_semana': len(sem),
                'presupuesto_diario': presu_diario, 'presupuesto_semana': presu_sem, 'venta_semana': v_sem,
                'comision_semana': v_sem * 0.01 if cumple else 0.0, 'cumplio_semana': int(cumple),
                'fecha_calculo': ahora
            })

    # === PASO 3: GUARDADO SEGURO EN DB ===
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM comisiones_por_vendedor WHERE mes = ? AND anio = ?", (month, year))
    conn.execute("DELETE FROM comisiones_semanales_por_vendedor WHERE mes = ? AND anio = ?", (month, year))
    conn.execute("DELETE FROM comisiones_vendedores_personales WHERE mes = ? AND anio = ?", (month, year))

    if resultados:
        pd.DataFrame(resultados).to_sql('comisiones_por_vendedor', conn, if_exists='append', index=False)

    if detalles_semanales:
        pd.DataFrame(detalles_semanales).to_sql('comisiones_semanales_por_vendedor', conn, if_exists='append',
                                                index=False)

    if resultados_personales:
        # AQUÍ ESTÁ EL TRUCO: Creamos un DF y eliminamos la columna 'ubicacion' solo para la DB
        df_personales_db = pd.DataFrame(resultados_personales).drop(columns=['ubicacion'], errors='ignore')
        # También eliminamos otras que no existan en tu tabla personal según tu esquema original
        columnas_validas = [
            'vendedor', 'mes', 'anio', 'presupuesto_vendedor', 'venta_total_vendedor',
            'porcentaje_cumplimiento_personal', 'comision_mensual', 'comision_juguetes',
            'comision_cxo', 'comision_dusa', 'comision_shumatsu', 'comision_semanal',
            'total_comisiones', 'fecha_calculo'
        ]
        df_personales_db = df_personales_db[[c for c in columnas_validas if c in df_personales_db.columns]]
        df_personales_db.to_sql('comisiones_vendedores_personales', conn, if_exists='append', index=False)

    conn.commit()
    conn.close()

    return resultados, detalles_semanales, resultados_personales

def calcular_comisiones_unificadas_ori(db_path: str, year: int, month: int):
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

    # Diccionarios de presupuestos
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

    # === Paso 1: Agrupar por (vendedor, ubicacion) → esto es clave
    for (vendedor, ubicacion), grupo in ventas.groupby(['vendedor', 'ubicacion']):
        grupo = grupo.copy()
        grupo['cantidad'] = pd.to_numeric(grupo['cantidad'], errors='coerce')
        grupo['precio_publico'] = pd.to_numeric(grupo['precio_publico'], errors='coerce')
        grupo = grupo.dropna(subset=['cantidad', 'precio_publico'])
        grupo['venta_total'] = grupo['cantidad'] * grupo['precio_publico']

        venta_total_vendedor_en_ubicacion = grupo['venta_total'].sum()
        if venta_total_vendedor_en_ubicacion <= 0:
            continue

        # Presupuesto de la ubicación
        presupuesto_ubicacion_valor = presupuestos_ubicacion[ubicacion]
        porc_cumpl_ubicacion = (venta_total_vendedor_en_ubicacion / presupuesto_ubicacion_valor) * 100
        print(ubicacion, venta_total_vendedor_en_ubicacion, porc_cumpl_ubicacion)

        # === Determinar esquema ===
        if vendedor in VENDEDORES_ESQUEMA1_PERSONAL or vendedor in presupuestos_vendedor:
            # Esquema personal: usar su presupuesto global, pero comisiones por ubicación
            if vendedor not in presupuestos_vendedor:
                print(f"⚠️ {vendedor} en lista personal pero sin presupuesto — usando por ubicación")
                esquema_personal = False
            else:
                esquema_personal = True
                presupuesto_vendedor_valor = presupuestos_vendedor[vendedor]
                porc_cumpl_personal = (venta_total_vendedor_en_ubicacion / presupuesto_vendedor_valor) * 100
                porcentajes = calcular_porcentajes_esquema_personal(porc_cumpl_personal)
        else:
            esquema_personal = False
            # Usar esquema por ubicación (rango 75-110%)
            if 75 <= porc_cumpl_ubicacion < 80:
                porc_com_mensual = 0.01
            elif 80 <= porc_cumpl_ubicacion < 90:
                porc_com_mensual = 0.0125
            elif 90 <= porc_cumpl_ubicacion < 110:
                porc_com_mensual = 0.02
            elif porc_cumpl_ubicacion >= 110:
                porc_com_mensual = 0.025
            else:
                porc_com_mensual = 0

        # === Calcular comisiones adicionales (siempre por ventas del vendedor en esa ubicación)
        juguetes = grupo[
            (grupo['familia_comercial'] == 'JUGUETE') &
            (~grupo['marca'].astype(str).str.startswith('CXO', na=False)) &
            (grupo['precio_publico'] > 1500)
        ]
        comision_juguetes = juguetes['venta_total'].sum() * (porcentajes['comision_juguetes'] if esquema_personal else 0.01)

        cxo_ventas = grupo[grupo['marca'].astype(str).str.startswith('CXO', na=False)]
        comision_cxo = cxo_ventas['venta_total'].sum() * (porcentajes['comision_cxo'] if esquema_personal else 0.06)

        dusa = grupo[
            (grupo['marca'] == 'DUSA') &
            (grupo['id_articulo'] != '5356')
        ]
        comision_dusa = dusa['venta_total'].sum() * (porcentajes['comision_dusa'] if esquema_personal else 0.02)

        shumatsu = grupo[grupo['id_articulo'] == '5356']
        comision_shumatsu = shumatsu['venta_total'].sum() * (porcentajes['comision_shumatsu'] if esquema_personal else 0.06)

        # === Comisión mensual ===
        if esquema_personal:
            comision_mensual = venta_total_vendedor_en_ubicacion * porcentajes['comision_mensual']
        else:
            comision_mensual = venta_total_vendedor_en_ubicacion * porc_com_mensual

        # === Comisión semanal (por ubicación, pero sobre ventas del vendedor en esa ubicación)
        comision_semanal = 0.0
        presupuesto_diario = presupuesto_ubicacion_valor / 30.0

        for i, semana in enumerate(semanas, start=1):
            dias_semana = len(semana)
            presupuesto_semana = presupuesto_diario * dias_semana

            fi, ff = semana[0], semana[-1]
            ventas_semana = grupo[
                (grupo['fecha'].dt.date >= fi) & (grupo['fecha'].dt.date <= ff)
            ]
            venta_semana = ventas_semana['venta_total'].sum()

            if venta_semana >= presupuesto_semana:
                comision_semana = venta_semana * 0.01
            else:
                comision_semana = 0.0

            comision_semanal += comision_semana

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
                'cumplio_semana': venta_semana >= presupuesto_semana
            })

        # ✅ Guardar resultado: venta_total_ubicacion = ventas del vendedor en esa ubicación
        resultados.append({
            'vendedor': vendedor,
            'ubicacion': ubicacion,
            'presupuesto_ubicacion': presupuesto_ubicacion_valor,
            'venta_total_ubicacion': venta_total_vendedor_en_ubicacion,  # ✅ Correcto
            'porcentaje_cumplimiento_ubicacion': porc_cumpl_ubicacion,
            'venta_total_vendedor': venta_total_vendedor_en_ubicacion,
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

        # Si es esquema personal, también guardamos en personales (para resumen)
        if esquema_personal:
            resultados_personales.append({
                'vendedor': vendedor,
                'ubicacion': ubicacion,
                'presupuesto_vendedor': presupuesto_vendedor_valor,
                'venta_total_vendedor': venta_total_vendedor_en_ubicacion,
                'venta_total_vendedor_global': venta_total_vendedor_en_ubicacion,  # En este caso, es igual
                'porcentaje_cumplimiento_personal': porc_cumpl_personal,
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


def exportar_a_excel(resultados, detalles_semanales, resultados_personales, year, month, df_ventas_origen):
    """
    Exporta los resultados a un archivo Excel con múltiples hojas para auditoría.
    Incluye la nueva hoja 'Detalle de Transacciones' para transparencia con el área comercial.
    """
    archivo_salida = f"comisiones_unificadas_{month}_{year}.xlsx"

    # Convertir listas a DataFrames
    df_resultados = pd.DataFrame(resultados)
    df_semanal = pd.DataFrame(detalles_semanales)
    df_personales = pd.DataFrame(resultados_personales)

    # Preparar datos de validación
    total_ventas_mes = df_ventas_origen['venta_total'].sum() if not df_ventas_origen.empty else 0
    df_validacion_ubic = df_ventas_origen.groupby('ubicacion')['venta_total'].sum().reset_index()
    df_validacion_ubic.columns = ['ubicacion', 'Total Ventas (Base de Datos)']

    # Crear el escritor de Excel con XlsxWriter
    with pd.ExcelWriter(archivo_salida, engine='xlsxwriter') as writer:

        # 1. Hoja: Detalle de Transacciones (LA SOLICITADA POR COMERCIAL)
        if not df_ventas_origen.empty:
            # Ordenamos cronológicamente y por ubicación para facilitar revisión
            df_detalle = df_ventas_origen.sort_values(['fecha', 'ubicacion', 'transaccion'])
            df_detalle.to_excel(writer, sheet_name='Detalle de Transacciones', index=False)

            # Formateo de la hoja de detalle
            worksheet_det = writer.sheets['Detalle de Transacciones']
            worksheet_det.freeze_panes(1, 0)  # Congelar encabezado (Corregido)

            # Ajustar anchos de columna automáticamente
            for i, col in enumerate(df_detalle.columns):
                column_len = max(df_detalle[col].astype(str).str.len().max(), len(col)) + 2
                worksheet_det.set_column(i, i, min(column_len, 50))  # Límite de 50 para que no sea excesivo

        # 2. Hoja: Comisiones por Ubicación (Original)
        if not df_resultados.empty:
            df_resultados.to_excel(writer, sheet_name='Comisiones por Ubicación', index=False)
            worksheet_res = writer.sheets['Comisiones por Ubicación']
            worksheet_res.freeze_panes(1, 0)

        # 3. Hoja: Bonos Semanales Tienda (Original)
        if not df_semanal.empty:
            df_semanal.to_excel(writer, sheet_name='Bonos Semanales Tienda', index=False)
            worksheet_sem = writer.sheets['Bonos Semanales Tienda']
            worksheet_sem.freeze_panes(1, 0)

        # 4. Hoja: Esquema Personal (Original)
        if not df_personales.empty:
            df_personales.to_excel(writer, sheet_name='Esquema Personal', index=False)
            worksheet_pers = writer.sheets['Esquema Personal']
            worksheet_pers.freeze_panes(1, 0)

        # 5. Hoja: Resumen por Vendedor Total (Original mejorado)
        if not df_resultados.empty:
            df_resumen_total = df_resultados.groupby('vendedor').agg({
                'venta_total_vendedor': 'sum',
                'comision_mensual': 'sum',
                'comision_juguetes': 'sum',
                'comision_cxo': 'sum',
                'comision_dusa': 'sum',
                'comision_shumatsu': 'sum',
                'comision_semanal': 'sum',
                'total_comisiones': 'sum'
            }).reset_index()
            df_resumen_total.to_excel(writer, sheet_name='Resumen por Vendedor Total', index=False)

        # 6. Hoja: Resumen por Ubicación (Original)
        if not df_resultados.empty:
            resumen_ubic = df_resultados.groupby('ubicacion').agg({
                'venta_total_ubicacion': 'sum',
                'porcentaje_cumplimiento_ubicacion': 'mean',
                'total_comisiones': 'sum'
            }).reset_index()
            resumen_ubic.columns = ['ubicacion', 'venta_total_ubicacion', 'porcentaje_cumplimiento_ubicacion',
                                    'total_comisiones']
            resumen_ubic.to_excel(writer, sheet_name='Resumen por Ubicación', index=False)

        # 7. Hoja: Ventas (Validación)
        df_validacion_ubic.to_excel(writer, sheet_name='Ventas (Validación)', index=False)

    print(f"✅ Reporte generado exitosamente: {archivo_salida}")
    print(f"📊 Total General de Ventas en Detalle: ${total_ventas_mes:,.2f}")

def exportar_a_excel_09abr2026(resultados, detalles, personales, archivo_salida: str, db_path: str, year: int, month: int, df_ventas_origen):
    df_resultados = pd.DataFrame(resultados)
    df_semanal = pd.DataFrame(detalles)
    df_personal = pd.DataFrame(personales)

    # === Hoja de Validación de Datos ===
    conn = sqlite3.connect(db_path)
    # query = """
    #     SELECT
    #         ubicacion,
    #         SUM(cantidad * precio_publico) AS venta_total
    #     FROM ventas
    #     WHERE strftime('%Y', fecha) = ? AND strftime('%m', fecha) = ?
    #     GROUP BY ubicacion;
    #     """
    # Pero como fecha es texto DD/MM/YYYY, usamos substr
    query = """
        SELECT 
            ubicacion,
            SUM(cantidad * precio_publico) AS venta_total
        FROM ventas
        WHERE substr(fecha, 7, 4) = ? AND substr(fecha, 4, 2) = ?
        GROUP BY ubicacion;
    """
    df_validacion_ubic = pd.read_sql_query(query, conn, params=(str(year), f"{month:02d}"))
    conn.close()

    total_ventas_mes = df_validacion_ubic['venta_total'].sum()
    num_transacciones = 0
    # Para ticket promedio global, necesitamos transacciones únicas
    conn = sqlite3.connect(db_path)
    query_trans = """
    SELECT COUNT(DISTINCT transaccion) AS n
    FROM ventas
    WHERE substr(fecha, 7, 4) = ? AND substr(fecha, 4, 2) = ?;
    """
    df_trans = pd.read_sql_query(query_trans, conn, params=(str(year), f"{month:02d}"))
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

        # Resumen por Ubicación (suma de venta_total_ubicacion por ubicación)
        if not df_resultados.empty:
            resumen_ubic = df_resultados.groupby('ubicacion').agg({
                'venta_total_ubicacion': 'sum',
                'porcentaje_cumplimiento_ubicacion': 'mean',
                'total_comisiones': 'sum'
            }).reset_index()
            resumen_ubic.columns = ['ubicacion', 'venta_total_ubicacion', 'porcentaje_cumplimiento_ubicacion', 'total_comisiones']
            resumen_ubic.to_excel(writer, sheet_name='Resumen por Ubicación', index=False)

        # ✅ Hoja de Validación
        df_validacion.to_excel(writer, sheet_name='Validación de Datos', index=False)
        df_validacion_ubic.to_excel(writer, sheet_name='Ventas (Validación)', index=False)

    print(f"✅ Reporte guardado en: {archivo_salida}")
    print(f"🔍 Total ventas mes (validación): ${total_ventas_mes:,.2f}")

# if __name__ == "__main__":
#     DB_PATH = "comisiones.db"
#     YEAR = 2026
#     MONTH = 3
#
#     print(f"🔍 Calculando comisiones UNIFICADAS para {MONTH}/{YEAR}...")
#
#     ventas_df = cargar_ventas_desde_db(DB_PATH, YEAR, MONTH)
#
#     resultados, detalles, personales = calcular_comisiones_unificadas(DB_PATH, YEAR, MONTH)
#
#     archivo_excel = f"comisiones_unificadas_{MONTH}_{YEAR}.xlsx"
#     exportar_a_excel(resultados, detalles, personales, archivo_excel, DB_PATH, YEAR, MONTH, ventas_df)

if __name__ == "__main__":
    DB_PATH = "comisiones.db"
    YEAR = 2026
    MONTH = 3 # El mes que estés calculando

    # 1. Cargar el dataframe de ventas original
    ventas_df = cargar_ventas_desde_db(DB_PATH, YEAR, MONTH)

    # 2. Calcular comisiones
    resultados, detalles, personales = calcular_comisiones_unificadas(DB_PATH, YEAR, MONTH)

    # 3. Exportar pasando el ventas_df para la hoja de auditoría
    exportar_a_excel(resultados, detalles, personales, YEAR, MONTH, ventas_df)
