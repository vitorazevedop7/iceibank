# ICEIBank

Banco simplificado dividido em agencias, usado como projeto pratico da disciplina de
Sistemas Distribuidos (PUC Minas). O sistema evolui ao longo de 4 sprints no semestre,
cada um partindo do codigo do anterior.

| Sprint | Unidade | Tecnologia | Conceito de Sistemas Distribuidos |
|--------|---------|-----------|------------------------------------|
| 1 | U2 - Desenvolvimento Web | API REST / MVC | Relogio logico de Lamport |
| 2 (atual) | U3 - Comunicacao indireta | Mensageria / Pub-Sub | Relogio vetorial |
| 3 | U4 - Desenvolvimento Movel | App Flutter | Consenso (eleicao de lider) |
| 4 | U5 - Computacao em Nuvem | Containers | Transacoes distribuidas (2PC/Saga) |

Respostas as questoes e decisoes de design de cada sprint: [`RESPOSTAS.md`](RESPOSTAS.md).

## Video de apresentacao (Sprint 1)

**Link:** https://drive.google.com/file/d/1Dtzv3RyZx0dm33Ogu5a_OrFzn73XzvO4/view?usp=sharing

## Video de apresentacao (Sprint 2)

<!-- COLE AQUI O LINK DO VIDEO (YouTube nao listado ou Google Drive com acesso liberado) -->
**Link:** _(a preencher)_

## Arquitetura (Sprint 2)

Uma agencia e um servico REST independente. O mesmo codigo e executado 3 vezes com
identidades diferentes (`AGENCIA_ID=0|1|2`), formando 3 agencias. As contas sao
**particionadas** (nao replicadas) entre elas: a agencia responsavel por uma conta e
`id_conta % 3`.

No Sprint 2, a transferencia entre agencias deixou de ser uma chamada REST direta. A agencia
de origem debita localmente e **publica** o credito no RabbitMQ; a agencia de destino o
**consome** de forma assincrona, mesmo que estivesse fora do ar no momento da publicacao.

```
POST /transferencias (Agencia 0)
  ├─ debito local                  TRANSFERENCIA_DEBITO   [2,0,0]
  ├─ envio (regra 2)               TRANSFERENCIA_ENVIADA  [3,0,0]
  └─ publish  iceibank.eventos  --agencia.1.creditar-->  fila-agencia-1
                                                            │
                        Agencia 1 (consumidor no mesmo event loop do FastAPI)
                        └─ recebimento (regra 3)  TRANSFERENCIA_CREDITO_REMOTO [3,2,0]

Credito que falha duas vezes  --x-dead-letter-exchange-->  iceibank.mortas -> fila-mortas
```

Toda operacao e carimbada com o **relogio vetorial** (um contador por agencia) e registrada
em um arquivo de eventos por agencia. Comparando os vetores, o `mesclar_logs.py` separa os
pares de eventos causalmente relacionados dos comprovadamente concorrentes.

## Stack

- **Backend:** Python 3.12+ + FastAPI (escolha mantida do Sprint 1 ao Sprint 4)
- **Comunicacao entre agencias:** RabbitMQ (CloudAMQP, plano Little Lemur) via `aio-pika`
- **Relogio logico:** relogio vetorial
- **Autenticacao:** JWT (HS256)
- **Frontend:** Vite + React + TypeScript
- **Estado:** em memoria, por processo (sem banco de dados, por decisao do roteiro)

## Estrutura do repositorio

```
iceibank/
├── agencia/              # servico de agencia (executado 3x com AGENCIA_ID diferente)
│   ├── requirements.txt
│   ├── .env.example          # modelo do .env com a RABBITMQ_URL (o .env fica fora do Git)
│   ├── src/
│   │   ├── main.py           # cria o app, conecta ao RabbitMQ e sobe o consumidor
│   │   ├── config.py         # particionamento, JWT e RABBITMQ_URL
│   │   ├── routes.py         # declaracao das rotas
│   │   ├── models/           # entidade Conta e schemas Pydantic (inclui MensagemCredito)
│   │   ├── controllers/      # contas e transferencias (inclui o consumidor de creditos)
│   │   ├── services/         # relogio vetorial, registro de eventos e mensageria
│   │   └── auth/             # autenticacao JWT
│   ├── tests/                # testes do relogio vetorial
│   ├── data/                 # logs .jsonl gerados em execucao (fora do Git)
│   ├── mesclar_logs.py       # linha do tempo causal: pares concorrentes e causais
│   ├── mensagens_mortas.py   # inspeciona e reprocessa a fila-mortas
│   └── capturar-evidencias-sprint2.sh
├── frontend/             # interface web que consome a API autenticada
├── evidencias/sprint1/   # prints do Sprint 1
├── evidencias/sprint2/   # prints do Sprint 2
└── RESPOSTAS.md          # respostas as questoes e justificativas de design
```

