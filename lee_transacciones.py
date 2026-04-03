import sqlite3
import requests
import json
import pandas as pd
import msal
from oauthlib import oauth1
from requests_oauthlib import OAuth1Session
from datetime import date
from datetime import timedelta, datetime
import csv
import openpyxl
from openpyxl.styles import Font  # Import the Font class for styling
from openpyxl.chart import BarChart, Reference  # Import the chart classes
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

ACCOUNT_ID = "6248386"
NETSUITE_DOMAIN = f"https://{ACCOUNT_ID}.suitetalk.api.netsuite.com"

import re
from urllib.parse import urlparse, parse_qs
def fetch_all_suiteql(client, query, page_size=1000):
    all_items = []
    offset = 0
    headers = {"Content-Type": "application/json", "Prefer": "transient"}

    while True:
        url = f"{NETSUITE_DOMAIN}/services/rest/query/v1/suiteql?limit={page_size}&offset={offset}"
        payload = {"q": query}

        response = client.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")

        result = response.json()
        items = result.get("items", [])
        all_items.extend(items)

        print(f"📄 Descargadas {len(all_items)} filas...")

        # Si ya no hay más registros, salir
        if len(items) < page_size:
            break

        offset += page_size

    return all_items

def agrupa_marca():
    table_marca = 'acumula_marca'
    vq = """
        SELECT 
            vendedor,
            ubicacion,
            marca,
            SUM(ABS(cantidad) * precio_publico) as total_venta -- Considerar descuentos de promociones?
        FROM 
            ventas
        GROUP BY 
            vendedor,
            ubicacion,
            marca
    """
    cursor = conn.execute(vq)
    rows = cursor.fetchall()

    # Obtener nombres de columna del cursor.description
    columnas = [desc[0] for desc in cursor.description]

    # Crear DataFrame con nombres de columna correctos
    df_marca = pd.DataFrame(rows, columns=columnas)

    # Guardar en SQLite (reemplaza la tabla si ya existe)
    df_marca.to_sql(table_marca, conn, if_exists='replace', index=False)


if __name__ == '__main__':
    # mes_ini = datetime.today().replace(day=1).strftime("%d/%m/%Y")
    mes_ini = '01/01/2026'
    archivo = 'comisiones.csv'
    results = []
    conn = sqlite3.connect('comisiones.db')

    qry = f"""
        SELECT
            t.tranid as transaccion,
            t.trandate as fecha,
            BUILTIN.DF(t.employee) as vendedor,
            BUILTIN.DF( t.entity ) as cliente,
            BUILTIN.DF( tl.location ) as ubicacion,
            REPLACE(tl.item,'"','') as id_articulo,
            BUILTIN.DF( tl.item ) as articulo,
            BUILTIN.DF( custbody_crt_tipodeventa_ ) as tipo_venta,
            
            BUILTIN.DF(i.custitem_ctr_marca) as marca,
            BUILTIN.DF(i.custitem23) as familia_comercial,

            ABS(tl.quantity) as cantidad,
            ( SELECT TOP 1 NVL(price,'0') FROM itemPrice ip WHERE ip.item = tl.item AND ip.priceLevelName = 'PRECIO PUBLICO') as precio_publico,
            tl.custcol_ctr_promo_discount as promo_descuento,
            tl.custcol_ctr_promo_id as promo_id

        FROM 
            transaction t,
            transactionline tl,
            item i
        WHERE 1=1
            -- AND (t.type = 'CashSale' OR t.type = 'CustInvc')
            AND t.type = 'CashSale'
            AND t.trandate >= '{mes_ini}'
            -- AND t.trandate = '31/10/2025'
            AND tl.transaction = t.id
            AND tl.taxLine = 'F'
            AND tl.mainLine = 'F'
            AND tl.netAmount <> 0
            AND tl.quantity <> 0
            AND tl.location not in (354, 365, 372, 419, 139, 377, 378, 257, 486, 487) -- no incluir EL ROBLE y PLAZA TLAQUEPAQUE ni MASCOTA 486 y 487
            -- AND tl.location = 282
            AND i.id = tl.item
            AND t.entity <> 1981 -- NO RAPPI
        ORDER BY t.trandate, t.id

    """
    client = OAuth1Session(
        client_key='260a11f980c7a6ef0b46ce5a9777165e31a2ede3c8ed7c39ef254ad3a0bf5cac',
        client_secret='81718e06b11c7ab902b20d46cda47c5ab5a8502619294f9a042b6e74ea1d88b9',
        resource_owner_key='445b99a0f9f38ef9284107aded99855b5cfe2631f944e0f724c78d6ab69c1df9',
        resource_owner_secret='6376e567eba2524babf2515b0308b15d9a5fc857d0870e3535ed7b3c30edf245',
        signature_type='auth_header',
        signature_method='HMAC-SHA256',
        # signature_method=oauth1.SIGNATURE_HMAC_SHA256,
        realm='6248386',
    )

    data = fetch_all_suiteql(client, qry)

    df = pd.DataFrame(data)
    df.to_csv(archivo, index=False, encoding="utf-8-sig")

    df = df.drop(columns='links')
    df.to_sql('ventas', conn, if_exists='replace', index=False)

    agrupa_marca()

