import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import threading
import requests
import asyncio

from csv_utils import CSVUploader, read_csv_preview
from http_utils import extract_token


class CSVPosterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV to API Poster")
        self.csv_file = None
        self.uploader = None

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.config_frame = ttk.Frame(self.notebook)
        self.log_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.config_frame, text="Configurações")
        self.notebook.add(self.log_frame, text="Logs")

        self.build_config_tab()
        self.build_log_tab()

    def build_config_tab(self):
        frame = self.config_frame

        # Endpoint URL
        tk.Label(frame, text="Endpoint URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = tk.Entry(frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        # Validate Endpoint
        self.validate_button = tk.Button(frame, text="Validar Endpoint", command=self.validate_url)
        self.validate_button.grid(row=0, column=2, padx=5)
        self.status_canvas = tk.Canvas(frame, width=20, height=20, highlightthickness=0)
        self.status_canvas.grid(row=0, column=3)
        self.status_circle = None

        # Method selection (POST or GET)
        tk.Label(frame, text="Método HTTP:").grid(row=1, column=0, sticky="w")
        self.method_var = tk.StringVar(value="POST")
        tk.Radiobutton(frame, text="POST", variable=self.method_var, value="POST").grid(row=1, column=1, sticky="w")
        tk.Radiobutton(frame, text="GET", variable=self.method_var, value="GET").grid(row=1, column=2, sticky="w")

        # Concurrency
        tk.Label(frame, text="Concorrência:").grid(row=2, column=0, sticky="w")
        self.concurrency_entry = tk.Entry(frame, width=5)
        self.concurrency_entry.insert(0, "10")
        self.concurrency_entry.grid(row=2, column=1, sticky="w")

        # Authentication checkbox
        self.auth_var = tk.BooleanVar()
        self.auth_check = tk.Checkbutton(
            frame, text="Requer Autenticação", variable=self.auth_var, command=self.toggle_auth_fields
        )
        self.auth_check.grid(row=3, column=0, columnspan=2, sticky="w")

        # Auth fields
        self.auth_frame = ttk.Frame(frame)
        self.auth_frame.grid(row=4, column=0, columnspan=4, sticky="w")

        tk.Label(self.auth_frame, text="Auth URL:").grid(row=0, column=0, sticky="w")
        self.auth_url_entry = tk.Entry(self.auth_frame, width=40)
        self.auth_url_entry.grid(row=0, column=1, padx=5, pady=2)
        self.auth_validate_button = tk.Button(self.auth_frame, text="Validar Auth URL", command=self.validate_auth_url)
        self.auth_validate_button.grid(row=0, column=2, padx=5)
        self.auth_status_canvas = tk.Canvas(self.auth_frame, width=20, height=20, highlightthickness=0)
        self.auth_status_canvas.grid(row=0, column=3)
        self.auth_status_circle = None

        tk.Label(self.auth_frame, text="Client ID:").grid(row=1, column=0, sticky="w")
        self.client_id_entry = tk.Entry(self.auth_frame, width=40)
        self.client_id_entry.grid(row=1, column=1, padx=5, pady=2)

        tk.Label(self.auth_frame, text="Client Secret:").grid(row=2, column=0, sticky="w")
        self.client_secret_entry = tk.Entry(self.auth_frame, width=40, show="*")
        self.client_secret_entry.grid(row=2, column=1, padx=5, pady=2)

        tk.Label(self.auth_frame, text="Token JSONPath:").grid(row=3, column=0, sticky="w")
        self.token_path_entry = tk.Entry(self.auth_frame, width=40)
        self.token_path_entry.insert(0, "$.access_token")
        self.token_path_entry.grid(row=3, column=1, padx=5, pady=2)

        self.auth_frame.grid_remove()

        # CSV selection
        self.csv_button = tk.Button(frame, text="Selecionar CSV", command=self.load_csv)
        self.csv_button.grid(row=5, column=0, pady=5)
        self.csv_label = tk.Label(frame, text="Nenhum arquivo selecionado")
        self.csv_label.grid(row=5, column=1, columnspan=2, sticky="w")

        tk.Label(frame, text="Delimitador do CSV:").grid(row=6, column=0, sticky="w")
        self.delimiter_entry = tk.Entry(frame, width=3)
        self.delimiter_entry.grid(row=6, column=1, sticky="w")
        self.delimiter_entry.insert(0, ",")
        self.delimiter_entry.bind("<KeyRelease>", self.refresh_preview)

        # Body Preview
        tk.Label(frame, text="Body Preview (primeiras linhas do CSV):").grid(row=7, column=0, sticky="w", pady=(10, 0))
        self.body_preview = tk.Text(frame, height=10, width=80, bg="#f4f4f4")
        self.body_preview.grid(row=8, column=0, columnspan=4, padx=5, pady=5)

        # Start button
        self.start_button = tk.Button(frame, text="Iniciar Envio", command=self.start_posting)
        self.start_button.grid(row=9, column=0, pady=10)

    def build_log_tab(self):
        self.log_text = tk.Text(self.log_frame, height=25, width=100)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def toggle_auth_fields(self):
        if self.auth_var.get():
            self.auth_frame.grid()
        else:
            self.auth_frame.grid_remove()

    def load_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.csv_file = file_path
            self.csv_label.config(text=os.path.basename(file_path))
            self.refresh_preview()

    def refresh_preview(self, event=None):
        if not self.csv_file:
            return
        delimiter = self.delimiter_entry.get().strip() or ","
        try:
            preview = read_csv_preview(self.csv_file, delimiter, num_lines=3)
            preview_json = json.dumps(preview, indent=4, ensure_ascii=False)
            self.body_preview.delete("1.0", tk.END)
            self.body_preview.insert(tk.END, preview_json)
        except Exception as e:
            self.body_preview.delete("1.0", tk.END)
            self.body_preview.insert(tk.END, f"Erro ao ler CSV: {e}")

    def validate_url(self):
        url = self.url_entry.get().strip()
        self._validate_generic_url(url, self.status_canvas, "Endpoint")

    def validate_auth_url(self):
        url = self.auth_url_entry.get().strip()
        self._validate_generic_url(url, self.auth_status_canvas, "Auth URL")

    def _validate_generic_url(self, url, canvas, label):
        if not url:
            messagebox.showerror("Erro", f"Informe a URL para {label}.")
            return
        canvas.delete("all")
        try:
            r = requests.head(url, timeout=3)
            if r.status_code < 400:
                canvas.create_oval(2, 2, 18, 18, fill="green")
                self.log(f"✅ {label} válido: {url}")
            else:
                canvas.create_oval(2, 2, 18, 18, fill="red")
                self.log(f"❌ {label} respondeu com status {r.status_code}")
        except Exception as e:
            canvas.create_oval(2, 2, 18, 18, fill="red")
            self.log(f"❌ Erro ao validar {label}: {e}")

    def start_posting(self):
        if not self.csv_file:
            messagebox.showerror("Erro", "Selecione um arquivo CSV primeiro.")
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Erro", "Informe a URL do endpoint.")
            return

        method = self.method_var.get()
        delimiter = self.delimiter_entry.get().strip() or ","
        concurrency = int(self.concurrency_entry.get().strip() or 10)

        # autenticação
        token = None
        if self.auth_var.get():
            auth_url = self.auth_url_entry.get().strip()
            client_id = self.client_id_entry.get().strip()
            client_secret = self.client_secret_entry.get().strip()
            token_path = self.token_path_entry.get().strip() or "$.access_token"

            if not auth_url or not client_id or not client_secret:
                messagebox.showerror("Erro", "Preencha todos os campos de autenticação.")
                return

            try:
                resp = requests.post(auth_url, data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials"
                })
                resp.raise_for_status()
                token = extract_token(resp.json(), token_path)
                self.log("✅ Autenticação bem sucedida.")
            except Exception as e:
                self.log(f"❌ Falha na autenticação: {e}")
                return

        # cria uploader com parâmetros corretos
        self.uploader = CSVUploader(
            file_path=self.csv_file,
            delimiter=delimiter,
            method=method,
            endpoint_url=url,
            auth_token=token,
            logger=self.log,
            concurrency=concurrency
        )

        # troca aba ativa para logs
        self.notebook.select(self.log_frame)

        # inicia upload em thread separada, executando a coroutine de forma segura
        threading.Thread(target=lambda: asyncio.run(self.uploader.upload_all()), daemon=True).start()
