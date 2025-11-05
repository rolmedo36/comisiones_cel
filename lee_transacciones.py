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

def envia_archivos(archivo):
    CLIENT_ID = '52a47c28-3837-4454-adf9-175f52a8430b'
    CLIENT_SECRET = 'OTw8Q~XhdIkx4mc_hvDO.Ks~NFqjubAdB1h7Zc4x'
    TENANT_ID = 'c6092570-06fd-4081-a2eb-63bb3b9fb806'
    USER_ID = '95a06940-50f5-43fd-9c8b-b3d977a904df'  # You can get this from the Graph API
    FILE_PATH = archivo
    UPLOAD_PATH = '/TMP/' + archivo  # Path where you want to upload the file

    # Get an access token
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    scope = ["https://graph.microsoft.com/.default"]

    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET
    )

    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" in result:
        access_token = result["access_token"]
    else:
        raise Exception("Failed to obtain access token")

    # Upload the file to OneDrive
    upload_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/drive/root:{UPLOAD_PATH}:/content"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "text/csv"
    }

    with open(FILE_PATH, 'rb') as f:
        response = requests.put(upload_url, headers=headers, data=f)

    if response.status_code == 201:
        print("File uploaded successfully")
    else:
        print(f"Failed to upload file: {response.status_code}")
        print(response.text)


