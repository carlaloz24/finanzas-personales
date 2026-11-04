#!/usr/bin/env python3
"""Idea Lab: bot de Telegram que convierte una nota de voz en una idea
clasificada dentro de tu vault de Obsidian.

Flujo: audio/texto -> transcripcion (Groq Whisper) -> clasificacion (Groq LLM)
       -> nota .md en Ideas/<categoria>/ -> respuesta en Telegram.

Solo necesita `requests`. Todo configurable por variables de entorno (.env).
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

# --------------------------------------------------------------------------- #
# Configuracion
# --------------------------------------------------------------------------- #

def load_env(path: Path) -> None:
    """Mini lector de .env (evita depender de python-dotenv)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env(Path(__file__).with_name(".env"))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "0") or 0)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "./vault")).expanduser()
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "whisper-large-v3-turbo")
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

GROQ_URL = "https://api.groq.com/openai/v1"
TG_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TG_FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}"

IDEAS_DIR = VAULT_PATH / "Ideas"

# Categoria -> carpeta (una idea va en UNA sola carpeta; el resto, en tags).
CATEGORIAS = {
    "Apps": "📱 Apps",
    "Herramientas y SaaS": "🧰 Herramientas y SaaS",
    "Productos": "🛍️ Productos",
    "Negocios": "💼 Negocios",
    "Contenido y Marca": "🎬 Contenido y Marca",
    "Experimentos": "🧪 Experimentos",
}
INBOX = "📥 Inbox"
MIN_CONFIANZA = 3  # por debajo de esto la idea va a Inbox

CATEGORIA_AYUDA = {
    "Apps": "app movil o web con usuarios",
    "Herramientas y SaaS": "software, extension, automatizacion, bot, API",
    "Productos": "producto fisico, plantilla, kit, infoproducto",
    "Negocios": "servicio, agencia, marketplace, modelo de negocio",
    "Contenido y Marca": "canal, newsletter, comunidad, curso, marca personal",
    "Experimentos": "algo pequeno que se prueba en un fin de semana",
}

CONTEXTO_POR_DEFECTO = """# Contexto para la IA (editalo a tu gusto)

Quien soy: desarrollador/a y creador/a con varios proyectos en paralelo.
Habilidades: programacion, diseno de producto, automatizacion.
Infraestructura: tengo un VPS propio y un design system propio.
Intereses (areas): finanzas personales, productividad, IA, herramientas para creadores.
Audiencia: hispanohablante, redes sociales en crecimiento.
Preferencias: me interesan ideas que pueda lanzar rapido, con coste bajo y recurrentes.
"""

PANEL = """# 🏠 Panel de ideas

> Requiere el plugin gratuito **Dataview** (Ajustes > Plugins de la comunidad).

## 🔥 Top 10 por prioridad
```dataview
TABLE categoria AS Categoria, potencial AS Pot, esfuerzo AS Esf, encaje AS Encaje, prioridad AS Prio
FROM "Ideas"
WHERE estado = "sin-desarrollar"
SORT prioridad DESC
LIMIT 10
```

## ⚡ Quick wins (poco esfuerzo, buen potencial)
```dataview
TABLE categoria AS Categoria, potencial AS Pot, esfuerzo AS Esf, resumen AS Resumen
FROM "Ideas"
WHERE estado = "sin-desarrollar" AND esfuerzo <= 2 AND potencial >= 3
SORT prioridad DESC
```

## 🆕 Ultimas anadidas
```dataview
TABLE categoria AS Categoria, potencial AS Pot, esfuerzo AS Esf, fecha AS Fecha
FROM "Ideas"
WHERE estado = "sin-desarrollar" OR estado = "sin-clasificar"
SORT fecha DESC
LIMIT 10
```

## 📥 Pendientes de revisar (Inbox)
```dataview
LIST resumen
FROM "Ideas/📥 Inbox"
SORT fecha DESC
```

## 🗂️ Por categoria
```dataview
TABLE WITHOUT ID categoria AS Categoria, length(rows) AS Ideas, round(sum(rows.prioridad) / length(rows), 1) AS "Prio media"
FROM "Ideas"
WHERE estado = "sin-desarrollar"
GROUP BY categoria
```

## 💀 Zona de descarte (potencial bajo)
```dataview
TABLE categoria AS Categoria, potencial AS Pot, esfuerzo AS Esf
FROM "Ideas"
WHERE estado = "sin-desarrollar" AND potencial <= 2
SORT potencial ASC
```
"""

