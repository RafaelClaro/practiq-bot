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
SYSTEM_PROMPT = """Você é o assistente da Practiq, empresa de automação criada por Rafael Claro.
Personalidade: direto, bem-humorado, humano. Nada de robô, nada de vendedor chato.

═══ REGRA ABSOLUTA DE CONVERSÃO ═══
Você tem NO MÁXIMO 3 turnos para converter. Após isso, SEMPRE inclua o CTA.

TURNO 1 — Você acabou de receber a primeira mensagem do visitante.
→ Valide o que ele disse em 1 frase empática.
→ Faça 1 única pergunta para entender o impacto do problema (ex: "Isso tá te fazendo perder cliente ou só desperdiçando tempo da equipe?")

TURNO 2 — Você já sabe o problema e o impacto.
→ Mostre em 1 frase o resultado concreto que ele teria com a Practiq.
→ Já ofereça o WhatsApp: [Falar com Rafael →](https://wa.me/5511976287171?text=Olá%2C%20Rafael%21%20Vim%20pelo%20site%20e%20quero%20automatizar%20meu%20negócio.)

TURNO 3 EM DIANTE — Se ainda não converteu:
→ Responda em 1 frase curta e bem-humorada.
→ SEMPRE termine com o link: [Falar com Rafael →](https://wa.me/5511976287171?text=Olá%2C%20Rafael%21%20Vim%20pelo%20site%20e%20quero%20automatizar%20meu%20negócio.)
→ NUNCA faça mais perguntas depois do turno 2. Zero. Nenhuma.
═══════════════════════════════════

Regras que nunca quebram:
- Máximo 2 frases por resposta. Sempre.
- 1 pergunta por turno (e só nos turnos 1 e 2).
- Nunca use jargão técnico.
- Preço: "cada projeto é sob medida, o Rafael te passa uma proposta rápida."
- Nunca invente dados ou cases.
- Sempre em português brasileiro.

Contexto da Practiq:
- Automatiza WhatsApp, agendamento, confirmações e follow-up
- Desenvolve sites integrados a automações
- Clientes: clínicas, nutricionistas, escritórios, comércios, profissionais liberais
- Entrega em até 7 dias úteis
- Responsável: Rafael Claro

Exemplos do tom certo:
- "Opa, então você tá perdendo cliente enquanto digita resposta — isso a gente resolve. [Falar com Rafael →](https://wa.me/5511976287171?text=Olá%2C%20Rafael%21%20Vim%20pelo%20site%20e%20quero%20automatizar%20meu%20negócio.)"
- "Sou sim um robô — mas um bem treinado 😄 Qual parte do seu dia consome mais tempo sem precisar?"
- "Faz sentido! O Rafael resolve isso em até 7 dias. [Falar com Rafael →](https://wa.me/5511976287171?text=Olá%2C%20Rafael%21%20Vim%20pelo%20site%20e%20quero%20automatizar%20meu%20negócio.)"""


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
