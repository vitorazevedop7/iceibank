#!/usr/bin/env bash
# Roteiro de demonstracao do ICEIBank - Sprint 1.
#
# Executa a sequencia completa de cenarios do roteiro, pausando nos pontos onde
# uma evidencia precisa ser capturada. A data e impressa em cada etapa para
# comprovar que a execucao e recente.
#
# Uso:  ./demonstracao.sh          (com pausas para print)
#       PAUSA=0 ./demonstracao.sh  (sem pausas, so para conferir se tudo passa)
#       LIMPAR=1 ./demonstracao.sh (apaga os logs antigos antes de comecar)
#
# Antes de capturar evidencias, prefira comecar limpo: LIMPAR=1 ./demonstracao.sh
# e reinicie as 3 agencias quando o script pedir.

set -u

CHAVE_IDEMP="transf-demo-$(date +%s)"

A0=http://localhost:4000
A1=http://localhost:4001
A2=http://localhost:4002

azul()  { printf '\n\033[1;34m%s\033[0m\n' "$1"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$1"; }
ama()   { printf '\033[0;33m%s\033[0m\n' "$1"; }

pausa() {
  if [ "${PAUSA:-1}" = "1" ]; then
    ama ">>> CAPTURE A EVIDENCIA: $1"
    read -r -p "    (enter para continuar) " _
  fi
}

etapa() {
  azul "=============================================================="
  azul " $1"
  printf '   '; date
  azul "=============================================================="
}

token_de() {
  curl -s -X POST "$2/auth/login" -H 'Content-Type: application/json' \
    -d "{\"usuario\":\"$1\",\"senha\":\"senha123\"}" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
}

json() { python3 -m json.tool 2>/dev/null || cat; }

# --------------------------------------------------------------------------
if [ "${LIMPAR:-0}" = "1" ]; then
  rm -f data/*.jsonl
  verde "Logs anteriores apagados (data/*.jsonl)."
  ama "Reinicie as 3 agencias AGORA para zerar tambem os relogios e as contas,"
  ama "senao a linha do tempo vai misturar execucoes diferentes."
  if [ "${PAUSA:-1}" = "1" ]; then read -r -p "    (enter quando as 3 agencias estiverem reiniciadas) " _; fi
fi

etapa "0. Agencias no ar"
for p in 4000 4001 4002; do
  printf 'porta %s -> ' "$p"
  curl -s --max-time 2 "http://localhost:$p/status" || echo "FORA DO AR"
  echo
done

# --------------------------------------------------------------------------
etapa "1. Autenticacao - login das tres pessoas"
TA=$(token_de ana "$A0")
TB=$(token_de bruno "$A1")
TC=$(token_de carla "$A2")
verde "tokens emitidos (ana / bruno / carla)"
echo "token da ana (truncado): ${TA:0:60}..."

echo
echo "> requisicao SEM token (esperado 401):"
curl -s -w '   [HTTP %{http_code}]\n' "$A0/contas/0"
pausa "evidencias/sprint1/auth-sem-token.png"

echo
echo "> requisicao COM token valido (esperado 200):"
curl -s -w '   [HTTP %{http_code}]\n' "$A0/status"
curl -s -X POST "$A0/contas" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"id":0,"nomeAluno":"Ana","saldoInicial":100}' -w '   [HTTP %{http_code}]\n'
pausa "evidencias/sprint1/auth-com-token.png"

echo
echo "> requisicao com token EXPIRADO (esperado 401):"
EXPIRADO=$(python gerar_token_expirado.py)
curl -s -w '   [HTTP %{http_code}]\n' "$A0/contas/0" -H "Authorization: Bearer $EXPIRADO"
pausa "evidencias/sprint1/auth-token-expirado.png"

# --------------------------------------------------------------------------
etapa "2. Particionamento de contas (id % 3)"
curl -s -X POST "$A0/contas" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"id":3,"nomeAluno":"Ana (2a conta)","saldoInicial":50}' -w '  [HTTP %{http_code}]\n'
curl -s -X POST "$A1/contas" -H "Authorization: Bearer $TB" \
  -H 'Content-Type: application/json' \
  -d '{"id":1,"nomeAluno":"Bruno","saldoInicial":50}' -w '  [HTTP %{http_code}]\n'
curl -s -X POST "$A2/contas" -H "Authorization: Bearer $TC" \
  -H 'Content-Type: application/json' \
  -d '{"id":2,"nomeAluno":"Carla","saldoInicial":80}' -w '  [HTTP %{http_code}]\n'

echo
echo "> tentando criar a conta 1 na Agencia 0 (nao e dela - esperado 400):"
curl -s -X POST "$A0/contas" -H "Authorization: Bearer $TB" \
  -H 'Content-Type: application/json' \
  -d '{"id":1,"nomeAluno":"Bruno","saldoInicial":50}' -w '\n  [HTTP %{http_code}]\n'

echo
echo "> autorizacao: ana tentando consultar a conta 1, que e do bruno (esperado 403):"
curl -s -w '\n  [HTTP %{http_code}]\n' "$A1/contas/1" -H "Authorization: Bearer $TA"

# --------------------------------------------------------------------------
etapa "3. Deposito e saque (cada operacao carimbada com Lamport)"
curl -s -X POST "$A0/contas/0/depositar" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' -d '{"valor":25}'; echo
curl -s -X POST "$A0/contas/0/sacar" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' -d '{"valor":15}'; echo
echo "> saque acima do saldo (esperado 400):"
curl -s -X POST "$A0/contas/0/sacar" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' -d '{"valor":999999}'; echo

# --------------------------------------------------------------------------
etapa "4. TRANSFERENCIA LOCAL - conta 0 para conta 3 (ambas na Agencia 0)"
curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"idOrigem":0,"idDestino":3,"valor":20}'; echo
echo "saldos depois:"
curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
curl -s "$A0/contas/3" -H "Authorization: Bearer $TA"; echo
ama "Observe o log da Agencia 0: dois eventos locais consecutivos (DEBITO e CREDITO),"
ama "sem ao_enviar/ao_receber - nao houve mensagem entre processos."
pausa "evidencias/sprint1/transferencia-local.png"

# --------------------------------------------------------------------------
etapa "5. TRANSFERENCIA ENTRE AGENCIAS - conta 0 (Ag0) para conta 1 (Ag1)"
curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"idOrigem":0,"idDestino":1,"valor":30}'; echo
echo "saldo da origem (Agencia 0):"; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
echo "saldo do destino (Agencia 1):"; curl -s "$A1/contas/1" -H "Authorization: Bearer $TB"; echo
ama "Observe os DOIS terminais: a Ag0 registra ao_enviar e a Ag1 aplica max(local, recebido)+1."
pausa "evidencias/sprint1/transferencia-entre-agencias.png (inclua os logs das DUAS agencias)"

# --------------------------------------------------------------------------
etapa "6. FUNCIONALIDADE ADICIONAL - idempotencia de transferencias"
echo "> mesma transferencia de R\$ 10,00 enviada 3 vezes com a mesma Idempotency-Key:"
for n in 1 2 3; do
  printf '  envio %s: ' "$n"
  curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
    -H 'Content-Type: application/json' -H "Idempotency-Key: $CHAVE_IDEMP" \
    -d '{"idOrigem":0,"idDestino":1,"valor":10}'; echo
done
echo
echo "saldo da origem (debitou 10 uma unica vez, nao 30):"
curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
echo "saldo do destino (creditou 10 uma unica vez):"
curl -s "$A1/contas/1" -H "Authorization: Bearer $TB"; echo
pausa "evidencias/sprint1/funcionalidade-adicional.png"

# --------------------------------------------------------------------------
etapa "7. FALHA CONHECIDA - agencia de destino fora do ar"
if [ "${PAUSA:-1}" != "1" ]; then
  ama "Etapa pulada: derrubar a Agencia 1 exige acao manual (rode sem PAUSA=0)."
else
  ama "ACAO NECESSARIA: derrube o terminal da Agencia 1 agora (Ctrl+C nele)."
  read -r -p "    (enter quando a Agencia 1 estiver derrubada) " _
fi
if [ "${PAUSA:-1}" = "1" ]; then
echo
echo "saldo da conta 0 ANTES:"; curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
echo
echo "> transferindo 25 da conta 0 para a conta 1 (agencia fora do ar):"
curl -s -X POST "$A0/transferencias" -H "Authorization: Bearer $TA" \
  -H 'Content-Type: application/json' \
  -d '{"idOrigem":0,"idDestino":1,"valor":25}' -w '\n  [HTTP %{http_code}]\n'
echo
echo "saldo da conta 0 DEPOIS (o debito NAO foi revertido):"
curl -s "$A0/contas/0" -H "Authorization: Bearer $TA"; echo
echo
echo "evento de inconsistencia registrado no log da Agencia 0:"
grep TRANSFERENCIA_FALHOU data/eventos-agencia-0.jsonl | tail -1 | json
pausa "evidencias/sprint1/falha-conhecida.png"
fi

# --------------------------------------------------------------------------
etapa "8. LINHA DO TEMPO UNIFICADA"
ama "Suba a Agencia 1 de novo e gere operacoes simultaneas nas 3 agencias antes"
ama "de rodar o script, para aumentar a chance de empates de timestamp."
echo
python mesclar_logs.py
pausa "evidencias/sprint1/linha-do-tempo.png"

azul "=============================================================="
verde " Demonstracao concluida."
printf '   '; date
azul "=============================================================="
