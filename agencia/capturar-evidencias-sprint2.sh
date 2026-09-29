#!/usr/bin/env bash
# Captura automatica das evidencias do Sprint 2 (macOS).
#
# Sobe as 3 agencias sozinho, executa o cenario pedido e tira o print da tela
# inteira, com a data visivel. Nao mexa no computador enquanto ele roda.
#
# Uso:
#   cd iceibank/agencia
#   source venv/bin/activate
#   ./capturar-evidencias-sprint2.sh resiliencia
#   ./capturar-evidencias-sprint2.sh linha-do-tempo
#
# Cenarios:
#   resiliencia     -> ../evidencias/sprint2/resiliencia-fila.png
#                      (Parte C, tarefa 3-4: Agencia 1 fora do ar, transferencia
#                       publicada mesmo assim, e o que acontece quando ela volta)
#   linha-do-tempo  -> ../evidencias/sprint2/linha-do-tempo-causal.png
#                      (Parte D: eventos independentes em agencias diferentes
#                       aparecem como concorrentes; o par envio -> credito de
#                       uma transferencia aparece como causal)
#
# Requer RABBITMQ_URL em agencia/.env (ou no terminal).

set -u

if ! command -v screencapture > /dev/null; then
  echo "ERRO: 'screencapture' nao encontrado. Este script e para macOS."
  exit 1
fi

CENARIO="${1:-}"
if [ -z "$CENARIO" ]; then
  echo "Uso: ./capturar-evidencias-sprint2.sh resiliencia|linha-do-tempo"
  exit 1
fi

EVID="../evidencias/sprint2"
LOGS="$(pwd)/.logs-execucao"
PORTA_BASE=$((4000 + ${OFFSET:-0}))
A0="http://localhost:$PORTA_BASE"
A1="http://localhost:$((PORTA_BASE + 1))"
A2="http://localhost:$((PORTA_BASE + 2))"

mkdir -p "$EVID" "$LOGS"

