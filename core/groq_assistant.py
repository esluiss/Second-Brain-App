# core/groq_assistant.py – NeuroCore AI
#
# Módulo de asistente con IA (Groq) + búsqueda web (DuckDuckGo).
#
# IMPORTANTE SOBRE LOS 403:
#   - Groq y DuckDuckGo bloquean clientes sin cabeceras "de navegador".
#   - Por eso NO usamos urllib.request (que manda un User-Agent tipo
#     "Python-urllib/3.x" y suele terminar en 403), sino `requests`
#     con un User-Agent real y cabeceras completas.
#   - `urllib.parse` sí se usa (solo para decodificar URLs), eso no
#     tiene nada que ver con el bloqueo: es solo un parser de texto,
#     no hace peticiones de red.

from __future__ import annotations

import os
import re
import time
import html
import urllib.parse
import requests

# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════

# Orden de prioridad para la clave:
#   1) Variable de entorno GROQ_API_KEY
#   2) Config.GROQ_API_KEY (app/config.py) — RECOMENDADO: pon tu key ahí,
#      no edites este archivo.
#   3) Placeholder (falla con un mensaje claro si no la reemplazaste)
_PLACEHOLDER = "gsk_TU_CLAVE_AQUI"


def _resolver_api_key() -> str:
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        return env_key.strip()
    try:
        from app.config import Config
        cfg_key = getattr(Config, "GROQ_API_KEY", None)
        if cfg_key and cfg_key != _PLACEHOLDER:
            return cfg_key.strip()
    except Exception:
        pass
    return _PLACEHOLDER


GROQ_API_KEY = _resolver_api_key()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Modelo gratuito recomendado en Groq (llama-3.3-70b-versatile y
# llama-3.1-8b-instant fueron descontinuados en 2026). Puedes cambiarlo
# por cualquier otro modelo activo que veas en https://console.groq.com/docs/models
GROQ_MODEL = "openai/gpt-oss-120b"

# Cabeceras "de navegador" reales, para Groq y para DuckDuckGo.
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_HEADERS_WEB = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Referer": "https://duckduckgo.com/",
}

_TIMEOUT = 15  # segundos


# ═══════════════════════════════════════════════════════════════════════════
#  BÚSQUEDA WEB (DuckDuckGo, endpoint HTML sin JS)
# ═══════════════════════════════════════════════════════════════════════════
#
# POR QUÉ FALLABA A VECES (diagnóstico):
#   1) Se usaba `requests.post(...)` "en frío" cada vez, sin sesión ni
#      cookies. DuckDuckGo trata con más sospecha a un cliente que no
#      arrastra ninguna cookie previa, y a veces responde con una página
#      de "anomalía"/aviso de tráfico inusual en vez de resultados reales.
#      Como esa página SÍ es un 200 OK, el código no lo detectaba como
#      error: simplemente no encontraba matches y devolvía [] en silencio.
#   2) La regex exigía el atributo `class="result__a"` ANTES que `href`
#      dentro del mismo tag `<a>`. DuckDuckGo no garantiza ese orden de
#      atributos (varía entre respuestas), así que la regex a veces
#      simplemente no encontraba nada, aunque el HTML sí tuviera resultados
#      válidos.
#   3) No había reintentos: un único fallo (bloqueo temporal, timeout,
#      hiccup de red) terminaba directo en "no se encontraron fuentes".
#
# Esta versión corrige los tres puntos: sesión persistente con cookies,
# parseo de atributos sin asumir orden fijo, reintentos con backoff, y un
# endpoint de respaldo (DuckDuckGo "lite") si el principal sigue fallando.
# ═══════════════════════════════════════════════════════════════════════════

# Sesión persistente: reutilizar cookies entre búsquedas reduce bastante
# la tasa de bloqueos comparado con abrir una conexión nueva "en frío"
# en cada llamada.
_session = requests.Session()
_session.headers.update(_HEADERS_WEB)
_session._calentada = False  # se marca True tras la primera visita de "calentamiento"

# Fragmentos que aparecen en la página de "anomalía"/aviso de tráfico
# inusual que DDG sirve en vez de resultados cuando sospecha de un bot.
# Es un 200 OK normal, así que hay que detectarlo por contenido.
_MARCADORES_BLOQUEO = (
    "anomaly",
    "unusually high number of requests",
    "detected an unusual amount",
    "if this error persists",
    "problem while searching",
)


def _pagina_es_bloqueo(texto_html: str) -> bool:
    texto_l = texto_html.lower()
    return any(marcador in texto_l for marcador in _MARCADORES_BLOQUEO)


