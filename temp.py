import sqlite3

def reparar_tabla_comisiones_nicolas(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Renombrar tabla antigua
    cursor.execute("ALTER TABLE comisiones_nicolas RENAME TO comisiones_nicolas_old;")

    # Crear nueva tabla con la estructura correcta
    cursor.execute("""
    CREATE TABLE comisiones_nicolas (
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

    # Copiar datos (si hay) — opcional, si quieres conservar historial
    # cursor.execute("""
    # INSERT INTO comisiones_nicolas
    # SELECT id, mes, anio, presupuesto_total, venta_total, cumplimiento,
    #        ticket_promedio, unidades_por_ticket,
    #        COALESCE(transacciones, 0) AS num_transacciones,  -- mapear transacciones → num_transacciones
    #        total_unidades,
    #        comision_cuota, comision_ticket, comision_unidades,
    #        comision_cxo, comision_juguetes, comision_dusa,
    #        comision_pastilla, comision_lenceria, total_comisiones, fecha_calculo
    # FROM comisiones_nicolas_old;
    # """)

    # Eliminar tabla antigua
    cursor.execute("DROP TABLE comisiones_nicolas_old;")

    conn.commit()
    conn.close()
    print("✅ Tabla 'comisiones_nicolas' reparada.")

# Ejecutar una vez
if __name__ == "__main__":
    reparar_tabla_comisiones_nicolas("comisiones.db")