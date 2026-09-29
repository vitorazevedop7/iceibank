"""Ponto de entrada da agencia: cria o app FastAPI, monta o estado do processo e sobe o uvicorn.

Uma unica base de codigo executada 3 vezes com AGENCIA_ID diferente forma as 3
agencias do ICEIBank. O estado (contas, relogio, log) e por processo - e disso que
depende a ideia de particao.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import config
from src.controllers import transferencias_controller
from src.routes import router
from src.services import Mensageria, RegistroEventos, RelogioVetorial


def criar_app(id_agencia: int) -> FastAPI:
    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        # Conecta ao RabbitMQ, declara a topologia e comeca a consumir a fila desta
        # agencia antes de aceitar a primeira requisicao HTTP. O consumidor roda no
        # mesmo event loop do uvicorn.
        mensageria = Mensageria(config.RABBITMQ_URL, config.NUMERO_AGENCIAS)
        await mensageria.conectar()
        app.state.mensageria = mensageria

        async def tratar_credito(corpo: dict, reentrega: bool) -> None:
            await transferencias_controller.processar_credito_remoto(
                corpo, app.state, reentrega
            )

        await mensageria.consumir(id_agencia, tratar_credito)
        print(f"[Agencia {id_agencia}] consumindo a fila fila-agencia-{id_agencia}", flush=True)
        yield
        await mensageria.fechar()

    app = FastAPI(
        title=f"ICEIBank - Agencia {id_agencia}",
        description=(
            "Sprint 2: API REST/MVC com relogio vetorial, mensageria via RabbitMQ, "
            "particionamento de contas e autenticacao JWT."
        ),
        version="2.0.0",
        lifespan=ciclo_de_vida,
    )

    # O frontend (Vite) roda em outra origem e precisa falar com as 3 agencias.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Estado do processo - equivalente ao app.locals do exemplo em Express.
    app.state.id_agencia = id_agencia
    app.state.relogio = RelogioVetorial(id_agencia, config.NUMERO_AGENCIAS)
    app.state.registro = RegistroEventos(f"agencia-{id_agencia}")
    app.state.contas = {}
    app.state.idempotencia = {}

    app.include_router(router)

    @app.exception_handler(500)
    async def erro_interno(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content={"erro": "Erro interno da agencia."})

    return app


if not config.RABBITMQ_URL:
    print(
        "Defina RABBITMQ_URL (no arquivo agencia/.env ou no terminal) com a URL AMQP "
        "do seu broker antes de iniciar. Ex.: amqps://usuario:senha@host/vhost",
        file=sys.stderr,
    )
    sys.exit(1)

_id_agencia = int(os.getenv("AGENCIA_ID", "0"))
if not any(a["id"] == _id_agencia for a in config.AGENCIAS):
    print(f"Agencia {_id_agencia} nao configurada em config.py", file=sys.stderr)
    sys.exit(1)

app = criar_app(_id_agencia)


if __name__ == "__main__":
    import uvicorn

    porta = config.PORTA_BASE + _id_agencia
    print(f"[Agencia {_id_agencia}] ouvindo na porta {porta}", flush=True)
    # Um unico worker: o estado das contas e o relogio vivem na memoria do processo.
    uvicorn.run(app, host="0.0.0.0", port=porta, workers=1, log_level="warning")
