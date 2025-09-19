import aiohttp
from jsonpath_ng import parse
import time
import asyncio

# Cache de token em memória
_token_cache = {
    "token": None,
    "expires_at": 0,
    "auth_url": None,
    "client_id": None,
    "client_secret": None,
    "token_path": None
}

async def send_request(session, method, url, data=None, token=None):
    """
    Envia uma requisição HTTP assíncrona usando aiohttp.
    Suporta POST e GET. Se token for informado, usa Bearer Authorization.
    Retorna (resp, text)
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    method = method.upper()
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


def get_cached_token(auth_url, client_id, client_secret, token_path="$.access_token"):
    """
    Retorna token válido, usando cache se não expirou.
    Caso token esteja expirado ou não exista, faz nova requisição.
    """
    current_time = time.time()
    # Verifica se token armazenado ainda é válido
    if (_token_cache["token"]
        and _token_cache["expires_at"] > current_time
        and _token_cache["auth_url"] == auth_url
        and _token_cache["client_id"] == client_id
        and _token_cache["client_secret"] == client_secret
        and _token_cache["token_path"] == token_path):
        return _token_cache["token"]

    # Se não houver token válido, faz autenticação
    import requests
    resp = requests.post(auth_url, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    })
    resp.raise_for_status()
    json_data = resp.json()

    token = extract_token(json_data, token_path)
    expires_in = json_data.get("expires_in", 3600)  # default 1 hora
    _token_cache.update({
        "token": token,
        "expires_at": current_time + expires_in,
        "auth_url": auth_url,
        "client_id": client_id,
        "client_secret": client_secret,
        "token_path": token_path
    })
    return token


def invalidate_token():
    """
    Invalida o token cacheado, forçando nova requisição na próxima chamada.
    """
    _token_cache.update({
        "token": None,
        "expires_at": 0,
        "auth_url": None,
        "client_id": None,
        "client_secret": None,
        "token_path": None
    })
