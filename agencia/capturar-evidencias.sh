#!/usr/bin/env bash
# Captura automatica das evidencias do backend (macOS).
#
# Sobe as 3 agencias, executa todos os cenarios do roteiro e tira os prints
# sozinho, com a data visivel na tela. Voce so precisa nao mexer no computador
# enquanto ele roda (cerca de 2 minutos).
#
# Uso:
#   cd iceibank/agencia
#   source venv/bin/activate
#   ./capturar-evidencias.sh
#
# Gera em ../evidencias/sprint1/:
#   auth-sem-token.png  auth-com-token.png  auth-token-expirado.png
#   transferencia-local.png  transferencia-entre-agencias.png
#   funcionalidade-adicional.png  falha-conhecida.png  linha-do-tempo.png

set -u

if ! command -v screencapture > /dev/null; then
  echo "ERRO: 'screencapture' nao encontrado. Este script e para macOS."
  echo "Em outro sistema, use ./demonstracao.sh e capture os prints manualmente."
  exit 1
fi

EVID="../evidencias/sprint1"
LOGS="$(pwd)/.logs-execucao"
PORTA_BASE=$((4000 + ${OFFSET:-0}))
A0="http://localhost:$PORTA_BASE"
A1="http://localhost:$((PORTA_BASE + 1))"
A2="http://localhost:$((PORTA_BASE + 2))"

mkdir -p "$EVID" "$LOGS"

