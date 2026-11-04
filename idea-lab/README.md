# 🧪 Idea Lab

Mandas una nota de voz a un bot de Telegram → se transcribe, se clasifica con IA y
aparece como nota en tu vault de Obsidian. Todo con servicios gratuitos.

```
Voz en Telegram → Groq Whisper → Groq LLM → Ideas/<categoria>/Idea.md → respuesta en Telegram
```

## Puesta en marcha (10 min)

1. **Bot de Telegram**: habla con [@BotFather](https://t.me/BotFather), `/newbot`, copia el token.
2. **Clave de Groq** (gratis): <https://console.groq.com/keys>
3. En tu VPS:
   ```bash
   cd idea-lab
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   cp .env.example .env      # rellena TELEGRAM_TOKEN, GROQ_API_KEY y VAULT_PATH
   .venv/bin/python bot.py
   ```
4. Escribe cualquier cosa al bot: te dirá tu **ID de usuario**. Ponlo en `ALLOWED_USER_ID`
   del `.env` y reinicia. Así el bot solo te obedece a ti.
5. Manda una nota de voz. Debe responder `✅ 📱 Apps · …` y crearse la nota.

### Dejarlo siempre encendido
```bash
sudo cp idea-lab.service /etc/systemd/system/   # ajusta rutas y User
sudo systemctl enable --now idea-lab
```

### Llevar las notas a Obsidian
`VAULT_PATH` debe ser una carpeta que llegue a tu vault. Gratis: **Syncthing**
(VPS ⇄ PC/móvil) o un repo Git privado con el plugin *Obsidian Git*.

## Qué crea
```
Ideas/
├── 📱 Apps/  🧰 Herramientas y SaaS/  🛍️ Productos/
├── 💼 Negocios/  🎬 Contenido y Marca/  🧪 Experimentos/
├── 📥 Inbox/        ← lo que la IA no tiene claro (o si falla la IA)
├── 🗄️ Archivo/      ← tú mueves aquí lo descartado/empezado
├── _Config/contexto.md   ← TU perfil: editalo, la IA lo usa para puntuar el "encaje"
└── 🏠 Panel.md      ← vista rápida (necesita el plugin Dataview)
```
Cada idea es una nota de ~10 líneas con propiedades (`potencial`, `esfuerzo`, `encaje`,
`prioridad = potencial × encaje ÷ esfuerzo`, `estado`, `tags`…).

## Extras incluidos
- **Nunca pierde una idea**: si falla la IA, se guarda el texto en Inbox.
- **Aviso de duplicados**: si se parece a una ya guardada, lo dice y la enlaza (`[[…]]`).
- **Confianza baja → Inbox** para que la revises tú.
- **`/top`** en Telegram devuelve tus 5 mejores ideas.
- También vale texto o reenviar mensajes, no solo voz.

## Ciclo de vida
Cambia `estado` a mano en la nota: `sin-desarrollar` → `validando` → `empezada`/`descartada`
(y muévela a `🗄️ Archivo/`). El Panel solo muestra `sin-desarrollar`.

## Ajustes
Variables opcionales en `.env`: `LLM_MODEL` (por defecto `llama-3.3-70b-versatile`) y
`WHISPER_MODEL` (`whisper-large-v3-turbo`). Para cambiar categorías edita `CATEGORIAS`
en `bot.py`.
