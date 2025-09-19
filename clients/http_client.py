# clients/http_client.py
import aiohttp
from jsonpath_ng import parse
import asyncio
import time
import ssl
import json
import os
from datetime import datetime


class HTTPClient:
    """
    Cliente HTTP assíncrono que suporta POST e GET, com Bearer Token opcional.
    """

    @staticmethod
    def _generate_curl_command(method, url, headers=None, data=None):
        """
        Gera um comando cURL equivalente à requisição HTTP.
        """
        curl_parts = ["curl", "-X", method.upper()]
        
        # Adicionar headers
        if headers:
            for key, value in headers.items():
                curl_parts.extend(["-H", f"'{key}: {value}'"])
        
        # Adicionar data para POST
        if method.upper() == "POST" and data:
            if isinstance(data, dict):
                curl_parts.extend(["-d", f"'{json.dumps(data)}'"])
                curl_parts.extend(["-H", "'Content-Type: application/json'"])
            else:
                curl_parts.extend(["-d", f"'{data}'"])
        
        # Adicionar parâmetros para GET
        elif method.upper() == "GET" and data:
            params = "&".join([f"{k}={v}" for k, v in data.items()])
            url = f"{url}?{params}"
        
        # Adicionar URL
        curl_parts.append(f"'{url}'")
        
        # Adicionar flag para ignorar SSL se necessário
        curl_parts.extend(["-k", "--insecure"])
        
        return " ".join(curl_parts)

    @staticmethod
    def _log_error_to_file(curl_command, error_info, response_text=None):
        """
        Salva o comando cURL e informações de erro em um arquivo de log.
        """
        try:
            # Criar diretório de logs se não existir
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"http_errors_{timestamp}.log")
            
            # Conteúdo do log
            log_content = f"""
HTTP REQUEST ERROR LOG
=====================
Timestamp: {datetime.now().isoformat()}

cURL Command:
{curl_command}

Error Information:
{error_info}
"""
            
            if response_text:
                log_content += f"""
Response Text:
{response_text}
"""
            
            log_content += "\n" + "="*50 + "\n"
            
            # Escrever no arquivo
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(log_content)
            
            print(f"Erro HTTP logado em: {log_file}")
            
        except Exception as e:
            print(f"Falha ao escrever log de erro: {e}")

    @staticmethod
    async def send_request(method, url, data=None, token=None):
        """
        Envia uma requisição HTTP assíncrona usando aiohttp.
        Suporta POST e GET. Se token for informado, usa Bearer Authorization.
        Em caso de erro, salva o cURL e informações do erro em arquivo.
        """
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        method = method.upper()
        
        # Gerar comando cURL para logging
        curl_command = HTTPClient._generate_curl_command(method, url, headers, data)

        # Criar connector SSL que ignora verificação de certificado
        connector = aiohttp.TCPConnector(ssl=False)

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                if method == "POST":
                    async with session.post(url, json=data, headers=headers) as resp:
                        text = await resp.text()
                        
                        # Verificar se houve erro HTTP
                        if resp.status >= 400:
                            error_info = f"HTTP {resp.status}: {resp.reason}"
                            HTTPClient._log_error_to_file(curl_command, error_info, text)
                        
                        return resp, text
                        
                elif method == "GET":
                    async with session.get(url, params=data, headers=headers) as resp:
                        text = await resp.text()
                        
                        # Verificar se houve erro HTTP
                        if resp.status >= 400:
                            error_info = f"HTTP {resp.status}: {resp.reason}"
                            HTTPClient._log_error_to_file(curl_command, error_info, text)
                        
                        return resp, text
                else:
                    raise ValueError(f"Método HTTP desconhecido: {method}")
                    
        except aiohttp.ClientError as e:
            # Erro de conexão/cliente
            error_info = f"aiohttp.ClientError: {str(e)}"
            HTTPClient._log_error_to_file(curl_command, error_info)
            raise
            
        except Exception as e:
            # Outros erros
            error_info = f"Exception: {type(e).__name__}: {str(e)}"
            HTTPClient._log_error_to_file(curl_command, error_info)
            raise

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