azul()  { printf '\n\033[1;34m%s\033[0m\n' "$1"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$1"; }
ama()   { printf '\033[0;33m%s\033[0m\n' "$1"; }

etapa() {
  clear
  azul "=================================================================="
  azul " ICEIBank - Sprint 1 | $1"
  printf '   '; date
  azul "=================================================================="
}

# Captura a tela inteira depois de dar tempo do terminal renderizar.
capturar() {
  sleep 1.2
  screencapture -x "$EVID/$1"
  verde ">> evidencia salva: evidencias/sprint1/$1"
  sleep 0.8
}

logs_das_agencias() {
  for id in $@; do
    printf '\n\033[1;36m--- log da Agencia %s ---\033[0m\n' "$id"
    tail -n "${LINHAS:-4}" "$LOGS/agencia-$id.log" 2>/dev/null | grep -v "^\[Agencia"
  done
}

subir_agencia() {
  AGENCIA_ID=$1 OFFSET=${OFFSET:-0} nohup python -m src.main \
    > "$LOGS/agencia-$1.log" 2>&1 &
  echo $! > "$LOGS/agencia-$1.pid"
}

derrubar_agencia() {
  if [ -f "$LOGS/agencia-$1.pid" ]; then
    kill -9 "$(cat "$LOGS/agencia-$1.pid")" 2>/dev/null
    rm -f "$LOGS/agencia-$1.pid"
  fi
}

derrubar_tudo() { for id in 0 1 2; do derrubar_agencia $id; done; }
trap derrubar_tudo EXIT

token_de() {
  curl -s -X POST "$2/auth/login" -H 'Content-Type: application/json' \
    -d "{\"usuario\":\"$1\",\"senha\":\"senha123\"}" \
    | python -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
}

# ==========================================================================
clear
azul "=================================================================="
azul " Captura automatica das evidencias do ICEIBank - Sprint 1"
azul "=================================================================="
echo
ama "O script vai tirar 8 prints da TELA INTEIRA nos proximos ~2 minutos."
ama "Deixe esta janela do terminal visivel e nao mexa no computador."
echo
read -r -p "Enter para comecar (Ctrl+C para cancelar) " _

derrubar_tudo
rm -f data/*.jsonl
sleep 1
for id in 0 1 2; do subir_agencia $id; done
sleep 4

# --------------------------------------------------------------------------
etapa "Parte F - autenticacao: requisicao SEM token"
echo "As 3 agencias no ar:"
for p in $PORTA_BASE $((PORTA_BASE+1)) $((PORTA_BASE+2)); do
  printf '  porta %s -> ' "$p"; curl -s --max-time 2 "http://localhost:$p/status"; echo
done
echo
echo "\$ curl $A0/contas/0        (sem cabecalho Authorization)"
curl -s -w '\n  [HTTP %{http_code}]\n' "$A0/contas/0"
capturar "auth-sem-token.png"

# --------------------------------------------------------------------------
TA=$(token_de ana "$A0")
TB=$(token_de bruno "$A1")
TC=$(token_de carla "$A2")

etapa "Parte F - autenticacao: requisicao COM token valido"
echo "\$ POST $A0/auth/login   usuario=ana"
echo "  token recebido: ${TA:0:55}..."
echo
echo "\$ POST $A0/contas   -H 'Authorization: Bearer <token>'"
curl -s -X POST "$A0/contas" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"id":0,"nomeAluno":"Ana","saldoInicial":100}' -w '\n  [HTTP %{http_code}]\n'
echo
echo "\$ GET $A0/contas/0   -H 'Authorization: Bearer <token>'"
curl -s "$A0/contas/0" -H "Authorization: Bearer $TA" -w '\n  [HTTP %{http_code}]\n'
capturar "auth-com-token.png"

# --------------------------------------------------------------------------
etapa "Parte F - autenticacao: token EXPIRADO"
EXPIRADO=$(python gerar_token_expirado.py)
echo "Token gerado ja vencido (exp 15 minutos no passado):"
echo "  ${EXPIRADO:0:55}..."
echo
echo "\$ GET $A0/contas/0   -H 'Authorization: Bearer <token expirado>'"
curl -s "$A0/contas/0" -H "Authorization: Bearer $EXPIRADO" -w '\n  [HTTP %{http_code}]\n'
capturar "auth-token-expirado.png"

# --------------------------------------------------------------------------
# contas restantes, sem print
curl -s -o /dev/null -X POST "$A0/contas" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' -d '{"id":3,"nomeAluno":"Ana (2a conta)","saldoInicial":50}'
curl -s -o /dev/null -X POST "$A1/contas" -H "Authorization: Bearer $TB" \
  -H 'Content-Type: application/json' -d '{"id":1,"nomeAluno":"Bruno","saldoInicial":50}'
curl -s -o /dev/null -X POST "$A2/contas" -H "Authorization: Bearer $TC" \
  -H 'Content-Type: application/json' -d '{"id":2,"nomeAluno":"Carla","saldoInicial":80}'

etapa "Parte D - TRANSFERENCIA LOCAL (conta 0 -> conta 3, ambas na Agencia 0)"
echo "\$ POST $A0/transferencias  {\"idOrigem\":0,\"idDestino\":3,\"valor\":20}"
curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"idOrigem":0,"idDestino":3,"valor":20}'; echo
echo
echo "saldos apos a operacao:"
printf '  origem  : '; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
printf '  destino : '; curl -s "$A0/contas/3" -H "Authorization: Bearer $TA"; echo
LINHAS=2 logs_das_agencias 0
echo
ama "Dois eventos LOCAIS consecutivos na mesma agencia - sem ao_enviar/ao_receber,"
ama "porque nao houve mensagem entre processos."
capturar "transferencia-local.png"

# --------------------------------------------------------------------------
etapa "Parte D - TRANSFERENCIA ENTRE AGENCIAS (conta 0 na Ag0 -> conta 1 na Ag1)"
echo "\$ POST $A0/transferencias  {\"idOrigem\":0,\"idDestino\":1,\"valor\":30}"
curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"idOrigem":0,"idDestino":1,"valor":30}'; echo
echo
echo "saldos nas DUAS agencias:"
printf '  origem  (Ag0): '; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
printf '  destino (Ag1): '; curl -s "$A1/contas/1" -H "Authorization: Bearer $TB"; echo
LINHAS=2 logs_das_agencias 0 1
echo
ama "Regra 2 na origem (ao_enviar anexa o timestamp) e regra 3 no destino"
ama "(ao_receber aplica max(local, recebido) + 1)."
capturar "transferencia-entre-agencias.png"

# --------------------------------------------------------------------------
etapa "Funcionalidade adicional - IDEMPOTENCIA de transferencias"
CHAVE="transf-$(date +%s)"
echo "Mesma transferencia de R\$ 10,00 enviada 3x com Idempotency-Key: $CHAVE"
echo
for n in 1 2 3; do
  printf '  envio %s: ' "$n"
  curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -H "Idempotency-Key: $CHAVE" \
    -d '{"idOrigem":0,"idDestino":1,"valor":10}'; echo
done
echo
echo "saldos (debitou/creditou uma unica vez, nao tres):"
printf '  origem  : '; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
printf '  destino : '; curl -s "$A1/contas/1" -H "Authorization: Bearer $TB"; echo
LINHAS=3 logs_das_agencias 0
capturar "funcionalidade-adicional.png"

# --------------------------------------------------------------------------
etapa "Parte D - FALHA CONHECIDA (agencia de destino fora do ar)"
echo "Derrubando a Agencia 1..."
derrubar_agencia 1
sleep 2
printf '  Agencia 1 responde? '; curl -s --max-time 2 "$A1/status" || echo "NAO - fora do ar"
echo
printf 'saldo da conta 0 ANTES : '; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
echo
echo "\$ POST $A0/transferencias  {\"idOrigem\":0,\"idDestino\":1,\"valor\":25}"
curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"idOrigem":0,"idDestino":1,"valor":25}' -w '\n  [HTTP %{http_code}]\n'
echo
printf 'saldo da conta 0 DEPOIS: '; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
ama "O debito NAO foi revertido - o dinheiro sumiu. Inconsistencia registrada no log:"
grep TRANSFERENCIA_FALHOU data/eventos-agencia-0.jsonl | tail -1 | python -m json.tool
capturar "falha-conhecida.png"

# --------------------------------------------------------------------------
subir_agencia 1
sleep 4
TB=$(token_de bruno "$A1")
curl -s -o /dev/null -X POST "$A1/contas" -H "Authorization: Bearer $TB" \
  -H 'Content-Type: application/json' -d '{"id":1,"nomeAluno":"Bruno","saldoInicial":50}'

# eventos concorrentes nas 3 agencias, para forcar empates de timestamp
for n in 1 2 3 4 5; do
  curl -s -o /dev/null -X POST "$A0/contas/0/depositar" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -d '{"valor":5}' &
  P1=$!
  curl -s -o /dev/null -X POST "$A1/contas/1/depositar" -H "Authorization: Bearer $TB" \
    -H 'Content-Type: application/json' -d '{"valor":5}' &
  P2=$!
  curl -s -o /dev/null -X POST "$A2/contas/2/depositar" -H "Authorization: Bearer $TC" \
    -H 'Content-Type: application/json' -d '{"valor":5}' &
  P3=$!
  wait $P1 $P2 $P3
done
curl -s -o /dev/null -X POST "$A2/transferencias" -H "Authorization: Bearer $TC" \
  -H 'Content-Type: application/json' -d '{"idOrigem":2,"idDestino":1,"valor":15}'

etapa "Parte E - LINHA DO TEMPO UNIFICADA das 3 agencias"
python mesclar_logs.py | tail -n 34
capturar "linha-do-tempo.png"

# --------------------------------------------------------------------------
clear
azul "=================================================================="
verde " Captura concluida."
printf '   '; date
azul "=================================================================="
echo
ls -1 "$EVID"/*.png 2>/dev/null | sed 's|.*/|  |'
echo
ama "Faltam os 3 prints do frontend (frontend-login, frontend-transferencia,"
ama "frontend-erro). Veja o ENTREGA.md."
echo
echo "A saida completa da linha do tempo esta em: $LOGS/"
python mesclar_logs.py > "$LOGS/linha-do-tempo-completa.txt" 2>/dev/null
