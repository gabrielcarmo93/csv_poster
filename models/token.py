# models/token.py

import time

class Token:
    """
    Representa um token de autenticação com valor e tempo de expiração.
    """

    def __init__(self, value: str, expires_in: int):
        """
        :param value: Valor do token
        :param expires_in: Tempo de validade em segundos
        """
        self.value = value
        self.expires_at = time.time() + expires_in  # Timestamp de expiração

    def is_expired(self) -> bool:
        """
        Retorna True se o token estiver expirado, False caso contrário.
        """
        return time.time() >= self.expires_at

    def remaining_seconds(self) -> int:
        """
        Retorna quantos segundos faltam para expirar. Retorna 0 se já expirou.
        """
        remaining = self.expires_at - time.time()
        return max(0, int(remaining))
