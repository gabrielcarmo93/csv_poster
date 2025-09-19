# clients/http_client.py
import aiohttp
from jsonpath_ng import parse
import asyncio
import time


class HTTPClient:
    """
    Cliente HTTP assíncrono que suporta POST e GET, com Bearer Token opcional.
    """

    @staticmethod
    async def send_request(method, url, data=None, token=None):
        """
        Envia uma requisição HTTP assíncrona usando aiohttp.
        Suporta POST e GET. Se token for informado, usa Bearer Authorization.
        """
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        method = method.upper()

        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(url, json=data, headers=headers) as resp:
                    text = await resp.text()
                    return resp, text
            elif method == "GET":
                async with session.get(url, params=data, headers=headers) as resp:
                    text = await resp.text()
                    return resp, text
            else:
                raise ValueError(f"Método HTTP desconhecido: {method}")

    @staticmethod
    def extract_token(json_data, json_path_str="$.access_token"):
        """
        Extrai o token do JSON retornado da autenticação usando JSONPath.
        Por padrão busca '$.access_token', mas o usuário pode passar outro JSONPath.
        """
        try:
            jsonpath_expr = parse(json_path_str)
            matches = [match.value for match in jsonpath_expr.find(json_data)]
            if matches:
                return matches[0]
            return None
        except Exception as e:
            raise ValueError(f"Falha ao extrair token com JSONPath '{json_path_str}': {e}")
