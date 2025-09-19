# services/auth_service.py
import time
import requests
import urllib3
from clients.http_client import HTTPClient
from models.token import Token
from utils.logger import log_message

# Desabilitar warnings de SSL quando verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AuthService:
    """
    Serviço responsável por autenticação e cache de token.
    O token é renovado somente quando expirar ou se recebermos 401.
    """

    def __init__(self, auth_url=None, client_id=None, client_secret=None, token_json_path="$.access_token", logger=None, log_widget=None):
        self._cached_token = None
        self.http_client = HTTPClient()
        self.auth_url = auth_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_json_path = token_json_path
        self.expires_json_path = "$.expires_in"
        self.logger = logger
        self.log_widget = log_widget

    def log(self, message):
        if self.logger:
            self.logger(message)
        elif self.log_widget:
            log_message(self.log_widget, message)
        else:
            print(message)

    def get_token_sync(self):
        """
        Método síncrono para obter token, usado pela GUI.
        Usa as configurações passadas no construtor.
        """
        if not all([self.auth_url, self.client_id, self.client_secret]):
            self.log("❌ Configurações de autenticação incompletas")
            return None
            
        return self.get_token(
            self.auth_url, 
            self.client_id, 
            self.client_secret, 
            self.token_json_path, 
            self.expires_json_path
        )

    def get_token(self, auth_url, client_id, client_secret, token_path="$.access_token", expires_path="$.expires_in"):
        """
        Retorna um token válido, reutilizando do cache se ainda não expirou.
        """
        if self._cached_token and not self._cached_token.is_expired():
            self.log("🔑 Usando token em cache")
            return self._cached_token.value

        self.log("🔑 Solicitando novo token de autenticação...")
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(auth_url, data=payload, timeout=5, verify=False)
            response.raise_for_status()
            json_data = response.json()
            token_value = self.http_client.extract_token(json_data, token_path)
            expires_in = self.http_client.extract_token(json_data, expires_path)

            if not token_value or expires_in is None:
                raise ValueError("Token ou expires_in não encontrados na resposta.")

            # Cria Token com timestamp de expiração
            self._cached_token = Token(token_value, expires_in)
            self.log(f"✅ Novo token obtido, expira em {expires_in} segundos")
            return self._cached_token.value
        except Exception as e:
            self.log(f"❌ Falha ao obter token: {e}")
            return None

    def invalidate_token(self):
        """Invalida o token em cache, forçando renovação na próxima chamada."""
        self._cached_token = None
        self.log("⚠️ Token em cache invalidado")
