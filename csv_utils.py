# csv_utils.py
import csv
import asyncio
from http_utils import send_request


def read_csv_preview(file_path, delimiter, num_lines=3):
    """
    Lê as primeiras linhas de um CSV para exibir como preview.
    Retorna uma lista de dicionários (cada linha representada como dict).
    """
    preview = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        for i, row in enumerate(reader):
            if i >= num_lines:
                break
            preview.append(row)
    return preview


class CSVUploader:
    """
    Classe responsável por orquestrar o envio de linhas do CSV
    com controle de concorrência.
    """

    def __init__(self, file_path, delimiter, method, endpoint_url, auth_token, logger, concurrency=10):
        self.file_path = file_path
        self.delimiter = delimiter
        self.method = method.upper()
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.logger = logger
        self.concurrency = concurrency

    async def _send_row(self, session, row, semaphore, idx, total):
        """
        Envia uma linha do CSV respeitando o limite de concorrência.
        """
        async with semaphore:
            try:
                response, text = await send_request(
                    session=session,
                    method=self.method,
                    url=self.endpoint_url,
                    data=row,
                    token=self.auth_token,
                )
                self.logger(f"[{idx}/{total}] OK → {row} → Status {response.status}")
            except Exception as e:
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
        self.logger(f"Iniciando envio de {total} linhas com concorrência {self.concurrency}...")

        import aiohttp
        async with aiohttp.ClientSession() as session:
            for idx, row in enumerate(rows, start=1):
                tasks.append(self._send_row(session, row, semaphore, idx, total))
            await asyncio.gather(*tasks)

        self.logger("Envio concluído!")

    def upload_all_sync(self):
        """
        Wrapper para rodar o upload assíncrono de forma síncrona,
        para ser chamado da GUI sem quebrar a thread principal.
        """
        asyncio.run(self.upload_all())
