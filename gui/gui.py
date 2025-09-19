# gui/gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import threading

from utils.csv_utils import read_csv_preview
from utils.logger import log_message
from services.uploader_service import UploaderService
from services.auth_service import AuthService
from config import Settings


class CSVPosterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV to API Poster")
        self.csv_file = None

        # Services (serão inicializados ao iniciar o envio)
        self.uploader_service = None
        self.auth_service = None

        # Settings
        self.settings = Settings()

        # Variables
        self.method_var = tk.StringVar(value=getattr(self.settings, "METHOD", "POST"))
        self.auth_var = tk.BooleanVar(value=False)

        # Notebook e abas
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)
        self.config_frame = ttk.Frame(self.notebook)
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="Configurações")
        self.notebook.add(self.log_frame, text="Logs")

        # Construir abas
        self.build_config_tab()
        self.build_log_tab()

    # =====================
    # Aba de Configurações
    # =====================
    def build_config_tab(self):
        frame = self.config_frame

        # Endpoint URL
        tk.Label(frame, text="Endpoint URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = tk.Entry(frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)
        self.url_entry.insert(0, getattr(self.settings, "ENDPOINT_URL", ""))
        self.validate_button = tk.Button(frame, text="Validar Endpoint", command=lambda: self.validate_url(self.url_entry, frame))
        self.validate_button.grid(row=0, column=2, padx=5)
        self.status_canvas = tk.Canvas(frame, width=20, height=20, highlightthickness=0)
        self.status_canvas.grid(row=0, column=3, padx=5)

        # Método HTTP
        tk.Label(frame, text="Método HTTP:").grid(row=1, column=0, sticky="w")
        tk.Radiobutton(frame, text="POST", variable=self.method_var, value="POST").grid(row=1, column=1, sticky="w")
        tk.Radiobutton(frame, text="GET", variable=self.method_var, value="GET").grid(row=1, column=2, sticky="w")

        # Concorrência
        tk.Label(frame, text="Concorrência:").grid(row=2, column=0, sticky="w")
        self.concurrency_entry = tk.Entry(frame, width=5)
        self.concurrency_entry.insert(0, str(getattr(self.settings, "CONCURRENCY", 10)))
        self.concurrency_entry.grid(row=2, column=1, sticky="w")

        # Autenticação
        self.auth_check = tk.Checkbutton(
            frame, text="Requer Autenticação", variable=self.auth_var, command=self.toggle_auth_fields
        )
        self.auth_check.grid(row=3, column=0, columnspan=2, sticky="w")

        # Campos de autenticação
        self.auth_frame = ttk.Frame(frame)
        self.auth_frame.grid(row=4, column=0, columnspan=4, sticky="w")
        tk.Label(self.auth_frame, text="Auth URL:").grid(row=0, column=0, sticky="w")
        self.auth_url_entry = tk.Entry(self.auth_frame, width=40)
        self.auth_url_entry.grid(row=0, column=1, padx=5, pady=2)
        self.auth_validate_button = tk.Button(self.auth_frame, text="Validar Auth URL", command=lambda: self.validate_url(self.auth_url_entry, self.auth_frame))
        self.auth_validate_button.grid(row=0, column=2, padx=5)
        self.auth_status_canvas = tk.Canvas(self.auth_frame, width=20, height=20, highlightthickness=0)
        self.auth_status_canvas.grid(row=0, column=3, padx=5)

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

        # Seleção do CSV
        self.csv_button = tk.Button(frame, text="Selecionar CSV", command=self.load_csv)
        self.csv_button.grid(row=5, column=0, pady=5)
        self.csv_label = tk.Label(frame, text="Nenhum arquivo selecionado")
        self.csv_label.grid(row=5, column=1, columnspan=2, sticky="w")

        # Delimitador
        tk.Label(frame, text="Delimitador do CSV:").grid(row=6, column=0, sticky="w")
        self.delimiter_entry = tk.Entry(frame, width=3)
        self.delimiter_entry.grid(row=6, column=1, sticky="w")
        self.delimiter_entry.insert(0, getattr(self.settings, "DELIMITER", ","))
        self.delimiter_entry.bind("<KeyRelease>", self.refresh_preview)

        # Body preview
        tk.Label(frame, text="Body Preview (primeiras linhas do CSV):").grid(row=7, column=0, sticky="w", pady=(10,0))
        self.body_preview = tk.Text(frame, height=10, width=80, bg="#f4f4f4")
        self.body_preview.grid(row=8, column=0, columnspan=4, padx=5, pady=5)

        # Start button
        self.start_button = tk.Button(frame, text="Iniciar Envio", command=self.start_posting)
        self.start_button.grid(row=9, column=0, pady=10)

    # =====================
    # Aba de Logs
    # =====================
    def build_log_tab(self):
        self.log_text = tk.Text(self.log_frame, height=25, width=100)
        self.log_text.pack(padx=5, pady=5, fill="both", expand=True)

    def log(self, msg):
        log_message(self.log_text, msg)

    # =====================
    # Funções auxiliares
    # =====================
    def toggle_auth_fields(self):
        if self.auth_var.get():
            self.auth_frame.grid()
        else:
            self.auth_frame.grid_remove()

    def load_csv(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.csv_file = file_path
            self.csv_label.config(text=file_path.split("/")[-1])
            self.refresh_preview()

    def refresh_preview(self, event=None):
        self.settings = Settings()
        
        if not self.csv_file:
            return
        delimiter = self.delimiter_entry.get().strip() or ","
        try:
            num_lines = self.settings.PREVIEW_LINES or 3
            preview = read_csv_preview(self.csv_file, delimiter, num_lines)
            preview_json = json.dumps(preview, indent=4, ensure_ascii=False)
            self.body_preview.delete("1.0", tk.END)
            self.body_preview.insert(tk.END, preview_json)
        except Exception as e:
            self.body_preview.delete("1.0", tk.END)
            self.body_preview.insert(tk.END, f"Erro ao ler CSV: {e}")

    def validate_url(self, entry_widget, parent_frame):
        url = entry_widget.get().strip()
        if not url:
            messagebox.showerror("Erro", "Informe a URL.")
            return
        # Aqui só fazemos uma checagem rápida visual
        try:
            import requests
            resp = requests.head(url, timeout=5)
            valid = 200 <= resp.status_code < 400
        except Exception:
            valid = False

        # Atualiza canvas de status
        canvas = self.status_canvas if parent_frame == self.config_frame else self.auth_status_canvas
        canvas.delete("all")
        color = "green" if valid else "red"
        canvas.create_oval(0, 0, 20, 20, fill=color)

        self.log(f"URL {'válida' if valid else 'inválida'}: {url}")

    # =====================
    # Iniciar envio
    # =====================
    def start_posting(self):
        if not self.csv_file:
            messagebox.showerror("Erro", "Selecione um CSV primeiro.")
            return

        url = self.url_entry.get().strip()
        method = self.method_var.get()
        delimiter = self.delimiter_entry.get().strip() or ","
        concurrency = int(self.concurrency_entry.get().strip() or 10)

        # Configurar AuthService se necessário
        token = None
        if self.auth_var.get():
            self.auth_service = AuthService(
                auth_url=self.auth_url_entry.get().strip(),
                client_id=self.client_id_entry.get().strip(),
                client_secret=self.client_secret_entry.get().strip(),
                token_json_path=self.token_path_entry.get().strip() or "$.access_token",
                logger=self.log
            )
            token = self.auth_service.get_token_sync()

        # Configurar UploaderService
        self.uploader_service = UploaderService(
            file_path=self.csv_file,
            auth_token=token,
            endpoint_url=url,
            delimiter=delimiter,
            method=method,
            concurrency=concurrency,
            logger=self.log
        )

        # Troca aba ativa para logs
        self.notebook.select(self.log_frame)

        # Inicia upload em thread separada
        threading.Thread(target=self.uploader_service.start_upload, daemon=True).start()
