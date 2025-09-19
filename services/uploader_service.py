# services/uploader_service.py
import csv
import asyncio
from enum import Enum
from clients.http_client import HTTPClient
from config import Settings

class UploadState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"

class UploaderService:
    """
    Serviço responsável por orquestrar o envio de linhas do CSV
    com controle de concorrência e suporte a pause/resume.
    """

    def __init__(self, file_path, auth_token, endpoint_url, delimiter=None, method=None, concurrency=None, logger=None):
        settings = Settings()
        
        self.file_path = file_path or settings.default_csv_file
        self.delimiter = delimiter or settings.default_csv_delimiter
        self.method = (method or settings.default_method).upper()
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.logger = logger
        self.concurrency = concurrency or settings.default_concurrency
        
        # Upload control
        self.state = UploadState.STOPPED
        self._pause_requested = False  # Flag simples para pause
        
        # Progress tracking
        self.current_index = 0
        self.total_rows = 0
        self.rows_data = []

    def run_upload(self):
        """
        Método principal que executa o upload com suporte completo a pause/resume.
        Mantém o loop vivo durante pause/resume.
        """
        async def upload_with_pause_support():
            # Carregar dados do CSV apenas se não estiverem carregados
            if not self.rows_data:
                with open(self.file_path, newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile, delimiter=self.delimiter)
                    self.rows_data = list(reader)
                self.total_rows = len(self.rows_data)
            
            # Log inicial
            if self.logger:
                if self.current_index == 0:
                    self.logger(f"🚀 Iniciando envio de {self.total_rows} linhas com concorrência {self.concurrency}...")
                else:
                    self.logger(f"▶️ Retomando envio na linha {self.current_index + 1}/{self.total_rows}...")

            # Configurar sessão HTTP
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(ssl=False)
            semaphore = asyncio.Semaphore(self.concurrency)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                # Loop principal que NUNCA termina até stop ou completion
                while self.state != UploadState.STOPPED:
                    
                    # Verificar se está pausado e aguardar se necessário
                    if self.state == UploadState.PAUSED:
                        if self.logger:
                            self.logger(f"⏸️ Upload pausado na linha {self.current_index + 1}/{self.total_rows}. Aguardando retomada...")
                        
                        # Polling em vez de event para evitar problemas de sincronização
                        while self.state == UploadState.PAUSED:
                            await asyncio.sleep(0.1)  # Verificar a cada 100ms
                            if self.state == UploadState.STOPPED:
                                break
                        
                        # Verificar se foi parado durante a pausa
                        if self.state == UploadState.STOPPED:
                            if self.logger:
                                self.logger("🛑 Upload foi parado durante a pausa.")
                            break
                            
                        # Log de retomada
                        if self.logger:
                            self.logger(f"▶️ Retomando upload da linha {self.current_index + 1}/{self.total_rows}...")
                    
                    # Verificar se já terminou
                    if self.current_index >= self.total_rows:
                        if self.logger:
                            self.logger("🎉 Upload concluído com sucesso!")
                        break
                    
                    # Processar próximo batch APENAS se estiver rodando
                    if self.state == UploadState.RUNNING:
                        batch_size = min(self.concurrency, self.total_rows - self.current_index)
                        batch_end = min(self.current_index + batch_size, self.total_rows)
                        
                        if self.logger:
                            progress_percent = (self.current_index / self.total_rows) * 100
                            self.logger(f"📦 Processando batch {self.current_index + 1}-{batch_end} ({progress_percent:.1f}%)")
                        
                        # Criar tarefas para o batch atual
                        batch_tasks = []
                        for idx in range(self.current_index, batch_end):
                            # Verificar novamente se não foi pausado/parado durante criação do batch
                            if self.state != UploadState.RUNNING:
                                break
                            
                            row = self.rows_data[idx]
                            batch_tasks.append(
                                self._send_row(session, row, semaphore, idx + 1, self.total_rows)
                            )
                        
                        # Executar batch se há tarefas
                        if batch_tasks and self.state == UploadState.RUNNING:
                            try:
                                # Executar todas as tarefas do batch
                                await asyncio.gather(*batch_tasks, return_exceptions=True)
                                
                                # Atualizar progresso APENAS se ainda está rodando
                                if self.state == UploadState.RUNNING:
                                    self.current_index = batch_end
                                    if self.logger:
                                        self.logger(f"✅ Batch concluído. Progresso: {self.current_index}/{self.total_rows}")
                                    
                                    # Pequena pausa entre batches se ainda há mais para processar
                                    if self.current_index < self.total_rows and self.state == UploadState.RUNNING:
                                        await asyncio.sleep(0.1)
                                else:
                                    # Se o estado mudou durante a execução, não atualizar progresso
                                    if self.logger:
                                        self.logger(f"⚠️ Estado mudou durante execução do batch. Não atualizando progresso.")
                                    
                            except Exception as e:
                                if self.logger:
                                    self.logger(f"❌ Erro durante execução do batch: {e}")
                                break
                    else:
                        # Se não está rodando, fazer uma pequena pausa antes de verificar novamente
                        await asyncio.sleep(0.1)

            # Log final baseado no estado
            if self.state == UploadState.STOPPED:
                if self.logger:
                    self.logger("🛑 Upload interrompido!")
            elif self.current_index >= self.total_rows:
                if self.logger:
                    self.logger("🎉 Upload concluído com sucesso!")
        
        try:
            # Executar o upload assíncrono
            asyncio.run(upload_with_pause_support())
        except Exception as e:
            if self.logger:
                self.logger(f"❌ Erro fatal no run_upload: {e}")

    async def _send_row(self, session, row, semaphore, current_row, total_rows):
        """Envia uma única linha para o endpoint com controle de semáforo"""
        async with semaphore:
            try:
                # Verificar se ainda deve processar (pode ter pausado durante await)
                if self.state != UploadState.RUNNING:
                    return  # Pausado ou parado
                
                headers = {"Content-Type": "application/json"}
                if self.auth_token:
                    headers["Authorization"] = f"Bearer {self.auth_token}"
                
                # Fazer a requisição HTTP
                async with session.post(self.endpoint_url, json=row, headers=headers) as response:
                    if response.status in [200, 201]:
                        if self.logger:
                            self.logger(f"✅ Linha {current_row}/{total_rows}: Status {response.status}")
                    else:
                        if self.logger:
                            self.logger(f"⚠️ Linha {current_row}/{total_rows}: Status {response.status}")
                            
            except Exception as e:
                if self.logger:
                    self.logger(f"❌ Erro na linha {current_row}/{total_rows}: {e}")

    def start_upload(self):
        """Inicia o upload (primeira vez ou após reset)"""
        self.state = UploadState.RUNNING
        
        # Reset apenas se for um novo upload (não resume)
        if self.current_index == 0:
            self.rows_data = []  # Forçar reload dos dados
        
        if self.logger:
            self.logger("🔄 Upload iniciado...")
        
    def pause_upload(self):
        """Pausa o upload atual"""
        if self.state == UploadState.RUNNING:
            self.state = UploadState.PAUSED
            if self.logger:
                self.logger(f"⏸️ Pausando upload na linha {self.current_index + 1}...")
    
    def resume_upload(self):
        """Retoma o upload pausado"""
        if self.state == UploadState.PAUSED:
            self.state = UploadState.RUNNING
            if self.logger:
                self.logger(f"▶️ Retomando upload da linha {self.current_index + 1}...")

    def stop_upload(self):
        """Para o upload completamente e reseta progresso"""
        self.state = UploadState.STOPPED
        self.current_index = 0  # Reset progresso
        if self.logger:
            self.logger("🛑 Upload parado e progresso resetado.")
    
    def get_progress(self):
        """Retorna o progresso atual do upload"""
        if self.total_rows == 0:
            return 0, 0, 0.0
        progress_percent = (self.current_index / self.total_rows) * 100
        return self.current_index, self.total_rows, progress_percent