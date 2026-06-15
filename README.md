# Practiq Bot — Webhook Claude Haiku + Typebot

Bot de qualificação de leads com IA real (Claude Haiku) integrado ao Typebot.
O visitante do site conversa com o Haiku — que atua como consultor de pré-venda da Practiq.

---

## Arquitetura

```
Visitante → Typebot (interface) → Webhook (FastAPI) → Claude Haiku API → resposta
```

---

## Setup local

### 1. Clonar e instalar dependências

```bash
cd practiq-bot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env e colocar sua ANTHROPIC_API_KEY
```

### 3. Rodar localmente

```bash
uvicorn app.main:app --reload
# Servidor em http://localhost:8000
```

### 4. Testar o endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "oi, quero saber mais sobre automação", "history": [], "session_id": "teste-1"}'
```

### 5. Rodar testes

```bash
pytest tests/ -v --tb=short
```

---

## Deploy no Railway (gratuito)

1. Crie conta em [railway.app](https://railway.app)
2. New Project → Deploy from GitHub (ou arrastar a pasta)
3. Em **Variables**, adicione: `ANTHROPIC_API_KEY=sua-chave`
4. Railway detecta o `Procfile` e sobe automaticamente
5. Copie a URL gerada (ex: `https://practiq-bot.up.railway.app`)

---

## Configuração do Typebot

### 1. Criar conta
Acesse [typebot.io](https://typebot.io) → criar conta gratuita

### 2. Criar novo bot
- New Typebot → Start from scratch
- Nome: "Practiq Demo Bot"

### 3. Estrutura do fluxo

```
[Start]
  ↓
[Text] "Olá! Sou o assistente da Practiq. Me conta: qual o maior problema operacional
        que você enfrenta hoje no seu negócio?"
  ↓
[User Input] → salvar em variável: {{user_message}}
  ↓
[HTTP Request] ← aqui chama o webhook
  ↓
[Text] exibe {{bot_reply}}
  ↓
[User Input] → salvar em {{user_message}}
  ↓
[HTTP Request] ← loop de conversa
  ↓
... (repetir até CTA)
```

### 4. Configurar o bloco HTTP Request

**Method:** POST
**URL:** `https://SEU-DOMINIO.up.railway.app/chat`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "message": "{{user_message}}",
  "session_id": "{{resultId}}",
  "history": []
}
```

> **Nota:** Para manter histórico entre turnos, use uma variável `{{history}}`
> acumulando as mensagens anteriores. No início é array vazio `[]`.

**Salvar resposta:**
- Response body path: `reply`
- Salvar em variável: `{{bot_reply}}`

### 5. Exibir resposta

Após o HTTP Request, adicione um bloco **Text**:
```
{{bot_reply}}
```

### 6. Embed no site

No Typebot: Share → Embed → Bubble (bolinha no canto) ou Popup

Cole o snippet gerado antes do `</body>` no `index.html`:

```html
<!-- Typebot -->
<script type="module">
  import Typebot from 'https://cdn.jsdelivr.net/npm/@typebot.io/js@0.3/dist/web.js'
  Typebot.initBubble({
    typebot: "SEU-TYPEBOT-ID",
    theme: {
      button: { backgroundColor: "#6EE7C7", iconColor: "#0D0F14" },
      chatWindow: { backgroundColor: "#0D0F14" }
    },
  });
</script>
```

---

## Histórico de conversa (avançado)

Para o Haiku manter contexto entre turnos, acumule o histórico no Typebot:

1. Criar variável `{{history}}` com valor inicial: `[]`
2. Após cada resposta, usar um bloco **Set Variable** para concatenar:
```
{{history}} + [{"role":"user","content":"{{user_message}}"},{"role":"assistant","content":"{{bot_reply}}"}]
```
3. Enviar `{{history}}` no body do HTTP Request

---

## Personalização do system prompt

Edite `SYSTEM_PROMPT` em `app/main.py` para ajustar:
- Tom de voz
- Serviços que menciona
- Quando oferece o WhatsApp
- Casos de uso que cita

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/chat` | Recebe mensagem, retorna resposta do Haiku |
| GET | `/health` | Health check |

---

## Custo estimado

Claude Haiku custa ~$0.25 por 1M tokens de input e ~$1.25 por 1M de output.
Uma conversa de 10 turnos com mensagens curtas = menos de $0.001 (menos de 1 centavo).
1.000 conversas no site = menos de R$ 5.

---

## Estrutura do projeto

```
practiq-bot/
├── app/
│   └── main.py          # FastAPI + webhook + system prompt
├── tests/
│   └── test_webhook.py  # Testes Pytest
├── .env.example
├── Procfile             # Deploy Railway
├── requirements.txt
└── README.md
```
