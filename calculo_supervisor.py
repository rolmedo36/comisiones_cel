# calculo_comisiones_nicolas.py

import pandas as pd
import sqlite3
from datetime import datetime


def cargar_todas_las_ventas(db_path: str, year: int, month: int) -> pd.DataFrame:
    """Carga TODAS las ventas del mes, sin filtrar por vendedor."""
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

    # Conversión robusta
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce')
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce')
    df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')

    # Eliminar filas inválidas
    df = df.dropna(subset=['fecha', 'cantidad', 'precio_publico', 'transaccion'])
    df = df[
        (df['fecha'].dt.year == year) &
        (df['fecha'].dt.month == month)
        ].copy()
    return df


def cargar_presupuestos_totales(db_path: str, year: int, month: int) -> float:
    conn = sqlite3.connect(db_path)

    # Presupuesto de ubicaciones
    query_ubic = "SELECT SUM(presupuesto) FROM presupuestos_ubicaciones WHERE mes = ? AND anio = ?;"
    total_ubic = pd.read_sql_query(query_ubic, conn, params=(month, year)).iloc[0, 0] or 0

    # Presupuesto de los 3 vendedores especiales
    query_vend = """
    SELECT SUM(presupuesto_vendedor) 
    FROM vendedores_esquema_personal 
    WHERE vendedor IN ('ALFONSO  M CARBALLAR', 'ANGEL DANILO RODRIGUEZ LOPEZ', 'GERMAN  GUZMAN AGUIRRE')
      AND mes = ? AND anio = ?;
    """
    total_vend = pd.read_sql_query(query_vend, conn, params=(month, year)).iloc[0, 0] or 0

    conn.close()
    return float(total_ubic + total_vend)


def calcular_porcentajes_nicolas(cumplimiento: float):
    """Devuelve dict con % para cada categoría según el esquema de supervisor"""
    if 60 <= cumplimiento < 75:
        return {
            'cuota': 0.003,
            'ticket': 0.0005,
            'unidades': 0.0005,
            'cxo': 0.01,
            'juguetes': 0.005,
            'dusa': 0.01,
            'pastilla': 0.01,
            'lenceria': 0.01
        }
    elif 70 <= cumplimiento < 80:
        return {
            'cuota': 0.003,
            'ticket': 0.0015,
            'unidades': 0.0015,
            'cxo': 0.01,
            'juguetes': 0.003,
            'dusa': 0.01,
            'pastilla': 0.01,
            'lenceria': 0.01
        }
    elif 80 <= cumplimiento < 91:
        return {
            'cuota': 0.004,
            'ticket': 0.0020,
            'unidades': 0.0020,
            'cxo': 0.015,
            'juguetes': 0.005,
            'dusa': 0.015,
            'pastilla': 0.015,
            'lenceria': 0.015
        }
    elif 91 <= cumplimiento <= 110:
        return {
            'cuota': 0.005,
            'ticket': 0.0035,
            'unidades': 0.0035,
            'cxo': 0.015,
            'juguetes': 0.005,
            'dusa': 0.015,
            'pastilla': 0.015,
            'lenceria': 0.015
        }
    elif cumplimiento > 110:
        return {
            'cuota': 0.006,
            'ticket': 0.0040,
            'unidades': 0.0040,
            'cxo': 0.02,
            'juguetes': 0.005,
            'dusa': 0.02,
            'pastilla': 0.02,
            'lenceria': 0.02
        }
    else:
        return {k: 0 for k in ['cuota', 'ticket', 'unidades', 'cxo', 'juguetes', 'dusa', 'pastilla', 'lenceria']}


