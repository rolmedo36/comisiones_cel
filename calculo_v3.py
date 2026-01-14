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

def crear_tabla_comisiones_vendedores_personales_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Crear tabla si no existe
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
    # Asegurar que la columna especial exista
    try:
        cursor.execute("ALTER TABLE comisiones_vendedores_personales ADD COLUMN esquema_nicolas_aplicado BOOLEAN DEFAULT 0;")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise e
    conn.commit()
    conn.close()

def crear_tabla_vendedores_esquema_nicolas_si_no_existe(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendedores_esquema_nicolas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendedor TEXT NOT NULL,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto_nicolas REAL NOT NULL,
        UNIQUE(vendedor, mes, anio)
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

    # 🔸 Conversión robusta temprana
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

def cargar_presupuesto_nicolas(db_path: str, year: int, month: int) -> float:
    conn = sqlite3.connect(db_path)
    query = """
    SELECT presupuesto_nicolas
    FROM vendedores_esquema_nicolas
    WHERE vendedor = 'NICOLAS H ACEVES' AND mes = ? AND anio = ?;
    """
    df = pd.read_sql_query(query, conn, params=(month, year))
    conn.close()

    if df.empty:
        return 0.0
    else:
        pres = pd.to_numeric(df['presupuesto_nicolas'].iloc[0], errors='coerce')
        return float(pres) if pd.notna(pres) and pres > 0 else 0.0

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

def calcular_porcentajes_nicolas(porc_cumplimiento: float):
    if porc_cumplimiento < 69:
        return {
            'comision_cuota': 0.0,
            'comision_cxo': 0.0,
            'comision_juguetes': 0.0,
            'comision_dusa': 0.0,
            'comision_shumatsu': 0.0
        }
    elif 70 <= porc_cumplimiento <= 75:
        return {
            'comision_cuota': 0.005,
            'comision_cxo': 0.03,
            'comision_juguetes': 0.005,
            'comision_dusa': 0.01,
            'comision_shumatsu': 0.03
        }
    elif 76 <= porc_cumplimiento <= 80:
        return {
            'comision_cuota': 0.01,
            'comision_cxo': 0.045,
            'comision_juguetes': 0.0075,
            'comision_dusa': 0.015,
            'comision_shumatsu': 0.045
        }
    elif 81 <= porc_cumplimiento <= 100:
        return {
            'comision_cuota': 0.02,
            'comision_cxo': 0.06,
            'comision_juguetes': 0.01,
            'comision_dusa': 0.02,
            'comision_shumatsu': 0.06
        }
    else:  # >= 110
        return {
            'comision_cuota': 0.025,
            'comision_cxo': 0.06,
            'comision_juguetes': 0.01,
            'comision_dusa': 0.02,
            'comision_shumatsu': 0.06
        }

def calcular_comisiones_por_vendedor(db_path: str, year: int, month: int):
    # Crear tablas si no existen
    crear_tabla_presupuestos_ubicaciones_si_no_existe(db_path)
    crear_tabla_comisiones_por_vendedor_si_no_existe(db_path)
    crear_tabla_comisiones_semanales_si_no_existe(db_path)
    crear_tabla_vendedores_esquema_personal_si_no_existe(db_path)
    crear_tabla_comisiones_vendedores_personales_si_no_existe(db_path)
    crear_tabla_vendedores_esquema_nicolas_si_no_existe(db_path)

    ventas = cargar_ventas_desde_db(db_path, year, month)
    presupuestos = cargar_presupuestos_por_ubicacion(db_path, year, month)
    vendedores_personal = cargar_vendedores_esquema_personal(db_path, year, month)

    if ventas.empty:
        print("⚠️ No hay ventas válidas para este mes.")
        return [], [], []

    # Diccionarios de presupuestos
    presupuestos_ubicacion = {}
    for _, row in presupuestos.iterrows():
        ub = row['ubicacion']
        pres = row['presupuesto']
        if pd.notna(pres) and pres > 0:
            presupuestos_ubicacion[ub] = float(pres)

    presupuestos_vendedor = {}
    for _, row in vendedores_personal.iterrows():
        vend = row['vendedor']
        pres = row['presupuesto_vendedor']
        if pd.notna(pres) and pres > 0:
            presupuestos_vendedor[vend] = float(pres)

    # Verificar presupuestos
    ubicaciones_con_ventas = set(ventas['ubicacion'].unique())
    ubicaciones_con_presupuesto = set(presupuestos_ubicacion.keys())
    vendedores_con_presupuesto = set(presupuestos_vendedor.keys())

    faltantes_ubicacion = ubicaciones_con_ventas - ubicaciones_con_presupuesto
    faltantes_vendedor = vendedores_con_presupuesto - set(ventas['vendedor'].unique())

    if faltantes_ubicacion:
        print(f"❌ ERROR: Faltan presupuestos de ubicación: {faltantes_ubicacion}")
        return [], [], []

    if faltantes_vendedor:
        print(f"⚠️ Advertencia: Vendedores con presupuesto personal pero sin ventas: {faltantes_vendedor}")

    resultados = []
    detalles_semanales = []
    resultados_personales = []
    semanas = get_weeks_for_month(year, month)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === Procesar todos los vendedores globalmente ===
    for vendedor, grupo_vendedor in ventas.groupby('vendedor'):
        # 🔸 Conversión defensiva
        grupo_vendedor = grupo_vendedor.copy()
        grupo_vendedor['cantidad'] = pd.to_numeric(grupo_vendedor['cantidad'], errors='coerce')
        grupo_vendedor['precio_publico'] = pd.to_numeric(grupo_vendedor['precio_publico'], errors='coerce')
        grupo_vendedor = grupo_vendedor.dropna(subset=['cantidad', 'precio_publico'])
        grupo_vendedor['venta_total'] = grupo_vendedor['cantidad'] * grupo_vendedor['precio_publico']
        venta_total_vendedor_global = grupo_vendedor['venta_total'].sum()

        # === Determinar esquema ===
        if vendedor in presupuestos_vendedor:
            # === ESQUEMA PERSONAL ===
            presupuesto_vendedor_valor = presupuestos_vendedor[vendedor]
            porc_cumplimiento_personal = (venta_total_vendedor_global / presupuesto_vendedor_valor) * 100
            porcentajes = calcular_porcentajes_esquema_personal(porc_cumplimiento_personal)

            comision_mensual = venta_total_vendedor_global * porcentajes['comision_mensual']

            cxo_ventas = grupo_vendedor[grupo_vendedor['marca'].astype(str).str.startswith('CXO', na=False)]['venta_total'].sum()
            comision_cxo = cxo_ventas * porcentajes['comision_cxo']

            juguetes = grupo_vendedor[
                (grupo_vendedor['familia_comercial'] == 'JUGUETE') &
                (~grupo_vendedor['marca'].astype(str).str.startswith('CXO', na=False)) &
                (grupo_vendedor['precio_publico'] > 1500)
            ]
            comision_juguetes = juguetes['venta_total'].sum() * porcentajes['comision_juguetes']

            dusa = grupo_vendedor[
                (grupo_vendedor['marca'] == 'DUSA') &
                (grupo_vendedor['id_articulo'] != '5356')
            ]
            comision_dusa = dusa['venta_total'].sum() * porcentajes['comision_dusa']

            shumatsu = grupo_vendedor[grupo_vendedor['id_articulo'] == '5356']
            comision_shumatsu = shumatsu['venta_total'].sum() * porcentajes['comision_shumatsu']

            # === Cálculo semanal: por cada ubicación donde vendió ===
            comision_semanal_total = 0.0
            for ubicacion_local, grupo_ubicacion_local in grupo_vendedor.groupby('ubicacion'):
                presupuesto_ubicacion_valor = presupuestos_ubicacion[ubicacion_local]
                presupuesto_diario = presupuesto_ubicacion_valor / 30.0

                for i, semana in enumerate(semanas, start=1):
                    dias_semana = len(semana)
                    presupuesto_semana = presupuesto_diario * dias_semana

                    fi, ff = semana[0], semana[-1]
                    ventas_semana = grupo_ubicacion_local[
                        (grupo_ubicacion_local['fecha'].dt.date >= fi) &
                        (grupo_ubicacion_local['fecha'].dt.date <= ff)
                    ]
                    venta_semana = ventas_semana['venta_total'].sum()

                    if venta_semana >= presupuesto_semana:
                        comision_semana = venta_semana * 0.01
                    else:
                        comision_semana = 0.0

                    comision_semanal_total += comision_semana

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
                        'comision_semana': comision_semana,
                        'cumplio_semana': venta_semana >= presupuesto_semana
                    })

            # === Guardar en tabla personal ===
            resultados_personales.append({
                'vendedor': vendedor,
                'presupuesto_vendedor': presupuesto_vendedor_valor,
                'venta_total_vendedor': venta_total_vendedor_global,
                'porcentaje_cumplimiento_personal': porc_cumplimiento_personal,
                'comision_mensual': comision_mensual,
                'comision_juguetes': comision_juguetes,
                'comision_cxo': comision_cxo,
                'comision_dusa': comision_dusa,
                'comision_shumatsu': comision_shumatsu,
                'comision_semanal': comision_semanal_total,
                'total_comisiones': (
                    comision_mensual + comision_juguetes + comision_cxo +
                    comision_dusa + comision_shumatsu + comision_semanal_total
                ),
                'esquema_nicolas_aplicado': 0
            })

        else:
            # === ESQUEMA POR UBICACIÓN ===
            for ubicacion_local, grupo_ubicacion_local in grupo_vendedor.groupby('ubicacion'):
                # 🔸 Conversión defensiva
                grupo_ubicacion_local = grupo_ubicacion_local.copy()
                grupo_ubicacion_local['cantidad'] = pd.to_numeric(grupo_ubicacion_local['cantidad'], errors='coerce')
                grupo_ubicacion_local['precio_publico'] = pd.to_numeric(grupo_ubicacion_local['precio_publico'], errors='coerce')
                grupo_ubicacion_local = grupo_ubicacion_local.dropna(subset=['cantidad', 'precio_publico'])
                grupo_ubicacion_local['venta_total'] = grupo_ubicacion_local['cantidad'] * grupo_ubicacion_local['precio_publico']

                presupuesto_ubicacion_valor = presupuestos_ubicacion[ubicacion_local]
                venta_total_ubicacion = grupo_ubicacion_local['venta_total'].sum()
                porc_cumpl_ubicacion = (venta_total_ubicacion / presupuesto_ubicacion_valor) * 100

                if 75 <= porc_cumpl_ubicacion < 80:
                    porc_com_mensual_ubicacion = 0.01
                elif 80 <= porc_cumpl_ubicacion < 90:
                    porc_com_mensual_ubicacion = 0.0125
                elif 90 <= porc_cumpl_ubicacion < 110:
                    porc_com_mensual_ubicacion = 0.02
                elif porc_cumpl_ubicacion >= 110:
                    porc_com_mensual_ubicacion = 0.025
                else:
                    porc_com_mensual_ubicacion = 0

                venta_total_vendedor = grupo_ubicacion_local['venta_total'].sum()
                comision_mensual = venta_total_vendedor * porc_com_mensual_ubicacion

                cxo_ventas = grupo_ubicacion_local[grupo_ubicacion_local['marca'].astype(str).str.startswith('CXO', na=False)]['venta_total'].sum()
                comision_cxo = cxo_ventas * 0.06

                juguetes = grupo_ubicacion_local[
                    (grupo_ubicacion_local['familia_comercial'] == 'JUGUETE') &
                    (~grupo_ubicacion_local['marca'].astype(str).str.startswith('CXO', na=False)) &
                    (grupo_ubicacion_local['precio_publico'] > 1500)
                ]
                comision_juguetes = juguetes['venta_total'].sum() * 0.01

                dusa = grupo_ubicacion_local[
                    (grupo_ubicacion_local['marca'] == 'DUSA') &
                    (grupo_ubicacion_local['id_articulo'] != '5356')
                ]
                comision_dusa = dusa['venta_total'].sum() * 0.02

                shumatsu = grupo_ubicacion_local[grupo_ubicacion_local['id_articulo'] == '5356']
                comision_shumatsu = shumatsu['venta_total'].sum() * 0.06

                # === Cálculo semanal por ubicación ===
                presupuesto_diario = presupuesto_ubicacion_valor / 30.0
                comision_semanal_total = 0.0
                for i, semana in enumerate(semanas, start=1):
                    dias_semana = len(semana)
                    presupuesto_semana = presupuesto_diario * dias_semana

                    fi, ff = semana[0], semana[-1]
                    ventas_semana = grupo_ubicacion_local[
                        (grupo_ubicacion_local['fecha'].dt.date >= fi) &
                        (grupo_ubicacion_local['fecha'].dt.date <= ff)
                    ]
                    venta_semana = ventas_semana['venta_total'].sum()

                    if venta_semana >= presupuesto_semana:
                        comision_semana = venta_semana * 0.01
                    else:
                        comision_semana = 0.0

                    comision_semanal_total += comision_semana

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
                        'comision_semana': comision_semana,
                        'cumplio_semana': venta_semana >= presupuesto_semana
                    })

                resultados.append({
                    'vendedor': vendedor,
                    'ubicacion': ubicacion_local,
                    'presupuesto_ubicacion': presupuesto_ubicacion_valor,
                    'venta_total_ubicacion': venta_total_ubicacion,
                    'porcentaje_cumplimiento_ubicacion': porc_cumpl_ubicacion,
                    'venta_total_vendedor': venta_total_vendedor,
                    'comision_mensual': comision_mensual,
                    'comision_juguetes': comision_juguetes,
                    'comision_cxo': comision_cxo,
                    'comision_dusa': comision_dusa,
                    'comision_shumatsu': comision_shumatsu,
                    'comision_semanal': comision_semanal_total,
                    'total_comisiones': (
                        comision_mensual + comision_juguetes + comision_cxo +
                        comision_dusa + comision_shumatsu + comision_semanal_total
                    )
                })

    # === Procesar NICOLAS H ACEVES ===
    nicolas_nombre = "NICOLAS H ACEVES"
    if nicolas_nombre in ventas['vendedor'].unique():
        grupo_nicolas = ventas[ventas['vendedor'] == nicolas_nombre].copy()

        # 🔸 Conversión defensiva
        grupo_nicolas['cantidad'] = pd.to_numeric(grupo_nicolas['cantidad'], errors='coerce')
        grupo_nicolas['precio_publico'] = pd.to_numeric(grupo_nicolas['precio_publico'], errors='coerce')
        grupo_nicolas = grupo_nicolas.dropna(subset=['cantidad', 'precio_publico'])
        grupo_nicolas['venta_total'] = grupo_nicolas['cantidad'] * grupo_nicolas['precio_publico']
        venta_total_nicolas = grupo_nicolas['venta_total'].sum()

        presupuesto_nicolas = cargar_presupuesto_nicolas(db_path, year, month)
        if presupuesto_nicolas > 0:
            porc_cumplimiento_nicolas = (venta_total_nicolas / presupuesto_nicolas) * 100
            porcentajes_nicolas = calcular_porcentajes_nicolas(porc_cumplimiento_nicolas)

            # Calcular comisiones adicionales
            comision_cuota_adicional = venta_total_nicolas * porcentajes_nicolas['comision_cuota']

            cxo_ventas = grupo_nicolas[grupo_nicolas['marca'].astype(str).str.startswith('CXO', na=False)]['venta_total'].sum()
            comision_cxo_adicional = cxo_ventas * porcentajes_nicolas['comision_cxo']

            juguetes = grupo_nicolas[
                (grupo_nicolas['familia_comercial'] == 'JUGUETE') &
                (~grupo_nicolas['marca'].astype(str).str.startswith('CXO', na=False)) &
                (grupo_nicolas['precio_publico'] > 1500)
            ]
            comision_juguetes_adicional = juguetes['venta_total'].sum() * porcentajes_nicolas['comision_juguetes']

            dusa = grupo_nicolas[
                (grupo_nicolas['marca'] == 'DUSA') &
                (grupo_nicolas['id_articulo'] != 5356)
            ]
            comision_dusa_adicional = dusa['venta_total'].sum() * porcentajes_nicolas['comision_dusa']

            shumatsu = grupo_nicolas[grupo_nicolas['id_articulo'] == 5356]
            comision_shumatsu_adicional = shumatsu['venta_total'].sum() * porcentajes_nicolas['comision_shumatsu']

            # === Cálculo semanal (por ubicación, como siempre) ===
            comision_semanal_nicolas = 0.0
            for ubicacion_local, grupo_ubicacion_local in grupo_nicolas.groupby('ubicacion'):
                presupuesto_ubicacion_valor = presupuestos_ubicacion[ubicacion_local]
                presupuesto_diario = presupuesto_ubicacion_valor / 30.0

                for i, semana in enumerate(semanas, start=1):
                    dias_semana = len(semana)
                    presupuesto_semana = presupuesto_diario * dias_semana

                    fi, ff = semana[0], semana[-1]
                    ventas_semana = grupo_ubicacion_local[
                        (grupo_ubicacion_local['fecha'].dt.date >= fi) &
                        (grupo_ubicacion_local['fecha'].dt.date <= ff)
                    ]
                    venta_semana = ventas_semana['venta_total'].sum()

                    if venta_semana >= presupuesto_semana:
                        comision_semana = venta_semana * 0.01
                    else:
                        comision_semana = 0.0

                    comision_semanal_nicolas += comision_semana

                    dias_str = ', '.join([d.strftime('%d/%m/%Y') for d in semana])
                    detalles_semanales.append({
                        'vendedor': nicolas_nombre,
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
                        'comision_semana': comision_semana,
                        'cumplio_semana': venta_semana >= presupuesto_semana
                    })

            # Sumar comisiones adicionales a las ya calculadas
            nicolas_en_personales = False
            for rp in resultados_personales:
                if rp['vendedor'] == nicolas_nombre:
                    nicolas_en_personales = True
                    rp['comision_mensual'] += comision_cuota_adicional
                    rp['comision_cxo'] += comision_cxo_adicional
                    rp['comision_juguetes'] += comision_juguetes_adicional
                    rp['comision_dusa'] += comision_dusa_adicional
                    rp['comision_shumatsu'] += comision_shumatsu_adicional
                    rp['comision_semanal'] += comision_semanal_nicolas
                    rp['total_comisiones'] += (
                        comision_cuota_adicional +
                        comision_cxo_adicional +
                        comision_juguetes_adicional +
                        comision_dusa_adicional +
                        comision_shumatsu_adicional +
                        comision_semanal_nicolas
                    )
                    rp['esquema_nicolas_aplicado'] = 1
                    break

            if not nicolas_en_personales:
                resultados_personales.append({
                    'vendedor': nicolas_nombre,
                    'presupuesto_vendedor': presupuesto_nicolas,
                    'venta_total_vendedor': venta_total_nicolas,
                    'porcentaje_cumplimiento_personal': porc_cumplimiento_nicolas,
                    'comision_mensual': comision_cuota_adicional,
                    'comision_juguetes': comision_juguetes_adicional,
                    'comision_cxo': comision_cxo_adicional,
                    'comision_dusa': comision_dusa_adicional,
                    'comision_shumatsu': comision_shumatsu_adicional,
                    'comision_semanal': comision_semanal_nicolas,
                    'total_comisiones': (
                        comision_cuota_adicional +
                        comision_juguetes_adicional +
                        comision_cxo_adicional +
                        comision_dusa_adicional +
                        comision_shumatsu_adicional +
                        comision_semanal_nicolas
                    ),
                    'esquema_nicolas_aplicado': 1
                })
        else:
            print(f"⚠️ Advertencia: No se encontró presupuesto para NICOLAS H ACEVES.")

    # === Guardar en base de datos ===
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
            total_comisiones, esquema_nicolas_aplicado, fecha_calculo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res_p['vendedor'], month, year, res_p['presupuesto_vendedor'],
            res_p['venta_total_vendedor'], res_p['porcentaje_cumplimiento_personal'],
            res_p['comision_mensual'], res_p['comision_juguetes'], res_p['comision_cxo'],
            res_p['comision_dusa'], res_p['comision_shumatsu'], res_p['comision_semanal'],
            res_p['total_comisiones'], int(res_p['esquema_nicolas_aplicado']), ahora
        ))

    conn.commit()
    conn.close()

    return resultados, detalles_semanales, resultados_personales