## Como executar

### 1. RabbitMQ

Crie uma instancia gratis no [CloudAMQP](https://www.cloudamqp.com/) (plano **Little Lemur**,
que e RabbitMQ) e copie a **AMQP URL** do painel da instancia. Grave-a em `agencia/.env`:

```bash
cd agencia
cp .env.example .env      # e edite a linha RABBITMQ_URL
```

Alternativa local: `docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management` e
`RABBITMQ_URL=amqp://guest:guest@localhost:5672/`.

Nao e preciso criar exchange nem filas: cada agencia declara a topologia inteira ao subir.

### 2. Backend - as 3 agencias

```bash
cd agencia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Abra tres terminais:

```bash
# Terminal 1
cd agencia && source venv/bin/activate && AGENCIA_ID=0 python -m src.main
# Terminal 2
cd agencia && source venv/bin/activate && AGENCIA_ID=1 python -m src.main
# Terminal 3
cd agencia && source venv/bin/activate && AGENCIA_ID=2 python -m src.main
```

Cada agencia mostra `ouvindo na porta 400X` e `consumindo a fila fila-agencia-X`. Se precisar
de portas exclusivas (maquina compartilhada de laboratorio), defina `OFFSET` com os dois
ultimos digitos da matricula: `OFFSET=42 AGENCIA_ID=0 python -m src.main`.

Documentacao interativa da API (gerada pelo FastAPI): <http://localhost:4000/docs>

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre em <http://localhost:5173>. O seletor "porta de entrada" no topo escolhe com qual
das 3 agencias a tela vai falar.

### Usuarios de teste

| Usuario | Senha | Contas | Agencia de cada conta |
|---------|-------|--------|------------------------|
| `ana`   | `senha123` | 0, 3 | Agencia 0, Agencia 0 |
| `bruno` | `senha123` | 1, 4 | Agencia 1, Agencia 1 |
| `carla` | `senha123` | 2, 5 | Agencia 2, Agencia 2 |

### Linha do tempo causal

Depois de gerar operacoes, lista os eventos das 3 agencias, os pares concorrentes e o par
causal envio -> credito de cada transferencia:

```bash
cd agencia && python mesclar_logs.py          # ate 20 pares concorrentes
cd agencia && python mesclar_logs.py --todos  # todos
```

### Fila de mensagens mortas (funcionalidade adicional)

```bash
cd agencia && python mensagens_mortas.py                # lista, sem remover
cd agencia && python mensagens_mortas.py --reprocessar  # devolve para a fila de origem
```

### Testes do relogio vetorial

```bash
cd agencia && python -m pytest tests/ -v
```

### Evidencias automaticas (macOS)

`agencia/capturar-evidencias-sprint2.sh` sobe as agencias, executa o cenario e tira o print
da tela inteira em `evidencias/sprint2/`, com a data visivel:

```bash
cd agencia && source venv/bin/activate
./capturar-evidencias-sprint2.sh resiliencia      # resiliencia-fila.png
./capturar-evidencias-sprint2.sh linha-do-tempo   # linha-do-tempo-causal.png
./capturar-evidencias-sprint2.sh dead-letter      # funcionalidade-adicional.png
```

`agencia/demonstracao.sh` e `agencia/capturar-evidencias.sh` sao os roteiros do Sprint 1 e
foram mantidos como historico (ainda usam a rota `creditar-remoto`, que nao existe mais).

## Endpoints

| Metodo | Rota | Protecao | Descricao |
|--------|------|----------|-----------|
| POST | `/auth/login` | publica | Autentica e devolve o JWT |
| POST | `/contas` | token de usuario | Cria conta (recusa conta de outra agencia) |
| GET | `/contas/{id}` | token de usuario | Consulta saldo |
| POST | `/contas/{id}/depositar` | token de usuario | Deposito |
| POST | `/contas/{id}/sacar` | token de usuario | Saque |
| POST | `/transferencias` | token de usuario | Local, ou publicacao no RabbitMQ se o destino for outra agencia. Aceita `Idempotency-Key` |
| GET | `/status` | publica | Identidade da agencia, relogio vetorial atual e contas sob sua guarda |

A rota interna `/contas/{id}/creditar-remoto` do Sprint 1 foi removida: o credito remoto
agora chega pela fila.

## Limitacoes conhecidas (intencionais neste sprint)

- **Resposta 200 = publicada, nao creditada.** O credito entre agencias e aplicado de forma
  assincrona; a origem nao recebe confirmacao.
- **Estado em memoria.** Se a agencia de destino reiniciar, as contas somem; a mensagem chega
  mas nao encontra a conta. Com a dead-letter, o credito fica na `fila-mortas` para ser
  reprocessado, mas o debito na origem nao e desfeito automaticamente. Garantir atomicidade
  entre as agencias e o objetivo do Sprint 4 (2PC ou Saga).
