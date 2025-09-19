# config/settings.py
class Settings:
  # URLs padrão
  ENDPOINT_URL = "https://"
  AUTH_URL = "https://"
  METHOD="POST"
  TOKEN_JSON_PATH="$.access_token"

  # Parâmetros de autenticação padrão
  CLIENT_ID = ""
  CLIENT_SECRET = ""

  # CSV
  DELIMITER = ";"
  PREVIEW_LINES = 5

  # Concorrência padrão
  CONCURRENCY = 10

  # Timeout das requisições HTTP (em segundos)
  HTTP_TIMEOUT = 10