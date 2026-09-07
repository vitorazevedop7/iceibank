"""Utilitario de teste: emite um JWT ja expirado, para evidenciar o cenario (c) da Parte F.

Uso:  python gerar_token_expirado.py
"""

from datetime import datetime, timedelta, timezone

import jwt

from src import config

agora = datetime.now(timezone.utc)
payload = {
    "sub": "ana",
    "tipo": "usuario",
    "contas": config.USUARIOS["ana"]["contas"],
    "iat": agora - timedelta(minutes=30),
    "exp": agora - timedelta(minutes=15),  # expirou ha 15 minutos
}
print(jwt.encode(payload, config.JWT_SEGREDO, algorithm=config.JWT_ALGORITMO))
