import json
import os
import pandas as pd
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

# --- CONFIGURACIÓN DE CONEXIÓN ---
REALM = os.getenv('NS_REALM')
URL = f"https://{REALM.lower().replace('_', '-')}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"

client = OAuth1Session(
    client_key=os.getenv('NS_CLIENT_KEY'),
    client_secret=os.getenv('NS_CLIENT_SECRET'),
    resource_owner_key=os.getenv('NS_RESOURCE_OWNER_KEY'),
    resource_owner_secret=os.getenv('NS_RESOURCE_OWNER_SECRET'),
    signature_type='auth_header',
    signature_method='HMAC-SHA256',
    realm=REALM,
)


def calcular_puntos_unitarios(precio):
    if precio < 10:
        return 0
    elif precio <= 200:
        return 12
    elif precio <= 450:
        return 30
    elif precio <= 750:
        return 50
    elif precio <= 2000:
        return 70
    else:
        return 95


def procesar_logica_negocio(row):
    marca_original = str(row['marca']).strip().upper()
    familia = str(row['familia']).strip().upper()

    try:
        id_art = int(row['id_articulo'])
    except (ValueError, TypeError):
        id_art = 0

    ids_especiales = [5356, 1165, 1164]

    if id_art in ids_especiales:
        marca_final = "SHUMATSU"
        tasa = 0.10
    elif marca_original in ['CXO', 'CXO: B']:
        marca_final = marca_original
        tasa = 0.07
    elif marca_original == 'DUSA':
        marca_final = "DUSA"
        tasa = 0.03
    elif familia == 'JUGUETES':
        marca_final = marca_original
        tasa = 0.02
    else:
        marca_final = marca_original
        tasa = 0.01

    return pd.Series([marca_final, tasa])


def obtener_datos_paginados(fecha_inicio, fecha_fin):
    all_items = []
    offset = 0
    limit = 1000
    has_more = True

    print(f"\n🔍 Extrayendo datos de NetSuite...")

    while has_more:
        sql_query = (
            f"SELECT BUILTIN.DF(t.employee) as vendedor, BUILTIN.DF(tl.location) as ubicacion, "
            f"t.tranid as transaccion, t.trandate as fecha, BUILTIN.DF(tl.item) as articulo, "
            f"i.id as id_articulo, BUILTIN.DF(i.custitem_ctr_marca) as marca, "
            f"BUILTIN.DF(i.custitem_ctr_familia) as familia, ABS(tl.quantity) as cantidad, "
            f"(SELECT TOP 1 NVL(price, 0) FROM itemPrice ip WHERE ip.item = tl.item AND ip.priceLevelName = 'PRECIO PUBLICO') as precio_publico "
            f"FROM transaction t "
            f"INNER JOIN transactionline tl ON tl.transaction = t.id "
            f"INNER JOIN item i ON i.id = tl.item "
            f"WHERE t.type = 'CashSale' "
            f"AND t.trandate >= TO_DATE('{fecha_inicio}', 'YYYY-MM-DD') "
            f"AND t.trandate <= TO_DATE('{fecha_fin}', 'YYYY-MM-DD') "
            f"AND tl.accountinglinetype = 'INCOME'"
        )

        headers = {"Content-Type": "application/json", "Prefer": "transient"}
        params = {"limit": limit, "offset": offset}

        response = client.post(URL, headers=headers, params=params, data=json.dumps({"q": sql_query}))

        if response.status_code != 200:
            print(f"❌ Error en NetSuite: {response.text}")
            break

        data = response.json()
        items = data.get('items', [])
        all_items.extend(items)

        has_more = data.get('hasMore', False)
        offset += limit
        print(f"--- Registros acumulados: {len(all_items)} ---")

    return all_items


def ejecutar_proceso():
    print("=== Configuración del Reporte de Comisiones Dual ===")

    f_inicio = input("📅 Fecha inicio (YYYY-MM-DD): ")
    f_fin = input("📅 Fecha fin (YYYY-MM-DD): ")

    try:
        valor_punto_input = float(input("💰 Valor del punto para Variable (ej. 2.00): "))
    except ValueError:
        print("❌ Inválido. Se usará 2.00.")
        valor_punto_input = 2.00

    valor_punto_fijo = 0.92  # Valor constante solicitado

    items = obtener_datos_paginados(f_inicio, f_fin)

    if not items:
        print("No se encontraron registros.")
        return

    df = pd.DataFrame(items)
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)

    # 1. Cálculo de Puntos
    df['pts_unitarios'] = df['precio_publico'].apply(calcular_puntos_unitarios)
    df['pts_totales'] = df['pts_unitarios'] * df['cantidad']

    # 2. Lógica de Marcas y Tasas
    df[['marca_reporte', 'tasa_comision']] = df.apply(procesar_logica_negocio, axis=1)

    # 3. Cálculo Comisión VARIABLE (Basada en tasa y valor input)
    df['pts_comision'] = df['pts_totales'] * df['tasa_comision']
    df['pago_variable'] = df['pts_comision'] * valor_punto_input

    # 4. Cálculo Comisión FIJA (0.92 por cada punto total)
    df['pago_fijo_092'] = df['pts_totales'] * valor_punto_fijo

    # --- EXCEL ---
    nombre_archivo = f"Reporte_Comisiones_Dual_{f_inicio}.xlsx"
    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:

        # Resumen de Pago con ambas columnas
        resumen_pago = df.groupby(['vendedor', 'ubicacion']).agg({
            'pts_totales': 'sum',
            'pago_variable': 'sum',
            'pago_fijo_092': 'sum'
        }).reset_index().rename(columns={
            'pago_variable': f'Comisión Variable (${valor_punto_input}/pt)',
            'pago_fijo_092': 'Comisión Fija ($0.92/pt)'
        })
        resumen_pago.to_excel(writer, sheet_name='Resumen Pago', index=False)

        # Resumen por Marca
        resumen_marca = df.groupby(['vendedor', 'ubicacion', 'marca_reporte']).agg({
            'pts_totales': 'sum',
            'pago_variable': 'sum',
            'pago_fijo_092': 'sum'
        }).reset_index().rename(columns={
            'marca_reporte': 'MARCA',
            'pts_totales': 'PUNTOS TOTALES',
            'pago_variable': 'VARIABLE GENERADA',
            'pago_fijo_092': 'FIJA GENERADA (0.92)'
        })
        resumen_marca.to_excel(writer, sheet_name='Resumen por Marca', index=False)

        df.to_excel(writer, sheet_name='Detalle Técnico', index=False)

        # Formatos de Moneda
        workbook = writer.book
        fmt_money = workbook.add_format({'num_format': '$#,##0.00'})
        for sheet in ['Resumen Pago', 'Resumen por Marca']:
            ws = writer.sheets[sheet]
            ws.set_column('D:E', 22, fmt_money)

    print(f"\n✅ Proceso completado.")
    print(f"📊 Esquema 1 (Variable): ${valor_punto_input} s/puntos comisión")
    print(f"📊 Esquema 2 (Fijo): $0.92 s/puntos totales")
    print(f"📁 Archivo: {nombre_archivo}")


if __name__ == "__main__":
    ejecutar_proceso()