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
        marca_final, tasa = "SHUMATSU", 0.10
    elif marca_original in ['CXO', 'CXO: B']:
        marca_final, tasa = marca_original, 0.07
    elif marca_original == 'DUSA':
        marca_final, tasa = "DUSA", 0.03
    elif familia == 'JUGUETES':
        marca_final, tasa = marca_original, 0.02
    else:
        marca_final, tasa = marca_original, 0.01

    return pd.Series([marca_final, tasa])


def obtener_datos_paginados(fecha_inicio, fecha_fin):
    all_items = []
    offset, limit, has_more = 0, 1000, True
    print(f"\n🔍 Extrayendo datos filtrados de NetSuite...")

    while has_more:
        sql_query = (
            f"SELECT BUILTIN.DF(t.employee) as vendedor, BUILTIN.DF(tl.location) as ubicacion, "
            f"t.tranid as transaccion, t.trandate as fecha, BUILTIN.DF(tl.item) as articulo, "
            f"i.id as id_articulo, BUILTIN.DF(i.custitem_ctr_marca) as marca, "
            f"BUILTIN.DF(i.custitem_ctr_familia) as familia, ABS(tl.quantity) as cantidad, "
            f"(SELECT TOP 1 NVL(price, 0) FROM itemPrice ip WHERE ip.item = tl.item AND ip.priceLevelName = 'PRECIO PUBLICO') as precio_publico "
            f"FROM transaction t "
            f"INNER JOIN transactionline tl ON tl.transaction = t.id AND tl.location NOT IN (486, 487) "
            f"INNER JOIN item i ON i.id = tl.item "
            f"WHERE t.type = 'CashSale' AND t.trandate >= TO_DATE('{fecha_inicio}', 'YYYY-MM-DD') "
            f"AND t.trandate <= TO_DATE('{fecha_fin}', 'YYYY-MM-DD') AND tl.accountinglinetype = 'INCOME'"
        )
        response = client.post(URL, headers={"Content-Type": "application/json", "Prefer": "transient"},
                               params={"limit": limit, "offset": offset}, data=json.dumps({"q": sql_query}))
        if response.status_code != 200: break
        data = response.json()
        items = data.get('items', [])
        all_items.extend(items)
        has_more = data.get('hasMore', False)
        offset += limit
    return all_items


def ejecutar_proceso():
    f_inicio = input("📅 Fecha inicio (YYYY-MM-DD): ")
    f_fin = input("📅 Fecha fin (YYYY-MM-DD): ")
    try:
        val_v = float(input("💰 Valor punto Variable (ej. 2.00): "))
    except:
        val_v = 2.00
    val_f = 0.92

    items = obtener_datos_paginados(f_inicio, f_fin)
    if not items: return print("No hay datos.")

    df = pd.DataFrame(items)
    df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
    df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)
    df['pts_unitarios'] = df['precio_publico'].apply(calcular_puntos_unitarios)
    df['pts_totales'] = df['pts_unitarios'] * df['cantidad']
    df[['marca_reporte', 'tasa_comision']] = df.apply(procesar_logica_negocio, axis=1)

    # Cálculos independientes
    df['pago_variable'] = (df['pts_totales'] * df['tasa_comision']) * val_v
    df['pago_fijo_092'] = df['pts_totales'] * val_f

    nombre_archivo = f"Reporte_Comisiones_Final_{f_inicio}.xlsx"
    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
        workbook = writer.book

        # --- ESTILOS PROFESIONALES ---
        header_fmt = workbook.add_format(
            {'bold': True, 'font_color': 'white', 'bg_color': '#203764', 'border': 1, 'align': 'center',
             'valign': 'vcenter'})
        money_fmt = workbook.add_format({'num_format': '$#,##0.00', 'border': 1, 'valign': 'vcenter'})
        num_fmt = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        pct_fmt = workbook.add_format({'num_format': '0.0%', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        border_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})

        # --- HOJA 1: RESUMEN VARIABLE (TASAS) ---
        res1 = df.groupby(['vendedor', 'ubicacion']).agg({'pts_totales': 'sum', 'pago_variable': 'sum'}).reset_index()
        res1.columns = ['VENDEDOR', 'UBICACION', 'PUNTOS TOTALES', f'COMISIÓN VARIABLE (${val_v})']
        res1.to_excel(writer, sheet_name='Escenario Variable', index=False)
        ws1 = writer.sheets['Escenario Variable']
        for col_num, value in enumerate(res1.columns.values): ws1.write(0, col_num, value, header_fmt)
        ws1.set_column('A:B', 30, border_fmt)
        ws1.set_column('C:C', 18, num_fmt)
        ws1.set_column('D:D', 25, money_fmt)

        # --- HOJA 2: RESUMEN FIJO (0.92) ---
        res2 = df.groupby(['vendedor', 'ubicacion']).agg({'pts_totales': 'sum', 'pago_fijo_092': 'sum'}).reset_index()
        res2.columns = ['VENDEDOR', 'UBICACION', 'PUNTOS TOTALES', 'COMISION FIJA ($0.92)']
        res2.to_excel(writer, sheet_name='Escenario Fijo 0.92', index=False)
        ws2 = writer.sheets['Escenario Fijo 0.92']
        for col_num, value in enumerate(res2.columns.values): ws2.write(0, col_num, value, header_fmt)
        ws2.set_column('A:B', 30, border_fmt)
        ws2.set_column('C:C', 18, num_fmt)
        ws2.set_column('D:D', 25, money_fmt)

        # --- HOJA 3: DETALLE COMPLETO ---
        df_detail = df.rename(
            columns={'marca_reporte': 'MARCA', 'tasa_comision': 'TASA %', 'pago_variable': 'MONTO VAR.',
                     'pago_fijo_092': 'MONTO FIJO'})
        df_detail.to_excel(writer, sheet_name='Detalle de Transacciones', index=False)
        ws3 = writer.sheets['Detalle de Transacciones']
        for col_num, value in enumerate(df_detail.columns.values): ws3.write(0, col_num, value, header_fmt)
        ws3.set_column('A:A', 25, border_fmt);
        ws3.set_column('B:E', 18, border_fmt);
        ws3.set_column('F:H', 15, border_fmt)
        ws3.set_column('I:J', 12, num_fmt);
        ws3.set_column('K:K', 15, money_fmt);
        ws3.set_column('L:L', 15, border_fmt);
        ws3.set_column('M:M', 10, pct_fmt);
        ws3.set_column('N:O', 15, money_fmt)

    print(f"\n✅ Reporte finalizado con dos escenarios independientes.")
    print(f"📁 Archivo: {nombre_archivo}")


if __name__ == "__main__": ejecutar_proceso()