def _limpiar(fragmento_html: str) -> str:
    texto = re.sub(r"<[^>]+>", "", fragmento_html)  # quita tags internos (<b>, etc.)
    texto = html.unescape(texto)                     # decodifica &amp;, &#x27;, etc.
    return re.sub(r"\s+", " ", texto).strip()


def _url_real(href: str) -> str:
    """DDG redirige a través de /l/?uddg=<url-encoded>. Extraemos la real."""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    if "uddg" in qs and qs["uddg"]:
        return urllib.parse.unquote(qs["uddg"][0])
    return href


def _extraer_resultados(html_texto: str, max_resultados: int) -> list[dict]:
    """
    Extrae resultados analizando cada tag <a> por separado (en vez de una
    única regex rígida que exige un orden fijo de atributos). Así funciona
    tanto con el HTML del endpoint "html" como con variantes del endpoint
    "lite", y no se rompe si DDG cambia el orden href/class de un día para
    otro.
    """
    resultados = []
    vistos = set()

    for tag in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html_texto, re.IGNORECASE | re.DOTALL):
        attrs, contenido = tag.group(1), tag.group(2)

        href_match = re.search(r'href="([^"]*)"', attrs)
        if not href_match:
            continue

        clase_match = re.search(r'class="([^"]*)"', attrs)
        clases = clase_match.group(1).split() if clase_match else []
        es_resultado = "result__a" in clases or "result-link" in clases
        if not es_resultado:
            continue

        titulo = _limpiar(contenido)
        url_final = _url_real(href_match.group(1))
        if not titulo or not url_final or not url_final.startswith("http"):
            continue

        dominio = urllib.parse.urlparse(url_final).netloc.lower()
        # Descartamos redirects propios de DDG sin resolver, anuncios o
        # dominios vacíos, y evitamos duplicados.
        if not dominio or "duckduckgo.com" in dominio or url_final in vistos:
            continue
        vistos.add(url_final)

        # El resumen suele estar en un bloque "result__snippet" (o
        # "result-snippet" en la versión lite) justo después del enlace.
        resto = html_texto[tag.end():tag.end() + 2000]
        snip_match = re.search(
            r'class="[^"]*result(?:__|-)snippet[^"]*"[^>]*>(.*?)</(?:a|td|span|div)>',
            resto, re.IGNORECASE | re.DOTALL,
        )
        snippet = _limpiar(snip_match.group(1)) if snip_match else ""

        resultados.append({"titulo": titulo, "url": url_final, "resumen": snippet})
        if len(resultados) >= max_resultados:
            break

    return resultados


