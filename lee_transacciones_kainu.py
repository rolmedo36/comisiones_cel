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


def send_email_with_attachment(re):
    sender_email = "soporte@celesterra.com.mx"  # Replace with your email
    sender_password = "mntxxfgkfqjmgpfz"  # Replace with your email password (or app password if using Gmail)
    # receiver_email = "rodrigo@celesterra.com.mx"  # Replace with the recipient's email
    receiver_email = re
    subject = "Ventas Reporte"
    body = "Adjunto reporte de ventas.\n\nSaludos."

    # Path to the Excel file
    file_path = "ventas_reporte_with_formula.xlsx"

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    # Add body as MIMEText to handle the email body properly
    msg.attach(MIMEText(body, 'plain'))

    # Attach the Excel file
    part = MIMEBase('application', 'octet-stream')
    try:
        with open(file_path, "rb") as attachment:
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
        msg.attach(part)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return
    # Connect to the Microsoft 365 SMTP server (use correct server and port)
    try:
        # Microsoft 365 SMTP server address: smtp.office365.com, port 587 (TLS)
        server = smtplib.SMTP('smtp.office365.com', 587)
        server.starttls()  # Upgrade to secure connection
        server.login(sender_email, sender_password)

        # Send the email
        text = msg.as_string()  # Convert the message to string
        server.sendmail(sender_email, receiver_email, text)
        print(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        print(f"Error sending email: {e}")
    finally:
        server.quit()

if __name__ == '__main__':
    # mes_ini = datetime.today().replace(day=1).strftime("%d/%m/%Y")
    mes_ini = '01/12/2025'
    archivo = 'comisiones_kainu.csv'
    results = []
    conn = sqlite3.connect('comisiones_kainu.db')

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
            AND t.type = 'CashSale'
            AND t.trandate >= '{mes_ini}'
            -- AND t.trandate = '31/10/2025'
            AND tl.transaction = t.id
            AND tl.taxLine = 'F'
            AND tl.mainLine = 'F'
            AND tl.netAmount <> 0
            AND tl.quantity <> 0
            AND tl.location in (486, 487) -- SOLO MASCOTA 486 y 487
            AND i.id = tl.item
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
    df.to_sql('ventas_kainu', conn, if_exists='replace', index=False)

    # genera_reporte()

    # envia correo
    # for r in ['soporte@celesterra.com.mx']:
    # for r in ['lider@erectus.com.mx', 'zenter@erectus.com.mx', 'asistente.direccion@celesterra.com.mx']:
    #    send_email_with_attachment(r)