# --------------------------------------------------------------------------- #
# Vault
# --------------------------------------------------------------------------- #

def init_vault() -> None:
    """Crea carpetas, contexto y panel si no existen."""
    for folder in list(CATEGORIAS.values()) + [INBOX, "🗄️ Archivo", "_Config"]:
        (IDEAS_DIR / folder).mkdir(parents=True, exist_ok=True)
    ctx = IDEAS_DIR / "_Config" / "contexto.md"
    if not ctx.exists():
        ctx.write_text(CONTEXTO_POR_DEFECTO, encoding="utf-8")
    panel = IDEAS_DIR / "🏠 Panel.md"
    if not panel.exists():
        panel.write_text(PANEL, encoding="utf-8")


def read_context() -> str:
    try:
        return (IDEAS_DIR / "_Config" / "contexto.md").read_text(encoding="utf-8")
    except OSError:
        return CONTEXTO_POR_DEFECTO


def existing_titles(limit: int = 200) -> list[str]:
    """Titulos ya guardados (para avisar de duplicados)."""
    notes = [p for p in IDEAS_DIR.rglob("*.md")
             if "_Config" not in p.parts and p.name != "🏠 Panel.md"]
    notes.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.stem for p in notes[:limit]]


def safe_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|#^\[\]]', "", title).strip().strip(".")
    name = re.sub(r"\s+", " ", name)[:80].strip()
    return name or "Idea sin titulo"


def unique_path(folder: Path, name: str) -> Path:
    path = folder / f"{name}.md"
    n = 2
    while path.exists():
        path = folder / f"{name} ({n}).md"
        n += 1
    return path


def yaml_str(value) -> str:
    # JSON es YAML valido para strings y listas.
    return json.dumps(value, ensure_ascii=False)


