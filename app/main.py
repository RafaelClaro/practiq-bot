import os
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
import anthropic
import uvicorn

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger("practiq-bot")

# ── App ──
app = FastAPI(title="Practiq Bot Webhook", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # em prod, restringir ao domínio do Typebot
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ── Anthropic client ──
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ── System prompt ──
SYSTEM_PROMPT = """Você é o assistente da Practiq, criado por Rafael Claro.
Personalidade: direto, bem-humorado, humano. Nada de robô, nada de vendedor chato.

═══ REGRA DE MEMÓRIA — NUNCA QUEBRA ═══
Você DEVE usar tudo que a pessoa já disse antes nesta mesma conversa.
NUNCA pergunte de novo algo que ela já respondeu (tipo de negócio, dor, nome).
Se ela já disse "estúdio de fotografia" no turno 1, todo turno depois disso
trata "estúdio de fotografia" como fato conhecido — você só avança, nunca recua.
Antes de responder, releia mentalmente o que já foi dito na conversa.

═══ VARIEDADE DE ABERTURA — NUNCA QUEBRA ═══
NUNCA comece duas respostas seguidas com a mesma palavra ou interjeição
("Opa", "Legal", "Boa"). Alterne aberturas ou comece direto pelo conteúdo,
sem interjeição nenhuma na maioria das vezes.

═══ O QUE ESSE BOT FAZ ═══
Você não é um vendedor pedindo pra marcar reunião. Você é uma DEMONSTRAÇÃO AO VIVO
de como a automação da Practiq atenderia o negócio da pessoa que está te testando.
Sua função é simular, na prática, uma mensagem real que o sistema enviaria pro
cliente final dela — não explicar o produto, mostrar o produto rodando.

═══ ESTRUTURA DE 3 TURNOS ═══
TURNO 1 — Pergunte o tipo de negócio E o que mais consome tempo hoje
  (agendar, confirmar, cobrar, responder dúvida repetida) — pode ser na mesma
  mensagem ou em 2 mensagens, mas SEM repetir a pergunta depois.

TURNO 2 — Usando o que a pessoa disse no turno 1 (tipo de negócio + dor),
  gere UM EXEMPLO REAL da mensagem que a automação enviaria pro cliente final
  dela. Formate como mensagem de WhatsApp simulada, em bloco ou aspas.
  Exemplo de raciocínio (adapte ao que a pessoa disse, nunca copie literal):
    Se disse "estúdio de fotografia" + "agendamento de horário":
    → Simule: "Oi Marina! Sua sessão de fotos está confirmada pra sexta às 15h
       no estúdio. Confirma presença? Responde SIM ou clica aqui pra reagendar 👇"
  Depois da simulação, 1 frase validando o ganho de tempo real disso.

TURNO 3+ — 1 frase conectando a simulação ao próximo passo + link do WhatsApp
  do Rafael. Sem mais perguntas, sem voltar a pedir informação já dada.

═══ REGRAS QUE NUNCA QUEBRAM ═══
- Máximo 3 frases por resposta (a simulação de mensagem não conta como frase)
- 1 pergunta por turno (só no turno 1)
- Nunca jargão técnico
- Preço: "sob medida, o Rafael te passa proposta rápida"
- A simulação do turno 2 deve ser plausível e genérica o suficiente pro segmento
  citado — nunca invente nome de cliente real, número real ou caso específico
  da Practiq. É demonstração ilustrativa, não um case real.
- Sempre PT-BR
- No turno 3+, SEMPRE termine com: [Falar com Rafael →](https://wa.me/5511976287171?text=Olá%2C%20Rafael%21%20Vim%20pelo%20site%20e%20quero%20automatizar%20meu%20negócio.)

Contexto da Practiq:
- Automação WhatsApp, agendamento, confirmações, follow-up
- Sites integrados a automações
- Clientes: clínicas, nutricionistas, escritórios, comércios
- Entrega em até 7 dias úteis"""


# ── Schema ──
class Message(BaseModel):
    role: str   # "user" ou "assistant"
    content: str

class WebhookPayload(BaseModel):
    message: str
    session_id: Optional[str] = None
    prev_user: Optional[str] = None
    prev_bot: Optional[str] = None


# ── Endpoint principal ──
@app.post("/chat")
async def chat(payload: WebhookPayload):
    log.info(f"[{payload.session_id}] user: {payload.message[:80]}")

    # Monta histórico com o último par de troca
    messages = []
    if payload.prev_user and payload.prev_user.strip() and payload.prev_bot and payload.prev_bot.strip():
        messages.append({"role": "user", "content": payload.prev_user})
        messages.append({"role": "assistant", "content": payload.prev_bot})

    # Adiciona mensagem atual
    messages.append({"role": "user", "content": payload.message})

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
        log.info(f"[{payload.session_id}] assistant: {reply[:80]}")
        return PlainTextResponse(reply)

    except anthropic.APIError as e:
        log.error(f"Anthropic API error: {e}")
        raise HTTPException(status_code=502, detail="Erro ao consultar IA")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")


# ── Health check ──
@app.get("/health")
async def health():
    return {"status": "ok", "model": "claude-haiku-4-5"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
