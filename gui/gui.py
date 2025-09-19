# gui/gui.py
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog
import json
import threading
import random
from utils.logger import log_message_with_level
from utils.csv_utils import read_csv_preview
from utils.logger import log_message
from services.uploader_service import UploaderService
from services.auth_service import AuthService
from config import Settings
from datetime import datetime
import os
import requests


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
        self.method_var = ttk.StringVar(value=getattr(self.settings, "METHOD", "POST"))
        self.auth_var = ttk.BooleanVar(value=False)
        
        # Theme variables
        self.current_theme = ttk.StringVar(value="darkly")
        self.light_themes = ["cosmo", "flatly", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "united", "yeti"]
        self.dark_themes = ["darkly", "cyborg", "superhero", "vapor"]

        # Criar menu superior para seleção de tema
        self.create_theme_menu()

        # Notebook e abas
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(50, 10))
        self.config_frame = ttk.Frame(self.notebook)
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="Configurações")
        self.notebook.add(self.log_frame, text="Logs")

        # Construir abas
        self.build_config_tab()
        self.build_log_tab()

    def create_theme_menu(self):
        """Cria o menu superior para seleção de tema"""
        # Frame superior para controles de tema
        theme_frame = ttk.Frame(self.root)
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        # Label e combobox para seleção de tema
        ttk.Label(theme_frame, text="🎨 Tema:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 5))
        
        # Combobox com todos os temas disponíveis
        all_themes = self.light_themes + self.dark_themes
        self.theme_combo = ttk.Combobox(
            theme_frame, 
            textvariable=self.current_theme,
            values=all_themes,
            state="readonly",
            width=15,
            bootstyle="info"
        )
        self.theme_combo.pack(side="left", padx=5)
        self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # Botões para alternar rapidamente entre claro/escuro
        ttk.Button(
            theme_frame, 
            text="☀️ Claro", 
            bootstyle="outline-warning",
            command=self.set_light_theme
        ).pack(side="left", padx=5)
        
        ttk.Button(
            theme_frame, 
            text="🌙 Escuro", 
            bootstyle="outline-info",
            command=self.set_dark_theme
        ).pack(side="left", padx=5)
        
        # Separador visual
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=10, pady=5)

    def change_theme(self, event=None):
        """Altera o tema da aplicação"""
        try:
            new_theme = self.current_theme.get()
            self.root.style.theme_use(new_theme)
            self.log(f"🎨 Tema alterado para: {new_theme}")
        except Exception as e:
            self.log(f"❌ Erro ao alterar tema: {e}")

    def set_light_theme(self):
        """Define um tema claro aleatório"""
        
        light_theme = random.choice(self.light_themes)
        self.current_theme.set(light_theme)
        self.change_theme()

    def set_dark_theme(self):
        """Define um tema escuro aleatório"""
        dark_theme = random.choice(self.dark_themes)
        self.current_theme.set(dark_theme)
        self.change_theme()

    # =====================
    # Aba de Configurações
    # =====================
    def build_config_tab(self):
        frame = self.config_frame

        # Endpoint URL
        ttk.Label(frame, text="Endpoint URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.url_entry = ttk.Entry(frame, width=50, bootstyle="info")
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)
        self.url_entry.insert(0, getattr(self.settings, "ENDPOINT_URL", ""))
        self.validate_button = ttk.Button(frame, text="Validar Endpoint", bootstyle="outline-success", command=lambda: self.validate_url(self.url_entry, "main"))
        self.validate_button.grid(row=0, column=2, padx=5)
        self.status_label = ttk.Label(frame, text="", width=15)
        self.status_label.grid(row=0, column=3, padx=5)

        # Método HTTP
        ttk.Label(frame, text="Método HTTP:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        method_frame = ttk.Frame(frame)
        method_frame.grid(row=1, column=1, sticky="w", padx=5)
        ttk.Radiobutton(method_frame, text="POST", variable=self.method_var, value="POST", bootstyle="info").pack(side="left", padx=5)
        ttk.Radiobutton(method_frame, text="GET", variable=self.method_var, value="GET", bootstyle="info").pack(side="left", padx=5)

        # Concorrência
        ttk.Label(frame, text="Concorrência:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.concurrency_entry = ttk.Entry(frame, width=10, bootstyle="warning")
        self.concurrency_entry.insert(0, str(getattr(self.settings, "CONCURRENCY", 10)))
        self.concurrency_entry.grid(row=2, column=1, sticky="w", padx=5)

        # Autenticação
        self.auth_check = ttk.Checkbutton(
            frame, text="Requer Autenticação", variable=self.auth_var, command=self.toggle_auth_fields, bootstyle="round-toggle"
        )
        self.auth_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=10)

        # Campos de autenticação
        self.auth_frame = ttk.Frame(frame)
        self.auth_frame.grid(row=4, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ttk.Label(self.auth_frame, text="Auth URL:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.auth_url_entry = ttk.Entry(self.auth_frame, width=40, bootstyle="info")
        self.auth_url_entry.grid(row=0, column=1, padx=5, pady=2)
        self.auth_validate_button = ttk.Button(self.auth_frame, text="Validar Auth URL", bootstyle="outline-success", command=lambda: self.validate_url(self.auth_url_entry, "auth"))
        self.auth_validate_button.grid(row=0, column=2, padx=5)
        self.auth_status_label = ttk.Label(self.auth_frame, text="", width=15)
        self.auth_status_label.grid(row=0, column=3, padx=5)

        ttk.Label(self.auth_frame, text="Client ID:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.client_id_entry = ttk.Entry(self.auth_frame, width=40, bootstyle="info")
        self.client_id_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(self.auth_frame, text="Client Secret:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.client_secret_entry = ttk.Entry(self.auth_frame, width=40, show="*", bootstyle="info")
        self.client_secret_entry.grid(row=2, column=1, padx=5, pady=2)
        ttk.Label(self.auth_frame, text="Token JSONPath:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.token_path_entry = ttk.Entry(self.auth_frame, width=40, bootstyle="info")
        self.token_path_entry.insert(0, "$.access_token")
        self.token_path_entry.grid(row=3, column=1, padx=5, pady=2)
        self.auth_frame.grid_remove()

        # Seleção do CSV
        self.csv_button = ttk.Button(frame, text="📁 Selecionar CSV", bootstyle="primary", command=self.load_csv)
        self.csv_button.grid(row=5, column=0, pady=10, padx=5)
        self.csv_label = ttk.Label(frame, text="Nenhum arquivo selecionado", bootstyle="secondary")
        self.csv_label.grid(row=5, column=1, columnspan=2, sticky="w", padx=5)

        # Delimitador
        ttk.Label(frame, text="Delimitador do CSV:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
        self.delimiter_entry = ttk.Entry(frame, width=5, bootstyle="warning")
        self.delimiter_entry.grid(row=6, column=1, sticky="w", padx=5)
        self.delimiter_entry.insert(0, getattr(self.settings, "DELIMITER", ","))
        self.delimiter_entry.bind("<KeyRelease>", self.refresh_preview)

        # Body preview
        ttk.Label(frame, text="Body Preview (primeiras linhas do CSV):").grid(row=7, column=0, sticky="w", pady=(10,0), padx=5)
        self.body_preview = ttk.Text(frame, height=10, width=80)
        self.body_preview.grid(row=8, column=0, columnspan=4, padx=5, pady=5)

        # Start button
        self.start_button = ttk.Button(frame, text="🚀 Iniciar Envio", bootstyle="success-outline", command=self.start_posting)
        self.start_button.grid(row=9, column=0, pady=15, padx=5)

    # =====================
    # Aba de Logs
    # =====================
    def build_log_tab(self):
        # Frame superior para controles dos logs
        log_controls_frame = ttk.Frame(self.log_frame)
        log_controls_frame.pack(fill="x", padx=5, pady=5)
        
        # Botão para limpar logs
        self.clear_logs_button = ttk.Button(
            log_controls_frame, 
            text="🗑️ Limpar Logs", 
            bootstyle="outline-danger",
            command=self.clear_logs
        )
        self.clear_logs_button.pack(side="left", padx=5)
        
        # Botão para salvar logs
        self.save_logs_button = ttk.Button(
            log_controls_frame, 
            text="💾 Salvar Logs", 
            bootstyle="outline-info",
            command=self.save_logs
        )
        self.save_logs_button.pack(side="left", padx=5)
        
        # Informação sobre quantidade de linhas
        self.log_info_label = ttk.Label(
            log_controls_frame, 
            text="0 linhas", 
            bootstyle="secondary"
        )
        self.log_info_label.pack(side="right", padx=5)
        
        # Área de texto dos logs
        self.log_text = ttk.Text(self.log_frame, height=25, width=100)
        self.log_text.pack(padx=5, pady=(0, 5), fill="both", expand=True)
        
        # Scrollbar para o texto dos logs
        scrollbar = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def log(self, msg):
        log_message(self.log_text, msg)
        self.update_log_info()

    def log_with_level(self, msg, level="INFO"):
        """Log com nível específico (INFO, WARNING, ERROR, SUCCESS, DEBUG)"""
        
        log_message_with_level(self.log_text, msg, level)
        self.update_log_info()

    def clear_logs(self):
        """Limpa todos os logs da área de texto"""
        self.log_text.delete("1.0", "end")
        self.update_log_info()
        # Usar timestamp direto para evitar recursão infinita na primeira limpeza
        
        timestamp = datetime.now().strftime("[%d/%m/%Y %H:%M:%S]")
        self.log_text.insert("end", f"{timestamp} 🗑️ Logs limpos\n")
        self.log_text.see("end")
        self.update_log_info()

    def save_logs(self):
        """Salva os logs atuais em um arquivo"""
        try:
            
            
            # Obter conteúdo dos logs
            content = self.log_text.get("1.0", "end")
            if not content.strip():
                Messagebox.show_warning("Não há logs para salvar.", "Aviso")
                return
            
            # Criar diretório de logs se não existir
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"csv_poster_logs_{timestamp}.txt"
            filepath = os.path.join(log_dir, filename)
            
            # Adicionar cabeçalho ao arquivo
            header = f"""CSV Poster - Log Export
======================
Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
Arquivo: {filename}

Conteúdo dos Logs:
------------------

"""
            
            # Salvar arquivo
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header + content)
            
            self.log(f"💾 Logs salvos em: {filepath}")
            Messagebox.show_info(f"Logs salvos com sucesso em:\n{filepath}", "Logs Salvos")
            
        except Exception as e:
            error_msg = f"❌ Erro ao salvar logs: {e}"
            self.log(error_msg)
            Messagebox.show_error(error_msg, "Erro")

    def update_log_info(self):
        """Atualiza a informação sobre quantidade de linhas nos logs"""
        try:
            # Contar linhas não vazias
            content = self.log_text.get("1.0", "end")
            lines = [line for line in content.split('\n') if line.strip()]
            line_count = len(lines)
            
            # Atualizar label
            if line_count == 0:
                self.log_info_label.config(text="0 linhas")
            elif line_count == 1:
                self.log_info_label.config(text="1 linha")
            else:
                self.log_info_label.config(text=f"{line_count} linhas")
        except:
            self.log_info_label.config(text="0 linhas")

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
            self.body_preview.delete("1.0", "end")
            self.body_preview.insert("end", preview_json)
        except Exception as e:
            self.body_preview.delete("1.0", "end")
            self.body_preview.insert("end", f"Erro ao ler CSV: {e}")

    def validate_url(self, entry_widget, url_type):
        """
        Valida se a URL é acessível fazendo uma requisição HEAD.
        url_type pode ser 'main' ou 'auth'
        """
        url = entry_widget.get().strip()
        if not url:
            Messagebox.show_error("Informe a URL.", "Erro")
            return
        # Aqui só fazemos uma checagem rápida visual
        try:
            
            resp = requests.head(url, timeout=5, verify=False)
            valid = 200 <= resp.status_code < 400
        except Exception:
            valid = False

        # Atualiza label de status
        if url_type == "main":
            status_label = self.status_label
        else:  # auth
            status_label = self.auth_status_label
        
        if valid:
            status_label.config(text="✅ Válida", bootstyle="success")
        else:
            status_label.config(text="❌ Inválida", bootstyle="danger")

        self.log(f"URL {'válida' if valid else 'inválida'}: {url}")

    # =====================
    # Iniciar envio
    # =====================
    def start_posting(self):
        if not self.csv_file:
            Messagebox.show_error("Selecione um CSV primeiro.", "Erro")
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