def genera_reporte():
    conn = sqlite3.connect('ventas.db')  # Replace 'mydatabase.db' with your desired database name
    cursor = conn.cursor()
    cursor.execute('''
        SELECT '0', transaccion, fecha, cliente, ubicacion, id_articulo, articulo, 
            coalesce(tipo_venta, 'Venta POS'), estatus, (cantidad), (importe_neto), (importe_efectivo), (importe_efectivo_clip),
            (importe_banorte), (importe_efectivo_ok), (importe_clip_ok), SUM(importe_neto) as importe_custinvc, importe_rappi, importe_banregio, tipo
         FROM ventas
         -- WHERE tipo_venta = 'Online' and fecha = '18/03/2025'
         GROUP BY transaccion
    ''')
    rows = cursor.fetchall()
    vfecha = ''
    vubicacion = ''
    vtotal = 0
    data = []

    for row in rows:
        vid_woo = row[0]
        vtransaccion = row[1]
        vfecha = row[2]
        vcliente = row[3]
        vubicacion = row[4]
        varticulo = row[6]
        vtipo_venta = row[7]
        vestatus = row[8]
        vcantidad = row[9]
        vimporte_neto = row[10]
        vimporte_efectivo = pd.to_numeric(row[11], errors='coerce')
        vimporte_efectivo_clip = pd.to_numeric(row[12], errors='coerce')
        vimporte_banorte = pd.to_numeric(row[13], errors='coerce')
        vimporte_efectivo_ok = pd.to_numeric(row[14], errors='coerce')
        vimporte_clip_ok = pd.to_numeric(row[15], errors='coerce')
        vimporte_custinv = pd.to_numeric(row[16], errors='coerce')
        vimporte_rappi = pd.to_numeric(row[17], errors='coerce')
        vimporte_banregio = pd.to_numeric(row[18], errors='coerce')
        vtipo = row[19]

        vimporte_efectivo = vimporte_efectivo if not pd.isna(vimporte_efectivo) else 0
        vimporte_efectivo_clip = vimporte_efectivo_clip if not pd.isna(vimporte_efectivo_clip) else 0
        vimporte_banorte = vimporte_banorte if not pd.isna(vimporte_banorte) else 0
        vimporte_efectivo_ok = vimporte_efectivo_ok if not pd.isna(vimporte_efectivo_ok) else 0

        # suma todos los importes de pagos: banorte, efectivo, clip
        vimporte_todo = vimporte_efectivo_ok + vimporte_banorte + vimporte_clip_ok + vimporte_banregio

        if vimporte_todo > 0: vtotal = vimporte_todo
        if vimporte_efectivo_clip > vimporte_efectivo: vtotal = vimporte_efectivo_clip
        if vimporte_efectivo > 0: vtotal = vimporte_efectivo

        # RAPPI se manda a parte
        # if vimporte_rappi > vtotal: vtotal = vimporte_rappi

        if vtipo == 'CustInvc':
        # if vtipo_venta.upper() == 'ONLINE' or vtipo_venta.upper() == 'ONLINE MASCOTAS' or vtipo_venta.upper() == 'EMPLEADOS' or vtipo_venta.upper() == 'MAYOREO' or vtipo_venta.upper() == 'WHATSAPP':
            vtotal = abs(vimporte_custinv) * 1.16 # le subimos el iva ya que se lo vuelve a quitar y este importe ya viene sin IVA
        # if vfecha != row[2]:

        data.append({
            'ubicacion': vubicacion ,
            'transaccion': vtransaccion,
            'fecha': vfecha,
            'venta': ( vtotal / 1.16 ), # Le quitamos el IVA
            'rappi': (vimporte_rappi / 1.16)  # Le quitamos el IVA
        })
        vtotal = 0


    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(data)

    # Create a Pivot Table
    pivot_table = pd.pivot_table(df, values=['venta','rappi'], index='ubicacion', columns='fecha', aggfunc={'venta': 'sum', 'rappi':'sum'}, fill_value=0)

    # Write the DataFrame with the Pivot Table to an Excel file
    with pd.ExcelWriter('ventas_reporte.xlsx', engine='openpyxl') as writer:
        pivot_table.to_excel(writer, sheet_name='Pivot Table')

    # Now we open the Excel file to add the formula
    workbook = openpyxl.load_workbook('ventas_reporte.xlsx')
    sheet = workbook['Pivot Table']

    # Add sum formulas for each column
    max_row = sheet.max_row
    max_col = sheet.max_column

    # Add SUM formula at the bottom of each column (starting from the second row, ignoring the header)
    # Add Encabezado
    projection_column_letter = openpyxl.utils.get_column_letter(max_col + 1)  # New column after row sum
    # Add header for the new column
    sheet[f"{projection_column_letter}2"] = "TOTAL"
    sheet[f"{projection_column_letter}2"].font = Font(bold=True)  # Make the header bold
    for col in range(2, max_col + 1):  # Start from column 2 (skip the 'ubicacion' column)
        column_letter = openpyxl.utils.get_column_letter(col)  # Convert column number to letter
        formula = f"=SUM({column_letter}2:{column_letter}{max_row})"  # Create the sum formula
        sheet[f"{column_letter}{max_row + 1}"] = formula  # Set the formula in the row just below the last data row
        cell = sheet[f"{column_letter}{max_row + 1}"]  # Get the cell where the formula will be added
        cell.value = formula  # Set the formula in the cell
        # Apply bold formatting to the formula cell
        cell.font = Font(bold=True)  # Make the font bold
        # Apply currency format to the cell
        cell.number_format = '"$"#,##0.00'  # Currency format (US Dollars in this case)

    # Add SUM formula for each row (last column)
    for row in range(4, max_row + 1):  # Start from row 2 to skip the header
        row_letter = openpyxl.utils.get_column_letter(max_col + 1)  # The new column where the sum will be placed
        formula = f"=SUM(B{row}:{openpyxl.utils.get_column_letter(max_col)}{row})"  # Sum all cells in the row
        sheet[f"{row_letter}{row}"] = formula  # Place the formula in the last column of each row
        cell = sheet[f"{row_letter}{row}"]  # Get the cell where the formula will be added
        cell.value = formula  # Set the formula in the cell
        # Apply bold formatting to the formula cell
        cell.font = Font(bold=True)  # Make the font bold
        # Apply currency format to the cell
        cell.number_format = '"$"#,##0.00'  # Currency format (US Dollars in this case)


    # Add 30-day projection column
    projection_column_letter = openpyxl.utils.get_column_letter(max_col + 2)  # New column after row sum
    # Add header for the new column
    sheet[f"{projection_column_letter}2"] = "PROYECCIÓN"
    sheet[f"{projection_column_letter}2"].font = Font(bold=True)  # Make the header bold

    for row in range(4, max_row + 2):  # Start from row 2 to skip the header
        formula = f"=AVERAGE(B{row}:{openpyxl.utils.get_column_letter(max_col)}{row})*2*30"  # Calculate 30-day projection
        sheet[f"{projection_column_letter}{row}"] = formula  # Set the formula in the new column
        cell = sheet[f"{projection_column_letter}{row}"]  # Get the cell where the formula will be added
        cell.value = formula  # Set the formula in the cell
        # Apply bold formatting to the formula cell
        cell.font = Font(bold=True)  # Make the font bold
        # Apply currency format to the cell
        cell.number_format = '"$"#,##0.00'  # Currency format (US Dollars in this case)

    # Add SUM formula for the sum of all column totals (at the bottom-right corner)
    column_letter_for_totals = openpyxl.utils.get_column_letter(max_col + 1)  # Column for the total sum
    formula = f"=SUM({column_letter_for_totals}2:{column_letter_for_totals}{max_row})"  # Create the sum formula
    sheet[
        f"{column_letter_for_totals}{max_row + 1}"] = formula  # Set the formula below the last row of row sums (one row above the original position)
    cell = sheet[f"{column_letter_for_totals}{max_row + 1}"]  # Get the cell where the formula will be added
    cell.value = formula  # Set the formula in the cell
    # Apply bold formatting to the formula cell
    cell.font = Font(bold=True)  # Make the font bold
    # Apply currency format to the cell
    cell.number_format = '"$"#,##0.00'  # Currency format (US Dollars in this case)

    # Apply currency formatting to all the cells with numerical data (for the pivot table)
    for row in sheet.iter_rows(min_row=2, max_row=max_row, min_col=2, max_col=max_col):
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = '"$"#,##0.00'  # Apply currency format

    # Adjust column widths
    for col in range(1, max_col + 3):  # Adjust columns 1 to max_col
        column_letter = openpyxl.utils.get_column_letter(col)  # Get column letter
        max_length = 0
        for cell in sheet[column_letter]:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 0)
        sheet.column_dimensions[column_letter].width = adjusted_width



    # Save the modified workbook
    workbook.save('ventas_reporte_with_formula.xlsx')

    # Close the database connection
    conn.close()

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
    mes_ini = '01/10/2025'
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

            tl.quantity as cantidad,
            -- tl.netAmount as importe_neto, -- este importe ya esta menos el costo
            ( SELECT TOP 1 NVL(price,'0') FROM itemPrice ip WHERE ip.item = tl.item AND ip.priceLevelName = 'PRECIO PUBLICO') as precio_publico,
            tl.custcol_ctr_promo_discount as promo_descuento,
            tl.custcol_ctr_promo_id as promo_id
            -- COALESCE(t.custbody24, '0')  as importe_efectivo,
            -- COALESCE(t.custbody25, 0) as importe_efectivo_clip,
            -- t.custbody_pos_tarjeta_banorte as importe_banorte,
            -- t.custbody_pos_efectivo as importe_efectivo_ok,
            -- t.custbody_drt_pos_metclip as importe_clip_ok,
            -- t.custbody_pos_tarjeta_rappi as importe_rappi,
            -- t.custbody_pos_tarjeta_credito as importe_banregio, -- franquicias
            -- t.type as tipo
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
        ORDER BY t.trandate

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

    # genera_reporte()

    # envia correo
    # for r in ['soporte@celesterra.com.mx']:
    # for r in ['lider@erectus.com.mx', 'zenter@erectus.com.mx', 'asistente.direccion@celesterra.com.mx']:
    #    send_email_with_attachment(r)