azul()  { printf '\n\033[1;34m%s\033[0m\n' "$1"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$1"; }
ama()   { printf '\033[0;33m%s\033[0m\n' "$1"; }
passo() { printf '\n\033[1;36m%s\033[0m\n' "$1"; }

etapa() {
  clear
  azul "=================================================================="
  azul " ICEIBank - Sprint 2 | $1"
  printf '   '; date
  azul "=================================================================="
}

capturar() {
  sleep 1.2
  screencapture -x "$EVID/$1"
  verde ">> evidencia salva: evidencias/sprint2/$1"
  sleep 0.8
}

subir_agencia() {
  AGENCIA_ID=$1 OFFSET=${OFFSET:-0} nohup python -m src.main \
    > "$LOGS/agencia-$1.log" 2>&1 &
  echo $! > "$LOGS/agencia-$1.pid"
  disown   # a queda forcada (kill -9, simulando crash) nao polui a tela com "Killed"
}

derrubar_agencia() {
  if [ -f "$LOGS/agencia-$1.pid" ]; then
    kill -9 "$(cat "$LOGS/agencia-$1.pid")" 2>/dev/null
    rm -f "$LOGS/agencia-$1.pid"
  fi
}

derrubar_tudo() { for id in 0 1 2; do derrubar_agencia $id; done; }
trap derrubar_tudo EXIT

esperar_agencia() {
  for _ in $(seq 1 30); do
    curl -s --max-time 1 "http://localhost:$((PORTA_BASE + $1))/status" > /dev/null && return 0
    sleep 0.5
  done
  echo "ERRO: Agencia $1 nao subiu. Veja $LOGS/agencia-$1.log"
  exit 1
}

token_de() {
  curl -s -X POST "$2/auth/login" -H 'Content-Type: application/json' \
    -d "{\"usuario\":\"$1\",\"senha\":\"senha123\"}" \
    | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
}

# Quantidade de mensagens paradas numa fila, perguntando ao proprio broker
# (declaracao passiva: so consulta, nao cria nem altera a fila).
mensagens_na_fila() {
  python - "$1" <<'EOF'
import asyncio, os, sys
import aio_pika
from dotenv import load_dotenv
load_dotenv(".env")
async def main():
    conexao = await aio_pika.connect(os.environ["RABBITMQ_URL"])
    async with conexao:
        canal = await conexao.channel()
        fila = await canal.declare_queue(sys.argv[1], passive=True)
        print(fila.declaration_result.message_count)
asyncio.run(main())
EOF
}

preparar() {
  clear
  azul "=================================================================="
  azul " Captura automatica das evidencias do ICEIBank - Sprint 2"
  azul "=================================================================="
  echo
  ama "As agencias que estiverem rodando serao encerradas; o script sobe as suas."
  ama "Deixe esta janela visivel e nao mexa no computador ate o fim."
  echo
  read -r -p "Enter para comecar (Ctrl+C para cancelar) " _

  pkill -f "python -m src.main" 2>/dev/null
  sleep 1
  rm -f data/*.jsonl
  for id in 0 1 2; do subir_agencia $id; done
  for id in 0 1 2; do esperar_agencia $id; done
  sleep 2   # tempo para cada agencia terminar de assinar a sua fila
}

# ==========================================================================
cenario_resiliencia() {
  TA=$(token_de ana "$A0")
  TB=$(token_de bruno "$A1")
  curl -s -o /dev/null -X POST "$A0/contas" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -d '{"id":0,"nomeAluno":"Ana","saldoInicial":100}'
  curl -s -o /dev/null -X POST "$A1/contas" -H "Authorization: Bearer $TB" \
    -H 'Content-Type: application/json' -d '{"id":1,"nomeAluno":"Bruno","saldoInicial":50}'

  derrubar_agencia 1
  sleep 1

  etapa "Parte C - resiliencia: destino FORA DO AR"
  echo "Conta 0 (Ana) na Agencia 0 e conta 1 (Bruno) na Agencia 1 ja criadas."
  passo "1) Agencia 1 derrubada. Ela responde?"
  printf '   $ curl %s/status  -> ' "$A1"
  curl -s --max-time 2 "$A1/status" || echo "sem resposta (fora do ar)"

  passo "2) Transferencia de R\$10 da conta 0 para a conta 1, com a Agencia 1 fora do ar"
  curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -d '{"idOrigem":0,"idDestino":1,"valor":10}' \
    -w '\n   [HTTP %{http_code}]\n' | sed 's/^/   /'
  sleep 1
  printf '   mensagens esperando na fila-agencia-1: '; mensagens_na_fila fila-agencia-1

  passo "3) Agencia 1 volta ao ar (processo novo: as contas em memoria se perderam)"
  subir_agencia 1
  esperar_agencia 1
  sleep 3
  echo "   log da Agencia 1 ao reconectar:"
  grep -v "ouvindo na porta" "$LOGS/agencia-1.log" | sed 's/^/     /'
  printf '   mensagens esperando na fila-agencia-1: '; mensagens_na_fila fila-agencia-1

  passo "4) A conta 1 ainda existe na Agencia 1?"
  curl -s "$A1/contas/1" -H "Authorization: Bearer $TB" -w '\n   [HTTP %{http_code}]\n' | sed 's/^/   /'
  echo
  ama "A mensagem NAO se perdeu (ficou na fila e foi entregue), mas a conta de destino"
  ama "sumiu com o reinicio - o credito foi registrado como CREDITO_REMOTO_FALHOU."
  capturar "resiliencia-fila.png"
}

# ==========================================================================
cenario_linha_do_tempo() {
  TA=$(token_de ana "$A0")
  TB=$(token_de bruno "$A1")
  TC=$(token_de carla "$A2")

  # 1) Eventos INDEPENDENTES: cada agencia cria a sua conta ao mesmo tempo, sem
  #    nenhuma mensagem trocada entre elas -> devem sair como concorrentes.
  curl -s -o /dev/null -X POST "$A0/contas" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -d '{"id":0,"nomeAluno":"Ana","saldoInicial":100}' &
  curl -s -o /dev/null -X POST "$A1/contas" -H "Authorization: Bearer $TB" \
    -H 'Content-Type: application/json' -d '{"id":1,"nomeAluno":"Bruno","saldoInicial":50}' &
  curl -s -o /dev/null -X POST "$A2/contas" -H "Authorization: Bearer $TC" \
    -H 'Content-Type: application/json' -d '{"id":2,"nomeAluno":"Carla","saldoInicial":80}' &
  wait

  # 2) Evento CAUSAL: transferencia da Agencia 0 para a Agencia 1 pela fila.
  curl -s -o /dev/null -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -d '{"idOrigem":0,"idDestino":1,"valor":30}'
  sleep 2

  # 3) Mais um evento independente na Agencia 2, que nao participou da transferencia.
  curl -s -o /dev/null -X POST "$A2/contas/2/depositar" -H "Authorization: Bearer $TC" \
    -H 'Content-Type: application/json' -d '{"valor":5}'

  etapa "Parte D - linha do tempo causal (relogio vetorial)"
  echo "Cenario: contas criadas em paralelo nas 3 agencias, transferencia 0 -> 1 pela"
  echo "fila e um deposito na Agencia 2. \$ python mesclar_logs.py"
  echo
  python mesclar_logs.py
  capturar "linha-do-tempo-causal.png"
}

case "$CENARIO" in
  resiliencia) preparar; cenario_resiliencia ;;
  linha-do-tempo) preparar; cenario_linha_do_tempo ;;
  *) echo "Cenario desconhecido: $CENARIO"; exit 1 ;;
esac

echo
verde "Concluido. As agencias abertas por este script serao encerradas agora."