def exportar_a_excel(resultados: list, detalles_semanales: list, resultados_personales: list, archivo_salida: str):
    df_resultados = pd.DataFrame(resultados)
    df_semanal = pd.DataFrame(detalles_semanales)
    df_personal = pd.DataFrame(resultados_personales)

    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df_resultados.to_excel(writer, sheet_name='Comisiones por Vendedor', index=False)
        df_semanal.to_excel(writer, sheet_name='Desglose Semanal', index=False)
        if not df_personal.empty:
            df_personal.to_excel(writer, sheet_name='Comisiones Personales', index=False)

        # === Resumen por Vendedor Total ===
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
                'total_comisiones': res['total_comisiones'],
                'esquema_nicolas_aplicado': 0
            })

        for res in resultados_personales:
            resumen_total.append({
                'vendedor': res['vendedor'],
                'ubicacion': 'Personal',
                'esquema': 'personal',
                'comision_ventas_fijas': (
                    res['comision_mensual'] +
                    res['comision_juguetes'] +
                    res['comision_cxo'] +
                    res['comision_dusa'] +
                    res['comision_shumatsu']
                ),
                'comision_semanal': res['comision_semanal'],
                'total_comisiones': res['total_comisiones'],
                'esquema_nicolas_aplicado': int(res.get('esquema_nicolas_aplicado', 0))
            })

        df_resumen_total = pd.DataFrame(resumen_total)
        if not df_resumen_total.empty:
            df_resumen_total = df_resumen_total.sort_values('vendedor').reset_index(drop=True)
            df_resumen_total.to_excel(writer, sheet_name='Resumen por Vendedor Total', index=False)

        if not df_resultados.empty:
            resumen_ubic = df_resultados.groupby('ubicacion').agg({
                'venta_total_ubicacion': 'first',
                'porcentaje_cumplimiento_ubicacion': 'first',
                'total_comisiones': 'sum'
            }).reset_index()
            resumen_ubic.to_excel(writer, sheet_name='Resumen por Ubicación', index=False)

    print(f"📄 Reporte detallado guardado en: {archivo_salida}")

# === EJECUCIÓN ===
if __name__ == "__main__":
    DB_PATH = "comisiones.db"
    YEAR = 2025
    MONTH = 12

    print(f"🔍 Calculando comisiones con esquema especial para NICOLAS H ACEVES...")
    resultados, detalles, personales = calcular_comisiones_por_vendedor(DB_PATH, YEAR, MONTH)

    archivo_excel = f"comisiones_{MONTH}_{YEAR}_detallado.xlsx"
    exportar_a_excel(resultados, detalles, personales, archivo_excel)