def _obtener_html_ddg(query: str, endpoint_url: str, intentos: int = 2) -> str:
    """Hace la petición a un endpoint de DDG con reintentos y backoff.
    Devuelve "" si tras varios intentos no se consiguió una página útil
    (sea por error de red o por página de bloqueo/anomalía)."""
    for intento in range(intentos):
        try:
            resp = _session.post(endpoint_url, data={"q": query}, timeout=_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[groq_assistant] Intento {intento + 1} falló en {endpoint_url}: {e}")
            time.sleep(1.0 * (intento + 1))
            continue

        if _pagina_es_bloqueo(resp.text):
            print(f"[groq_assistant] DDG devolvió página de bloqueo/anomalía "
                  f"(intento {intento + 1} en {endpoint_url}), reintentando...")
            time.sleep(1.3 * (intento + 1))
            continue

        return resp.text

    return ""


def _buscar_duckduckgo(query: str, max_resultados: int = 5) -> list[dict]:
    """
    Busca `query` en DuckDuckGo. Primero intenta el endpoint "html"
    completo (https://html.duckduckgo.com/html/) y, si no consigue
    resultados utilizables tras varios reintentos, cae al endpoint "lite"
    (https://lite.duckduckgo.com/lite/) como respaldo antes de rendirse.

    Devuelve una lista de dicts: [{"titulo": str, "url": str, "resumen": str}, ...]
    Si todo falla (red, bloqueo persistente, cambio de HTML) devuelve una
    lista vacía en lugar de lanzar una excepción, para que la app no se caiga.
    """
    if not query or not query.strip():
        return []

    query = query.strip()

    # "Calentar" la sesión con una visita normal antes de la primera
    # búsqueda de la ejecución ayuda a que DDG no la trate como bot.
    if not _session._calentada:
        try:
            _session.get("https://duckduckgo.com/", timeout=_TIMEOUT)
        except requests.RequestException:
            pass
        _session._calentada = True

    for endpoint_url in ("https://html.duckduckgo.com/html/", "https://lite.duckduckgo.com/lite/"):
        html_texto = _obtener_html_ddg(query, endpoint_url)
        if not html_texto:
            continue
        resultados = _extraer_resultados(html_texto, max_resultados)
        if resultados:
            return resultados

    print("[groq_assistant] No se pudieron obtener resultados de DuckDuckGo tras varios intentos.")
    return []


# ═══════════════════════════════════════════════════════════════════════════
#  LIMPIEZA DE FORMATO (red de seguridad por si el modelo igual manda LaTeX)
# ═══════════════════════════════════════════════════════════════════════════

# Reemplazos de comandos LaTeX comunes por su símbolo o texto equivalente.
# Se aplican DESPUÉS de quitar los delimitadores \[ \] \( \) $ $$.
_LATEX_COMANDOS = [
    (r"\\mathcal\{([^{}]*)\}", r"\1"),
    (r"\\text\{([^{}]*)\}", r"\1"),
    (r"\\mathrm\{([^{}]*)\}", r"\1"),
    (r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)"),
    (r"\\sqrt\{([^{}]*)\}", r"√(\1)"),
    (r"\\int_\{([^{}]*)\}\^\{([^{}]*)\}", r"∫[\1 a \2]"),
    (r"\\int", "∫"),
    (r"\\sum_\{([^{}]*)\}\^\{([^{}]*)\}", r"Σ[\1 a \2]"),
    (r"\\sum", "Σ"),
    (r"\\infty", "∞"),
    (r"\\cdot", "·"),
    (r"\\times", "×"),
    (r"\\pm", "±"),
    (r"\\geq?", "≥"),
    (r"\\leq?", "≤"),
    (r"\\neq", "≠"),
    (r"\\approx", "≈"),
    (r"\\to", "→"),
    (r"\\rightarrow", "→"),
    (r"\\pi", "π"),
    (r"\\alpha", "α"),
    (r"\\beta", "β"),
    (r"\\theta", "θ"),
    (r"\\omega", "ω"),
    (r"\\lambda", "λ"),
    (r"\\partial", "∂"),
    (r"\\left", ""),
    (r"\\right", ""),
    (r"\\,", " "),
    (r"\\;", " "),
    (r"\\\\", " "),
    (r"\\\{", "{"),
    (r"\\\}", "}"),
]


def limpiar_formato_ia(texto: str) -> str:
    """
    Quita restos de notación LaTeX que el modelo pudiera colar pese a las
    instrucciones del prompt, y los deja en texto plano legible.
    No toca el markdown simple (negrita **, listas con -), eso se procesa
    aparte en la interfaz.
    """
    if not texto:
        return texto

    # Quitar delimitadores de bloque/inline: \[ ... \], \( ... \), $$ ... $$, $ ... $
    texto = re.sub(r"\\\[(.*?)\\\]", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"\\\((.*?)\\\)", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"\$\$(.*?)\$\$", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"(?<!\d)\$(.*?)\$(?!\d)", r"\1", texto)

    for patron, reemplazo in _LATEX_COMANDOS:
        texto = re.sub(patron, reemplazo, texto)

    # Exponentes/subíndices con llaves: x^{-st} -> x^(-st), x_{n} -> x_(n)
    texto = re.sub(r"\^\{([^{}]*)\}", r"^(\1)", texto)
    texto = re.sub(r"_\{([^{}]*)\}", r"_(\1)", texto)

    # Limpiar espacios sobrantes que puedan quedar tras los reemplazos
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()




def _preguntar_groq(mensajes: list[dict], api_key: str = GROQ_API_KEY,
                     modelo: str = GROQ_MODEL, temperatura: float = 0.4) -> str:
    """
    Envía una lista de mensajes (formato OpenAI-style: [{"role":..,"content":..}])
    a la API de Groq y devuelve el texto de la respuesta.
    Lanza RuntimeError con un mensaje claro si algo falla (clave inválida,
    error de red, respuesta inesperada, etc.).
    """
    api_key = (api_key or "").strip()
    if not api_key or api_key == _PLACEHOLDER:
        raise RuntimeError(
            "No configuraste tu GROQ_API_KEY. Ponla en app/config.py "
            "(GROQ_API_KEY = \"gsk_tu_clave_real\") o define la variable de "
            "entorno GROQ_API_KEY."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": _UA,
    }
    payload = {
        "model": modelo,
        "messages": mensajes,
        "temperature": temperatura,
    }

    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=_TIMEOUT * 2)
    except requests.RequestException as e:
        raise RuntimeError(f"Error de conexión con Groq: {e}") from e

    if resp.status_code == 401:
        raise RuntimeError("Groq rechazó la clave (401). Revisa tu GROQ_API_KEY.")
    if resp.status_code == 403:
        raise RuntimeError(
            "Groq devolvió 403. Verifica que estés usando 'requests' con cabeceras "
            "válidas (no urllib.request) y que la clave sea correcta."
        )
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"Error de Groq ({resp.status_code}): {resp.text[:300]}") from e

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Respuesta inesperada de Groq: {data}") from e