def clamp(value, default=3) -> int:
    try:
        return max(1, min(5, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def build_note(data: dict, transcript: str) -> tuple[Path, str]:
    """Devuelve (ruta, contenido) de la nota segun la clasificacion."""
    categoria = data.get("categoria")
    confianza = clamp(data.get("confianza"), 3)
    if categoria not in CATEGORIAS or confianza < MIN_CONFIANZA:
        folder = INBOX
        estado = "sin-clasificar"
    else:
        folder = CATEGORIAS[categoria]
        estado = "sin-desarrollar"

    potencial = clamp(data.get("potencial"))
    esfuerzo = clamp(data.get("esfuerzo"))
    encaje = clamp(data.get("encaje"))
    prioridad = round(potencial * encaje / esfuerzo, 1)
    titulo = str(data.get("titulo") or "Idea sin titulo").strip()
    resumen = str(data.get("resumen") or "").strip()
    tags = [re.sub(r"\s+", "-", str(t).strip().lstrip("#").strip().lower())
            for t in (data.get("tags") or []) if str(t).strip().lstrip("#").strip()][:5]

    front = [
        "---",
        f"categoria: {yaml_str(categoria if categoria in CATEGORIAS else 'Sin clasificar')}",
        f"area: {yaml_str(str(data.get('area') or '').lower())}",
        f"potencial: {potencial}",
        f"esfuerzo: {esfuerzo}",
        f"encaje: {encaje}",
        f"prioridad: {prioridad}",
        f"estado: {estado}",
        f"fecha: {date.today().isoformat()}",
        f"resumen: {yaml_str(resumen)}",
        f"tags: {yaml_str(tags)}",
        "---",
    ]
    similar = str(data.get("parecida_a") or "").strip()
    body = [
        f"# {titulo}",
        "",
        f"**En una linea:** {resumen}",
        "",
        f"**Problema:** {data.get('problema') or '-'}",
        f"**Para quien:** {data.get('publico') or '-'}",
        f"**Como ganaria dinero:** {data.get('monetizacion') or '-'}",
        f"**Siguiente paso:** {data.get('siguiente_paso') or '-'}",
        "",
        f"**Valoracion:** {data.get('justificacion') or '-'}",
    ]
    if similar:
        body += ["", f"⚠️ **Se parece a:** [[{similar}]]"]
    body += ["", f"> 🎙️ Original: \"{transcript.strip()}\""]

    path = unique_path(IDEAS_DIR / folder, safe_filename(titulo))
    return path, "\n".join(front + [""] + body) + "\n"


def save_raw(transcript: str) -> Path:
    """Red de seguridad: si la IA falla, la idea NO se pierde."""
    titulo = "Sin clasificar " + time.strftime("%Y-%m-%d %H-%M-%S")
    content = (
        "---\ncategoria: \"Sin clasificar\"\nestado: sin-clasificar\n"
        f"fecha: {date.today().isoformat()}\nresumen: \"(pendiente de clasificar)\"\n"
        "potencial: 1\nesfuerzo: 3\nprioridad: 0\ntags: []\n---\n"
        f"# {titulo}\n\n> 🎙️ Original: \"{transcript.strip()}\"\n"
    )
    path = unique_path(IDEAS_DIR / INBOX, safe_filename(titulo))
    path.write_text(content, encoding="utf-8")
    return path

# --------------------------------------------------------------------------- #
# IA (Groq)
# --------------------------------------------------------------------------- #

def groq_headers() -> dict:
    return {"Authorization": f"Bearer {GROQ_API_KEY}"}


def transcribe(audio: bytes, filename: str) -> str:
    r = requests.post(
        f"{GROQ_URL}/audio/transcriptions",
        headers=groq_headers(),
        files={"file": (filename, audio)},
        data={"model": WHISPER_MODEL, "language": "es", "response_format": "json"},
        timeout=120,
    )
    r.raise_for_status()
    return r.json().get("text", "").strip()


def system_prompt() -> str:
    cats = "\n".join(f"- {k}: {v}" for k, v in CATEGORIA_AYUDA.items())
    return f"""Eres un analista de ideas de negocio y producto, directo y critico.
Recibes una idea hablada (puede estar desordenada o incompleta). Devuelve SOLO un JSON con:

titulo: corto y claro (max 8 palabras)
resumen: una linea
categoria: UNA de estas (texto exacto):
{cats}
area: tema en 1-2 palabras (finanzas, IA, salud, educacion...)
potencial: 1-5 (tamano de mercado + dolor real del problema + facilidad de monetizar)
esfuerzo: 1-5 (1 = un fin de semana, 5 = meses de trabajo)
encaje: 1-5 (cuanto encaja con el perfil, habilidades e infraestructura del usuario)
confianza: 1-5 (seguridad al elegir la categoria; baja si la idea es vaga)
problema: que problema resuelve (1 frase)
publico: para quien (1 frase)
monetizacion: como ganaria dinero (1 frase)
siguiente_paso: la accion MAS pequena para validarla (1 frase)
justificacion: por que esas puntuaciones (1-2 frases)
tags: lista de 2-5 palabras clave en minusculas
parecida_a: titulo EXACTO de una idea ya guardada si es muy parecida, si no, ""

Reglas:
- Se critico. No des 4-5 de potencial salvo que haya un problema claro y gente dispuesta a pagar.
- Si la idea es vaga, puntua bajo y dilo en la justificacion.
- Escribe en espanol.

Contexto del usuario:
{read_context()}"""


def classify(transcript: str) -> dict:
    titles = existing_titles()
    user = f"IDEA:\n{transcript}\n\nIDEAS YA GUARDADAS (para detectar duplicados):\n" + (
        "\n".join(f"- {t}" for t in titles) if titles else "(ninguna)")
    r = requests.post(
        f"{GROQ_URL}/chat/completions",
        headers=groq_headers(),
        json={
            "model": LLM_MODEL,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": user},
            ],
        },
        timeout=120,
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])

# --------------------------------------------------------------------------- #
# Telegram
# --------------------------------------------------------------------------- #

def tg(method: str, **params):
    r = requests.post(f"{TG_URL}/{method}", json=params, timeout=70)
    r.raise_for_status()
    return r.json()["result"]


