# services/uploader_service.py
import csv
import asyncio
from clients.http_client import HTTPClient
from config import Settings

class UploaderService:
    """
    Serviço responsável por orquestrar o envio de linhas do CSV
    com controle de concorrência.
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

    async def _send_row(self, session, row, semaphore, idx, total):
        """
        Envia uma linha do CSV respeitando o limite de concorrência.
        """
        async with semaphore:
            try:
                response, text = await HTTPClient.send_request(
                    method=self.method,
                    url=self.endpoint_url,
                    data=row,
                    token=self.auth_token,
                )
                if self.logger:
                    self.logger(f"[{idx}/{total}] OK → {row} → Status {response.status}")
            except Exception as e:
                if self.logger:
                    self.logger(f"[{idx}/{total}] ERRO → {row} → {e}")

    async def upload_all(self):
        """
        Lê o CSV e envia todas as linhas de forma assíncrona,
        respeitando o limite de concorrência.
        """
        tasks = []
        semaphore = asyncio.Semaphore(self.concurrency)

        with open(self.file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=self.delimiter)
            rows = list(reader)

        total = len(rows)
        if self.logger:
            self.logger(f"Iniciando envio de {total} linhas com concorrência {self.concurrency}...")

        import aiohttp
        async with aiohttp.ClientSession() as session:
            for idx, row in enumerate(rows, start=1):
                tasks.append(
                    self._send_row(session, row, semaphore, idx, total)
                )
            await asyncio.gather(*tasks)

        if self.logger:
            self.logger("Envio concluído!")

    def start_upload(self):
        """
        Método de conveniência para ser chamado de forma síncrona,
        executando o loop assíncrono internamente.
        """
        asyncio.run(self.upload_all())