def calcular_comisiones_nicolas(db_path: str, year: int, month: int):
    # Cargar TODAS las ventas del mes
    ventas = cargar_todas_las_ventas(db_path, year, month)
    if ventas.empty:
        print("⚠️ No hay ventas en este mes.")
        return None

    presupuesto_total = cargar_presupuestos_totales(db_path, year, month)
    if presupuesto_total <= 0:
        print("❌ Error: Presupuesto total es 0 o negativo.")
        return None

    # Métrica 1: Venta total
    ventas['venta_total'] = ventas['cantidad'] * ventas['precio_publico']
    venta_total = ventas['venta_total'].sum()
    cumplimiento = (venta_total / presupuesto_total) * 100

    # Métrica 2: Ticket promedio
    num_transacciones = ventas['transaccion'].nunique()
    ticket_promedio = venta_total / num_transacciones if num_transacciones > 0 else 0

    # Métrica 3: Unidades por ticket
    total_unidades = ventas['cantidad'].sum()
    unidades_por_ticket = total_unidades / num_transacciones if num_transacciones > 0 else 0

    # Comisiones adicionales sobre TODAS las ventas
    cxo = ventas[ventas['marca'].astype(str).str.startswith('CXO', na=False)]['venta_total'].sum()
    juguetes = ventas[
        (ventas['familia_comercial'] == 'JUGUETE') &
        (~ventas['marca'].astype(str).str.startswith('CXO', na=False)) &
        (ventas['precio_publico'] > 1500)
        ]['venta_total'].sum()
    dusa = ventas[
        (ventas['marca'] == 'DUSA') &
        (ventas['id_articulo'] != '5356')
        ]['venta_total'].sum()
    pastilla = ventas[ventas['id_articulo'] == '5356']['venta_total'].sum()
    lenceria = ventas[ventas['familia_comercial'] == 'LENCERIA']['venta_total'].sum()

    # Obtener porcentajes
    porcentajes = calcular_porcentajes_nicolas(cumplimiento)

    # Calcular comisiones
    comision_cuota = venta_total * porcentajes['cuota']
    comision_ticket = ticket_promedio * porcentajes['ticket'] * num_transacciones
    comision_unidades = total_unidades * porcentajes['unidades']
    comision_cxo = cxo * porcentajes['cxo']
    comision_juguetes = juguetes * porcentajes['juguetes']
    comision_dusa = dusa * porcentajes['dusa']
    comision_pastilla = pastilla * porcentajes['pastilla']
    comision_lenceria = lenceria * porcentajes['lenceria']

    total_comisiones = (
            comision_cuota + comision_ticket + comision_unidades +
            comision_cxo + comision_juguetes + comision_dusa +
            comision_pastilla + comision_lenceria
    )

    resultado = {
        'vendedor': 'NICOLAS H ACEVES',
        'presupuesto_total': presupuesto_total,
        'venta_total': venta_total,
        'cumplimiento': cumplimiento,
        'ticket_promedio': ticket_promedio,
        'unidades_por_ticket': unidades_por_ticket,
        'num_transacciones': num_transacciones,
        'total_unidades': total_unidades,
        'comision_cuota': comision_cuota,
        'comision_ticket': comision_ticket,
        'comision_unidades': comision_unidades,
        'comision_cxo': comision_cxo,
        'comision_juguetes': comision_juguetes,
        'comision_dusa': comision_dusa,
        'comision_pastilla': comision_pastilla,
        'comision_lenceria': comision_lenceria,
        'total_comisiones': total_comisiones
    }

    # Guardar en base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comisiones_nicolas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mes INTEGER NOT NULL,
        anio INTEGER NOT NULL,
        presupuesto_total REAL NOT NULL,
        venta_total REAL NOT NULL,
        cumplimiento REAL NOT NULL,
        ticket_promedio REAL NOT NULL,
        unidades_por_ticket REAL NOT NULL,
        num_transacciones INTEGER NOT NULL,
        total_unidades REAL NOT NULL,
        comision_cuota REAL NOT NULL,
        comision_ticket REAL NOT NULL,
        comision_unidades REAL NOT NULL,
        comision_cxo REAL NOT NULL,
        comision_juguetes REAL NOT NULL,
        comision_dusa REAL NOT NULL,
        comision_pastilla REAL NOT NULL,
        comision_lenceria REAL NOT NULL,
        total_comisiones REAL NOT NULL,
        fecha_calculo TEXT NOT NULL
    );
    """)

    # Asegurar compatibilidad si la tabla ya existía sin 'num_transacciones'
    try:
        cursor.execute("ALTER TABLE comisiones_nicolas ADD COLUMN num_transacciones INTEGER DEFAULT 0;")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise e

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO comisiones_nicolas (
        mes, anio, presupuesto_total, venta_total, cumplimiento,
        ticket_promedio, unidades_por_ticket, num_transacciones, total_unidades,
        comision_cuota, comision_ticket, comision_unidades,
        comision_cxo, comision_juguetes, comision_dusa,
        comision_pastilla, comision_lenceria, total_comisiones, fecha_calculo
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        month, year, presupuesto_total, venta_total, cumplimiento,
        ticket_promedio, unidades_por_ticket, num_transacciones, total_unidades,
        comision_cuota, comision_ticket, comision_unidades,
        comision_cxo, comision_juguetes, comision_dusa,
        comision_pastilla, comision_lenceria, total_comisiones, ahora
    ))
    conn.commit()
    conn.close()

    return resultado


def exportar_nicolas_a_excel(resultado: dict, archivo_salida: str):
    df = pd.DataFrame([resultado])
    with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Comisiones NICOLAS', index=False)
    print(f"📄 Reporte de NICOLAS guardado en: {archivo_salida}")


if __name__ == "__main__":
    DB_PATH = "comisiones.db"
    YEAR = 2025
    MONTH = 12

    print("🔍 Calculando comisiones de NICOLAS H ACEVES (supervisor)...")
    resultado = calcular_comisiones_nicolas(DB_PATH, YEAR, MONTH)

    if resultado:
        archivo_excel = f"comisiones_nicolas_{MONTH}_{YEAR}.xlsx"
        exportar_nicolas_a_excel(resultado, archivo_excel)