def reply(chat_id: int, text: str) -> None:
    tg("sendMessage", chat_id=chat_id, text=text, disable_web_page_preview=True)


def download(file_id: str) -> tuple[bytes, str]:
    info = tg("getFile", file_id=file_id)
    r = requests.get(f"{TG_FILE_URL}/{info['file_path']}", timeout=120)
    r.raise_for_status()
    return r.content, Path(info["file_path"]).name


def top_ideas(n: int = 5) -> str:
    rows = []
    for p in IDEAS_DIR.rglob("*.md"):
        if "_Config" in p.parts:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "estado: sin-desarrollar" not in text:
            continue
        m = re.search(r"^prioridad: ([\d.]+)", text, re.M)
        if m:
            rows.append((float(m.group(1)), p.stem, p.parent.name))
    rows.sort(reverse=True)
    if not rows:
        return "Aun no hay ideas guardadas."
    return "🔥 Tus mejores ideas:\n" + "\n".join(
        f"{i}. {t} ({c}) · prio {pr}" for i, (pr, t, c) in enumerate(rows[:n], 1))


# --------------------------------------------------------------------------- #
# Consultar ideas desde Telegram: lista, detalle y acciones
# --------------------------------------------------------------------------- #

ARCHIVO = "🗄️ Archivo"
PAGE = 8
# (etiqueta del boton, carpeta). None = todas las activas.
FILTROS = [("Todas", None)] + [(v.split(" ", 1)[0], v) for v in CATEGORIAS.values()] + [
    ("📥", INBOX), ("🗄️", ARCHIVO)]
QUERY: dict[int, str] = {}  # ultima busqueda por chat


def norm(text: str) -> str:
    text = text.lower().strip().lstrip("/").rstrip(".!?¡¿ ")
    for a, b in zip("áéíóúü", "aeiouu"):
        text = text.replace(a, b)
    return re.sub(r"@\w+$", "", text).strip()