# ═══════════════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL: pregunta + búsqueda en internet + respuesta de la IA
# ═══════════════════════════════════════════════════════════════════════════

def responder_con_busqueda(pregunta: str, api_key: str = GROQ_API_KEY,
                            max_resultados: int = 5) -> dict:
    """
    1. Busca `pregunta` en DuckDuckGo.
    2. Arma un contexto con los resultados.
    3. Le pide a Groq que responda usando ese contexto.

    Devuelve: {"respuesta": str, "fuentes": list[dict]}
    """
    fuentes = _buscar_duckduckgo(pregunta, max_resultados=max_resultados)

    instrucciones_formato = (
        "Responde en texto plano, legible en una interfaz simple (no en un "
        "editor con soporte LaTeX/Markdown). Reglas de formato:\n"
        "- NUNCA uses notación LaTeX (nada de \\[, \\], \\(, \\), \\frac, "
        "\\int, \\mathcal, $, $$, etc.). Escribe las fórmulas con símbolos "
        "normales de teclado, ej: F(s) = integral de 0 a infinito de "
        "e^(-st) f(t) dt.\n"
        "- No uses encabezados con # ni ###.\n"
        "- Puedes usar **negrita** para resaltar términos clave y listas "
        "con guion '-' cuando ayuden a organizar la respuesta.\n"
        "- Evita bloques de código a menos que el usuario pida código."
    )

    if fuentes:
        contexto = "\n\n".join(
            f"[{i+1}] {f['titulo']}\n{f['resumen']}\nURL: {f['url']}"
            for i, f in enumerate(fuentes)
        )
        mensaje_sistema = (
            "Eres un asistente de investigación. Usa los resultados de búsqueda "
            "de abajo para responder la pregunta del usuario de forma clara y "
            "concisa, en español. Si citas un dato, indica el número de fuente "
            "entre corchetes, ej: [1]. Si los resultados no alcanzan para "
            "responder, dilo honestamente.\n\n"
            f"{instrucciones_formato}\n\n"
            f"RESULTADOS DE BÚSQUEDA:\n{contexto}"
        )
    else:
        mensaje_sistema = (
            "Eres un asistente útil. No se encontraron resultados de búsqueda "
            "web para esta consulta, así que responde con tu propio conocimiento "
            "y aclara que no pudiste verificarlo con fuentes actuales.\n\n"
            f"{instrucciones_formato}"
        )

    mensajes = [
        {"role": "system", "content": mensaje_sistema},
        {"role": "user", "content": pregunta},
    ]

    respuesta = _preguntar_groq(mensajes, api_key=api_key)
    respuesta = limpiar_formato_ia(respuesta)
    return {"respuesta": respuesta, "fuentes": fuentes}


def preguntar_ia(pregunta: str, api_key: str = GROQ_API_KEY) -> str:
    """Pregunta directa a Groq, sin búsqueda web (chat simple)."""
    mensajes = [
        {"role": "system", "content": "Eres un asistente útil que responde en español."},
        {"role": "user", "content": pregunta},
    ]
    return limpiar_formato_ia(_preguntar_groq(mensajes, api_key=api_key))


# ═══════════════════════════════════════════════════════════════════════════
#  PRUEBA MANUAL (python -m core.groq_assistant)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("── Prueba de búsqueda ──")
    res = _buscar_duckduckgo("clima en Lima hoy", max_resultados=3)
    for r in res:
        print(f"- {r['titulo']} -> {r['url']}")
        print(f"  {r['resumen'][:120]}...")

    print("\n── Prueba de Groq + búsqueda ──")
    try:
        salida = responder_con_busqueda("¿Qué es Groq y para qué sirve?")
        print(salida["respuesta"])
        print("\nFuentes:")
        for i, f in enumerate(salida["fuentes"], 1):
            print(f"[{i}] {f['url']}")
    except RuntimeError as e:
        print(f"Error: {e}")