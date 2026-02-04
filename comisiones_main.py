import json
import os
import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry  # Requiere: pip install tkcalendar
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
import threading

# Cargar variables de entorno
load_dotenv()


class CommissionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NetSuite Commission Pro v3.1")
        self.root.geometry("550x520")

        # Configuración de OAuth1 (NetSuite)
        self.REALM = os.getenv('NS_REALM')
        self.URL = f"https://{self.REALM.lower().replace('_', '-')}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql"

        self.client = OAuth1Session(
            client_key=os.getenv('NS_CLIENT_KEY'),
            client_secret=os.getenv('NS_CLIENT_SECRET'),
            resource_owner_key=os.getenv('NS_RESOURCE_OWNER_KEY'),
            resource_owner_secret=os.getenv('NS_RESOURCE_OWNER_SECRET'),
            signature_type='auth_header',
            signature_method='HMAC-SHA256',
            realm=self.REALM,
        )

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="PROCESADOR DE COMISIONES", font=('Segoe UI', 16, 'bold')).pack(pady=(0, 20))

        # Rango de Fechas
        date_frame = ttk.LabelFrame(main_frame, text=" Período de Ventas ", padding=15)
        date_frame.pack(fill=tk.X, pady=10)

        ttk.Label(date_frame, text="Desde:").grid(row=0, column=0, padx=5)
        self.cal_start = DateEntry(date_frame, width=12, background='darkblue', foreground='white',
                                   date_pattern='yyyy-mm-dd')
        self.cal_start.grid(row=0, column=1, padx=15)

        ttk.Label(date_frame, text="Hasta:").grid(row=0, column=2, padx=5)
        self.cal_end = DateEntry(date_frame, width=12, background='darkblue', foreground='white',
                                 date_pattern='yyyy-mm-dd')
        self.cal_end.grid(row=0, column=3, padx=15)

        # Configuración de Pago
        config_frame = ttk.LabelFrame(main_frame, text=" Parámetros de Pago ", padding=15)
        config_frame.pack(fill=tk.X, pady=10)

        ttk.Label(config_frame, text="Valor Punto Variable ($):").grid(row=0, column=0, sticky=tk.W)
        self.ent_var_val = ttk.Entry(config_frame, width=10)
        self.ent_var_val.insert(0, "2.00")
        self.ent_var_val.grid(row=0, column=1, padx=10, sticky=tk.W)

        ttk.Label(config_frame, text="Valor Punto Fijo ($):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ent_fijo_val = ttk.Entry(config_frame, width=10)
        self.ent_fijo_val.insert(0, "0.92")
        self.ent_fijo_val.config(state='readonly')
        self.ent_fijo_val.grid(row=1, column=1, padx=10, sticky=tk.W)

        # Barra de progreso
        self.pb = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate', length=400)
        self.pb.pack(pady=20)

        self.lbl_status = ttk.Label(main_frame, text="Esperando instrucciones...", foreground="gray")
        self.lbl_status.pack()

        self.btn_run = ttk.Button(main_frame, text="GENERAR REPORTE EXCEL", command=self.run_process_thread)
        self.btn_run.pack(pady=20, ipadx=10, ipady=5)

    def run_process_thread(self):
        t = threading.Thread(target=self.process_logic)
        t.daemon = True
        t.start()

    def calcular_puntos(self, precio):
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

    def get_tasa_y_marca(self, row):
        marca_orig = str(row['marca']).strip().upper()
        familia = str(row['familia']).strip().upper()
        try:
            id_art = int(row['id_articulo'])
        except:
            id_art = 0

        ids_esp = [5356, 1165, 1164]

        if id_art in ids_esp: return "SHUMATSU", 0.10
        if marca_orig in ['CXO', 'CXO: B']: return marca_orig, 0.07
        if marca_orig == 'DUSA': return "DUSA", 0.03
        if familia == 'JUGUETES': return "JUGUETES", 0.02
        return marca_orig, 0.01

    def process_logic(self):
        try:
            self.btn_run.config(state='disabled')
            f_ini = self.cal_start.get()
            f_fin = self.cal_end.get()
            val_v = float(self.ent_var_val.get())
            val_f = 0.92

            self.lbl_status.config(text="Conectando a NetSuite...", foreground="blue")
            self.pb['value'] = 10

            all_items = []
            offset, limit, has_more = 0, 1000, True

            while has_more:
                sql = (
                    f"SELECT BUILTIN.DF(t.employee) as vendedor, BUILTIN.DF(tl.location) as ubicacion, "
                    f"t.tranid as transaccion, t.trandate as fecha, BUILTIN.DF(tl.item) as articulo, "
                    f"i.id as id_articulo, BUILTIN.DF(i.custitem_ctr_marca) as marca, "
                    f"BUILTIN.DF(i.custitem_ctr_familia) as familia, ABS(tl.quantity) as cantidad, "
                    f"(SELECT TOP 1 NVL(price, 0) FROM itemPrice ip WHERE ip.item = tl.item AND ip.priceLevelName = 'PRECIO PUBLICO') as precio_publico "
                    f"FROM transaction t "
                    f"INNER JOIN transactionline tl ON tl.transaction = t.id AND tl.location NOT IN (486, 487) "
                    f"INNER JOIN item i ON i.id = tl.item "
                    f"WHERE t.type = 'CashSale' AND t.trandate >= TO_DATE('{f_ini}', 'YYYY-MM-DD') "
                    f"AND t.trandate <= TO_DATE('{f_fin}', 'YYYY-MM-DD') AND tl.accountinglinetype = 'INCOME'"
                )

                resp = self.client.post(self.URL, headers={"Prefer": "transient"},
                                        params={"limit": limit, "offset": offset}, data=json.dumps({"q": sql}))
                if resp.status_code != 200:
                    raise Exception(f"Error NS: {resp.text}")

                data = resp.json()
                items = data.get('items', [])
                all_items.extend(items)
                has_more = data.get('hasMore', False)
                offset += limit
                self.lbl_status.config(text=f"Descargando datos: {len(all_items)} registros...")

            if not all_items:
                messagebox.showinfo("Resultado", "No se encontraron ventas.")
                return

            self.pb['value'] = 50
            self.lbl_status.config(text="Procesando cálculos...")

            # CREACIÓN DEL DATAFRAME
            df = pd.DataFrame(all_items)

            # --- ELIMINAR COLUMNA LINKS ---
            df = df.drop(columns=['links'], errors='ignore')

            df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0)
            df['precio_publico'] = pd.to_numeric(df['precio_publico'], errors='coerce').fillna(0)
            df['pts_unit'] = df['precio_publico'].apply(self.calcular_puntos)
            df['pts_totales'] = df['pts_unit'] * df['cantidad']

            df[['MARCA_REP', 'TASA']] = df.apply(lambda r: pd.Series(self.get_tasa_y_marca(r)), axis=1)
            df['PAGO_VAR'] = (df['pts_totales'] * df['TASA']) * val_v
            df['PAGO_FIJO'] = df['pts_totales'] * val_f

            file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile=f"Comisiones_{f_ini}.xlsx")
            if not file_path: return

            self.lbl_status.config(text="Generando Excel profesional...")
            self.save_excel(df, file_path)

            self.pb['value'] = 100
            self.lbl_status.config(text="¡Reporte completado!", foreground="green")
            messagebox.showinfo("Éxito", "El reporte se ha generado correctamente.")

        except Exception as e:
            messagebox.showerror("Error Crítico", str(e))
        finally:
            self.btn_run.config(state='normal')
            self.pb['value'] = 0

    def save_excel(self, df, path):
        with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
            wb = writer.book
            head = wb.add_format(
                {'bold': True, 'font_color': 'white', 'bg_color': '#203764', 'border': 1, 'align': 'center',
                 'valign': 'vcenter'})
            mon = wb.add_format({'num_format': '$#,##0.00', 'border': 1, 'valign': 'vcenter'})
            num = wb.add_format({'num_format': '#,##0', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            pct = wb.add_format({'num_format': '0.0%', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            txt = wb.add_format({'border': 1, 'valign': 'vcenter'})

            # Escenario Variable
            res_v = df.groupby(['vendedor', 'ubicacion']).agg({'pts_totales': 'sum', 'PAGO_VAR': 'sum'}).reset_index()
            res_v.columns = ['VENDEDOR', 'UBICACION', 'PUNTOS', 'COMISION VARIABLE']
            res_v.to_excel(writer, sheet_name='Escenario Variable', index=False)
            ws1 = writer.sheets['Escenario Variable']
            for c, val in enumerate(res_v.columns): ws1.write(0, c, val, head)
            ws1.set_column('A:B', 30, txt)
            ws1.set_column('C:C', 15, num)
            ws1.set_column('D:D', 25, mon)

            # Escenario Fijo
            res_f = df.groupby(['vendedor', 'ubicacion']).agg({'pts_totales': 'sum', 'PAGO_FIJO': 'sum'}).reset_index()
            res_f.columns = ['VENDEDOR', 'UBICACION', 'PUNTOS TOTALES', 'COMISION GENERADA (0.92)']
            res_f.to_excel(writer, sheet_name='Escenario Fijo 0.92', index=False)
            ws2 = writer.sheets['Escenario Fijo 0.92']
            for c, val in enumerate(res_f.columns): ws2.write(0, c, val, head)
            ws2.set_column('A:B', 30, txt)
            ws2.set_column('C:C', 15, num)
            ws2.set_column('D:D', 25, mon)

            # Detalle
            df_detail = df.rename(
                columns={'MARCA_REP': 'MARCA', 'TASA': 'TASA %', 'PAGO_VAR': 'COM. VAR', 'PAGO_FIJO': 'COM. FIJA'})
            df_detail.to_excel(writer, sheet_name='Detalle Tecnico', index=False)
            ws3 = writer.sheets['Detalle Tecnico']
            for c, val in enumerate(df_detail.columns): ws3.write(0, c, val, head)
            ws3.set_column('B:B', 20, num)
            ws3.set_column('C:D', 20, txt)
            ws3.set_column('E:F', 20, txt)
            ws3.set_column('G:G', 20, mon)
            ws3.set_column('H:J', 20, txt)
            ws3.set_column('K:J', 12, num)
            ws3.set_column('M:M', 10, txt)
            ws3.set_column('N:N', 10, pct)
            ws3.set_column('O:P', 15, mon)


if __name__ == "__main__":
    root = tk.Tk()
    app = CommissionApp(root)
    root.mainloop()