def parse_note(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        return None
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        try:
            v = json.loads(v)
        except ValueError:
            pass
        meta[k.strip()] = v
    rel = str(path.relative_to(IDEAS_DIR))
    meta.update(path=path, folder=path.parent.name, titulo=path.stem, body=m.group(2).strip(),
                id=hashlib.sha1(rel.encode()).hexdigest()[:8])
    return meta


def all_ideas() -> list[dict]:
    out = []
    for p in IDEAS_DIR.rglob("*.md"):
        if "_Config" in p.parts or p.name.startswith("🏠"):
            continue
        n = parse_note(p)
        if n:
            out.append(n)
    return out


def filter_ideas(cat: int, query: str) -> list[dict]:
    folder = FILTROS[cat][1]
    ideas = all_ideas()
    if folder:
        ideas = [i for i in ideas if i["folder"] == folder]
    else:  # "Todas" = activas (sin archivo)
        ideas = [i for i in ideas if i["folder"] != ARCHIVO]
    if query:
        words = norm(query).split()
        def hay(i):
            blob = norm(" ".join([i["titulo"], str(i.get("resumen", "")),
                                  " ".join(i.get("tags") or []), str(i.get("area", ""))]))
            return all(w in blob for w in words)
        ideas = [i for i in ideas if hay(i)]
    ideas.sort(key=lambda i: float(i.get("prioridad") or 0), reverse=True)
    return ideas


def list_view(chat_id: int, cat: int = 0, page: int = 0) -> tuple[str, dict]:
    query = QUERY.get(chat_id, "")
    ideas = filter_ideas(cat, query)
    pages = max(1, -(-len(ideas) // PAGE))
    page = max(0, min(page, pages - 1))
    head = f"💡 Tus ideas ({len(ideas)})"
    if query:
        head += f" · busqueda: “{query}”"
    if not ideas:
        head += "\n\nNo hay nada aqui todavia."
    rows = [[{"text": f"{'⭐' if float(i.get('prioridad') or 0) >= 6 else '•'} {i['titulo'][:40]} · P{i.get('potencial', '?')} E{i.get('esfuerzo', '?')}",
              "callback_data": f"d:{i['id']}:{cat}:{page}"}]
            for i in ideas[page * PAGE:(page + 1) * PAGE]]
    if pages > 1:
        rows.append([
            {"text": "◀", "callback_data": f"l:{cat}:{max(0, page - 1)}"},
            {"text": f"{page + 1}/{pages}", "callback_data": "noop"},
            {"text": "▶", "callback_data": f"l:{cat}:{min(pages - 1, page + 1)}"}])
    rows.append([{"text": ("• " if i == cat else "") + label, "callback_data": f"l:{i}:0"}
                 for i, (label, _) in enumerate(FILTROS)])
    return head, {"inline_keyboard": rows}


def detail_view(idea_id: str, cat: int, page: int) -> tuple[str, dict]:
    idea = next((i for i in all_ideas() if i["id"] == idea_id), None)
    if not idea:
        return "No encuentro esa idea (¿la moviste o borraste?).", {
            "inline_keyboard": [[{"text": "⬅️ Volver", "callback_data": f"l:{cat}:{page}"}]]}
    body = re.sub(r"^# .*\n+", "", idea["body"])
    text = (f"{idea['folder']}\n{idea['titulo']}\n"
            f"Estado: {idea.get('estado', '?')} · Potencial {idea.get('potencial')}/5 · "
            f"Esfuerzo {idea.get('esfuerzo')}/5 · Encaje {idea.get('encaje')}/5 · Prio {idea.get('prioridad')}\n\n"
            f"{body}")[:3900]
    base = f"a:{idea_id}"
    if idea["folder"] == ARCHIVO:
        acciones = [{"text": "♻️ Reactivar", "callback_data": f"{base}:r:{cat}:{page}"}]
    else:
        acciones = [{"text": "🔍 Validando", "callback_data": f"{base}:v:{cat}:{page}"},
                    {"text": "🚀 Empezada", "callback_data": f"{base}:e:{cat}:{page}"},
                    {"text": "🗑️ Descartar", "callback_data": f"{base}:d:{cat}:{page}"}]
    return text, {"inline_keyboard": [acciones, [{"text": "⬅️ Volver", "callback_data": f"l:{cat}:{page}"}]]}


def apply_action(idea_id: str, action: str) -> str:
    idea = next((i for i in all_ideas() if i["id"] == idea_id), None)
    if not idea:
        return "No encuentro esa idea."
    estado = {"v": "validando", "e": "empezada", "d": "descartada", "r": "sin-desarrollar"}[action]
    path: Path = idea["path"]
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^estado: .*$", f"estado: {estado}", text, count=1, flags=re.M)
    if action in ("e", "d"):
        dest = ARCHIVO
    elif action == "r":
        dest = CATEGORIAS.get(idea.get("categoria"), INBOX)
    else:
        dest = idea["folder"]
    new_path = path if dest == idea["folder"] else unique_path(IDEAS_DIR / dest, path.stem)
    path.write_text(text, encoding="utf-8")
    if new_path != path:
        path.rename(new_path)
    return f"Hecho: {idea['titulo']} → {estado}"


def send_list(chat_id: int, query: str = "") -> None:
    QUERY[chat_id] = query
    text, kb = list_view(chat_id)
    tg("sendMessage", chat_id=chat_id, text=text, reply_markup=kb)


def edit(cq: dict, text: str, kb: dict) -> None:
    try:
        tg("editMessageText", chat_id=cq["message"]["chat"]["id"],
           message_id=cq["message"]["message_id"], text=text, reply_markup=kb)
    except requests.HTTPError as exc:  # "message is not modified" no es un error real
        print("edit:", exc, file=sys.stderr)


def handle_callback(cq: dict) -> None:
    if ALLOWED_USER_ID and cq["from"]["id"] != ALLOWED_USER_ID:
        return
    chat_id = cq["message"]["chat"]["id"]
    parts = cq.get("data", "").split(":")
    toast = None
    if parts[0] == "l":  # lista: l:cat:page
        edit(cq, *list_view(chat_id, int(parts[1]), int(parts[2])))
    elif parts[0] == "d":  # detalle: d:id:cat:page
        edit(cq, *detail_view(parts[1], int(parts[2]), int(parts[3])))
    elif parts[0] == "a":  # accion: a:id:accion:cat:page
        toast = apply_action(parts[1], parts[2])
        edit(cq, *list_view(chat_id, int(parts[3]), int(parts[4])))
    tg("answerCallbackQuery", callback_query_id=cq["id"], **({"text": toast} if toast else {}))


def process_idea(chat_id: int, transcript: str) -> None:
    try:
        data = classify(transcript)
        path, content = build_note(data, transcript)
        path.write_text(content, encoding="utf-8")
    except Exception as exc:  # la idea no se pierde nunca
        print("Error clasificando:", exc, file=sys.stderr)
        path = save_raw(transcript)
        reply(chat_id, f"⚠️ No pude clasificarla, pero la guarde en Inbox:\n“{transcript[:200]}”")
        return

    folder = path.parent.name
    fm = content.split("---")[1]
    get = lambda k: (re.search(rf"^{k}: (.*)$", fm, re.M) or [None, "?"])[1]
    msg = (f"✅ {folder}\n{path.stem}\n"
           f"Potencial {get('potencial')}/5 · Esfuerzo {get('esfuerzo')}/5 · Prio {get('prioridad')}")
    if "sin-clasificar" in fm:
        msg += "\n📥 Confianza baja: revisala en Inbox."
    similar = str(data.get("parecida_a") or "").strip()
    if similar:
        msg += f"\n⚠️ Se parece a: {similar}"
    reply(chat_id, msg)


LISTA_VOZ = {"ideas", "mis ideas", "lista de ideas", "ver ideas", "dame las ideas", "muestrame las ideas"}


def handle(update: dict) -> None:
    if update.get("callback_query"):
        handle_callback(update["callback_query"])
        return
    msg = update.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    user_id = (msg.get("from") or {}).get("id")
    if not chat_id:
        return
    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        return  # ignora a cualquiera que no seas tu
    if not ALLOWED_USER_ID:
        reply(chat_id, f"Tu ID de usuario es {user_id}. Ponlo en ALLOWED_USER_ID del .env y reinicia el bot.")
        return

    text = (msg.get("text") or "").strip()
    n = norm(text)
    if n == "ideas" or n in LISTA_VOZ or n.startswith("ideas "):
        send_list(chat_id, n[len("ideas"):].strip() if n.startswith("ideas ") else "")
        return
    if text.startswith("/start") or text.startswith("/ayuda"):
        reply(chat_id, "🎙️ Mandame una nota de voz (o texto) con tu idea y la guardo clasificada en Obsidian.\n\n💡 /ideas → lista con botones (toca una para ver el detalle)\n🔎 /ideas palabra → buscar\n🔥 /top → tus 5 mejores")
        return
    if text.startswith("/top"):
        reply(chat_id, top_ideas())
        return

    media = msg.get("voice") or msg.get("audio") or msg.get("video_note")
    if media:
        try:
            audio, name = download(media["file_id"])
            transcript = transcribe(audio, name)
        except Exception as exc:
            print("Error transcribiendo:", exc, file=sys.stderr)
            reply(chat_id, "⚠️ No pude transcribir el audio. Intentalo de nuevo o mandamelo en texto.")
            return
        if not transcript:
            reply(chat_id, "No he entendido nada en el audio 🤔 Prueba otra vez.")
            return
    elif text:
        transcript = text
    else:
        return

    if norm(transcript) in LISTA_VOZ:  # dijiste "ideas" por voz
        send_list(chat_id)
        return
    process_idea(chat_id, transcript)


def main() -> None:
    missing = [k for k, v in {"TELEGRAM_TOKEN": TELEGRAM_TOKEN, "GROQ_API_KEY": GROQ_API_KEY}.items() if not v]
    if missing:
        sys.exit(f"Faltan variables en .env: {', '.join(missing)}")
    init_vault()
    print(f"Idea Lab listo. Vault: {VAULT_PATH}")
    offset = None
    while True:
        try:
            updates = tg("getUpdates", offset=offset, timeout=50)
        except Exception as exc:
            print("Error de red:", exc, file=sys.stderr)
            time.sleep(5)
            continue
        for upd in updates:
            offset = upd["update_id"] + 1
            try:
                handle(upd)
            except Exception as exc:
                print("Error procesando update:", exc, file=sys.stderr)


if __name__ == "__main__":
    main()
