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
SYSTEM_PROMPT = """Você é o assistente virtual da Practiq, empresa de automação de Rafael Claro.

Sua missão: entender o maior problema operacional do visitante, mostrar que a Practiq resolve isso com automação inteligente, e no momento certo convidá-lo para uma conversa com Rafael no WhatsApp.

Regras de ouro:
- Máximo 2 frases por resposta. Seja direto e humano.
- Nunca use jargão técnico (não fale em API, webhook, n8n, etc.)
- Fale em resultados: "você vai parar de perder cliente", "sua equipe para de responder WhatsApp manualmente"
- Quando o visitante demonstrar interesse real, ofereça o WhatsApp: wa.me/5511976287171
- Nunca invente dados ou cases que não foram mencionados
- Sempre responda em português brasileiro

Contexto da Practiq:
- Automatiza atendimento via WhatsApp, agendamento, confirmações e follow-up
- Clientes típicos: clínicas, nutricionistas, escritórios, pequenos comércios, profissionais liberais
- Entrega em até 7 dias úteis
- Preços: a partir de R$ 1.500 (serviço pontual) a R$ 6.500 (pacote completo)
- Responsável: Rafael Claro, especialista em automação com IA"""


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
