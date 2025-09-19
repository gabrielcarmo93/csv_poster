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
        self.upload_thread = None
        
        # Upload state tracking
        self.upload_state = "stopped"  # stopped, running, paused

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
        
        # Criar controles de upload (visíveis em todas as abas)
        self.create_control_buttons()

    def create_control_buttons(self):
        """Cria os botões de controle de upload visíveis em todas as abas"""
        # Frame principal para controles de upload
        control_frame = ttk.LabelFrame(self.root, text="🎮 Controles de Upload", bootstyle="primary")
        control_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Frame interno para organizar os botões
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(pady=10, padx=10)
        
        # Botões de controle
        self.start_button = ttk.Button(
            buttons_frame, 
            text="🚀 Iniciar", 
            bootstyle="success-outline", 
            command=self.start_posting,
            width=12
        )
        self.start_button.pack(side="left", padx=(0, 10))
        
        self.pause_resume_button = ttk.Button(
            buttons_frame, 
            text="⏸️ Pausar", 
            bootstyle="warning-outline", 
            command=self.pause_resume_posting, 
            state="disabled",
            width=12
        )
        self.pause_resume_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = ttk.Button(
            buttons_frame, 
            text="⏹️ Parar", 
            bootstyle="danger-outline", 
            command=self.stop_posting, 
            state="disabled",
            width=12
        )
        self.stop_button.pack(side="left", padx=(0, 10))
        
        # Label de status do upload
        self.upload_status_label = ttk.Label(
            buttons_frame, 
            text="📊 Pronto para upload", 
            bootstyle="info",
            font=("Segoe UI", 9, "bold")
        )
        self.upload_status_label.pack(side="left", padx=10)

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
        
        # Frame para conter o Text widget e scrollbars
        preview_frame = ttk.Frame(frame)
        preview_frame.grid(row=8, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        
        # Configurar grid para permitir expansão
        frame.grid_rowconfigure(8, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        
        # Text widget
        self.body_preview = ttk.Text(preview_frame, height=10, width=80, wrap="none")
        self.body_preview.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar vertical (auto-hide)
        v_scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.body_preview.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Scrollbar horizontal (auto-hide)
        h_scrollbar = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.body_preview.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure scrollbars to auto-hide
        def on_text_configure(event=None):
            # Update scrollbars
            self.body_preview.update_idletasks()
            
        def set_v_scrollbar(*args):
            v_scrollbar.set(*args)
            # Hide/show vertical scrollbar
            if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
                v_scrollbar.grid_remove()
            else:
                v_scrollbar.grid()
                
        def set_h_scrollbar(*args):
            h_scrollbar.set(*args)
            # Hide/show horizontal scrollbar
            if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
                h_scrollbar.grid_remove()
            else:
                h_scrollbar.grid()
        
        self.body_preview.configure(yscrollcommand=set_v_scrollbar, xscrollcommand=set_h_scrollbar)
        self.body_preview.bind('<Configure>', on_text_configure)

        # Start e Stop buttons - moved to create_control_buttons method

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
        
        # Área de texto dos logs com scrollbars
        log_text_frame = ttk.Frame(self.log_frame)
        log_text_frame.pack(padx=5, pady=(0, 5), fill="both", expand=True)
        
        # Configurar grid para expansão
        log_text_frame.grid_rowconfigure(0, weight=1)
        log_text_frame.grid_columnconfigure(0, weight=1)
        
        # Text widget para logs
        self.log_text = ttk.Text(log_text_frame, height=25, width=100, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar vertical para logs (auto-hide)
        log_v_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        log_v_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Scrollbar horizontal para logs (auto-hide)
        log_h_scrollbar = ttk.Scrollbar(log_text_frame, orient="horizontal", command=self.log_text.xview)
        log_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure scrollbars to auto-hide
        def set_log_v_scrollbar(*args):
            log_v_scrollbar.set(*args)
            # Hide/show vertical scrollbar
            if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
                log_v_scrollbar.grid_remove()
            else:
                log_v_scrollbar.grid()
                
        def set_log_h_scrollbar(*args):
            log_h_scrollbar.set(*args)
            # Hide/show horizontal scrollbar
            if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
                log_h_scrollbar.grid_remove()
            else:
                log_h_scrollbar.grid()
        
        self.log_text.configure(yscrollcommand=set_log_v_scrollbar, xscrollcommand=set_log_h_scrollbar)

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
        except Exception:
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
    # Iniciar/Parar envio
    # =====================
    def start_posting(self):
        if not self.csv_file:
            Messagebox.show_error("Selecione um CSV primeiro.", "Erro")
            return

        # Se já existe um uploader_service em pausa, apenas retomar
        if self.uploader_service and self.upload_state == "paused":
            self.resume_posting()
            return

        url = self.url_entry.get().strip()
        method = self.method_var.get()
        delimiter = self.delimiter_entry.get().strip() or ","
        concurrency = int(self.concurrency_entry.get().strip() or 10)

        # Atualizar estado
        self.upload_state = "running"
        self.update_button_states()

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

        # Iniciar o upload
        self.uploader_service.start_upload()
        
        # Inicia upload em thread separada
        self.upload_thread = threading.Thread(target=self.run_upload, daemon=True)
        self.upload_thread.start()

    def pause_resume_posting(self):
        """Alterna entre pausar e retomar o upload"""
        if not self.uploader_service:
            return
            
        if self.upload_state == "running":
            self.upload_state = "paused"
            self.uploader_service.pause_upload()
            self.pause_resume_button.config(text="▶️ Retomar")
            self.log("⏸️ Pausando upload...")
        elif self.upload_state == "paused":
            self.upload_state = "running"
            self.uploader_service.resume_upload()
            self.pause_resume_button.config(text="⏸️ Pausar")
            self.log("▶️ Retomando upload...")
            
            # CHAVE: Verificar se a thread ainda está viva, senão criar nova
            if not self.upload_thread or not self.upload_thread.is_alive():
                self.log("🔄 Thread terminou, criando nova para continuar o upload...")
                self.upload_thread = threading.Thread(target=self.run_upload, daemon=True)
                self.upload_thread.start()

    def resume_posting(self):
        """Retoma um upload pausado"""
        if self.uploader_service and self.upload_state == "paused":
            self.upload_state = "running"
            self.uploader_service.resume_upload()
            self.update_button_states()
            
            # CHAVE: Verificar se a thread ainda está viva, senão criar nova
            if not self.upload_thread or not self.upload_thread.is_alive():
                self.log("🔄 Thread terminou, criando nova para continuar o upload...")
                self.upload_thread = threading.Thread(target=self.run_upload, daemon=True)
                self.upload_thread.start()

    def stop_posting(self):
        """Para o envio em execução"""
        if self.uploader_service and self.upload_state in ["running", "paused"]:
            self.log("⏹️ Parando upload...")
            self.upload_state = "stopped"
            self.uploader_service.stop_upload()
            
            # Atualizar interface imediatamente
            self.stop_button.config(text="⏳ Parando...", state="disabled")
            
            # Aguardar um pouco e restaurar botões
            def restore_buttons():
                import time
                time.sleep(1)  # Dar tempo para as requests pararem
                self.upload_state = "stopped"
                self.update_button_states()
                self.log("🛑 Upload interrompido")
            
            # Executar restauração em thread separada
            threading.Thread(target=restore_buttons, daemon=True).start()

    def run_upload(self):
        """Executa o upload e restaura botões quando terminar"""
        try:
            self.uploader_service.run_upload()
        except Exception as e:
            self.log(f"❌ Erro durante o upload: {e}")
        finally:
            # Verificar estado final do uploader
            current_idx, total_rows, progress = self.uploader_service.get_progress()
            
            if current_idx >= total_rows:
                # Upload concluído
                self.upload_state = "stopped"
                self.uploader_service.current_index = 0  # Reset apenas quando completo
                self.log("✅ Upload finalizado com sucesso!")
                self.update_button_states()
            elif self.uploader_service.state.value == "stopped":
                # Upload foi parado manualmente
                self.upload_state = "stopped"
                self.log("🛑 Upload interrompido")
                self.update_button_states()
            elif self.uploader_service.state.value == "paused":
                # Upload está pausado - NÃO fazer nada aqui, thread vai terminar
                # mas o resume vai criar uma nova thread quando necessário
                self.log(f"⏸️ Thread finalizou, upload pausado na linha {current_idx + 1}/{total_rows}")
                # Manter estado pausado na GUI
                self.upload_state = "paused"
                self.update_button_states()
            else:
                # Outro estado, atualizar interface
                self.update_button_states()
    
    def update_button_states(self):
        """Atualiza o estado dos botões baseado no estado atual do upload"""
        if self.upload_state == "stopped":
            self.start_button.config(state="normal", text="🚀 Iniciar")
            self.pause_resume_button.config(state="disabled", text="⏸️ Pausar")
            self.stop_button.config(state="disabled", text="⏹️ Parar")
            self.upload_status_label.config(text="📊 Pronto para upload", bootstyle="info")
        elif self.upload_state == "running":
            self.start_button.config(state="disabled")
            self.pause_resume_button.config(state="normal", text="⏸️ Pausar")
            self.stop_button.config(state="normal", text="⏹️ Parar")
            self.upload_status_label.config(text="🚀 Upload em execução...", bootstyle="success")
        elif self.upload_state == "paused":
            self.start_button.config(state="normal", text="▶️ Retomar")
            self.pause_resume_button.config(state="normal", text="▶️ Retomar")
            self.stop_button.config(state="normal", text="⏹️ Parar")
            self.upload_status_label.config(text="⏸️ Upload pausado", bootstyle="warning")
