# services/brain_service.py  –  NeuroCore AI
# Maneja la persistencia en SQLite y la búsqueda semántica (con fallback por texto)

import os
import sqlite3
from pathlib import Path

# ── Ruta absoluta a la base de datos ──────────────────────────────────────────
# Este archivo vive en  <proyecto>/services/brain_service.py
# La base de datos está en  <proyecto>/data/brain.db
_BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH   = _BASE_DIR / "data" / "brain.db"

# ── Soporte de embeddings (opcional) ──────────────────────────────────────────
try:
    from core.embeddings import EmbeddingManager
    _HAS_EMBEDDINGS = True
except Exception:
    _HAS_EMBEDDINGS = False

# ── Soporte para "ingesta" de PDFs (opcional) ─────────────────────────────────
try:
    from core.pdf_reader import extraer_texto_pdf, dividir_en_parrafos
    _HAS_PDF = True
except ImportError:
    _HAS_PDF = False


class BrainService:
    """Servicio central de persistencia y búsqueda para NeuroCore AI."""

    def __init__(self):
        # Aseguramos que la carpeta data/ exista
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

        if _HAS_EMBEDDINGS:
            try:
                self._emb = EmbeddingManager(self._conn)
            except Exception:
                pass

    # ── Inicialización del esquema ─────────────────────────────────────────────

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS apuntes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                texto      TEXT    NOT NULL,
                categoria  TEXT    NOT NULL DEFAULT 'General',
                embedding  BLOB,
                fecha      TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS pomodoro_temp (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                minutos INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sesiones_concentracion (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT    NOT NULL,
                minutos_totales INTEGER NOT NULL,
                fecha           TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS flashcards (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                pregunta         TEXT    NOT NULL,
                respuesta        TEXT    NOT NULL,
                categoria        TEXT    NOT NULL DEFAULT 'General',
                intervalo_dias   INTEGER NOT NULL DEFAULT 1,
                proxima_revision TEXT    DEFAULT (date('now')),
                fecha_creacion   TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS cursos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL UNIQUE,
                fecha_creacion TEXT    DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS temas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL,
                curso_id       INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
                fecha_creacion TEXT    DEFAULT (datetime('now','localtime')),
                UNIQUE(nombre, curso_id)
            );
        """)
        self._conn.commit()

        # Migracion: agregar columnas a flashcards si no existen (ALTER TABLE no soporta IF NOT EXISTS)
        for col_def in [
            ("tema_id",  "ALTER TABLE flashcards ADD COLUMN tema_id  INTEGER REFERENCES temas(id) ON DELETE SET NULL"),
            ("curso_id", "ALTER TABLE flashcards ADD COLUMN curso_id INTEGER REFERENCES cursos(id) ON DELETE SET NULL"),
        ]:
            col_name, sql = col_def
            cols = [r[1] for r in self._conn.execute("PRAGMA table_info(flashcards)").fetchall()]
            if col_name not in cols:
                self._conn.execute(sql)
        self._conn.commit()

        # Sembramos un curso "General" por defecto para que la lista de
        # categorías (compartida entre Cuaderno, Notas de Voz y Flashcards)
        # nunca empiece vacía.
        self._conn.execute("INSERT OR IGNORE INTO cursos (nombre) VALUES ('General')")
        self._conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    #  CUADERNO DE APUNTES
    # ═══════════════════════════════════════════════════════════════════════════

    def guardar_en_el_cerebro(self, texto: str, categoria: str = "General"):
        """Persiste un apunte; genera embedding semántico si sentence-transformers está disponible."""
        embedding_blob = None
        if _HAS_EMBEDDINGS and hasattr(self, "_emb"):
            try:
                embedding_blob = self._emb.encode(texto)  # devuelve bytes (BLOB)
            except Exception:
                pass

        self._conn.execute(
            "INSERT INTO apuntes (texto, categoria, embedding) VALUES (?, ?, ?)",
            (texto, categoria, embedding_blob)
        )
        self._conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    #  INGESTA DE PDFs
    # ═══════════════════════════════════════════════════════════════════════════

    def ingestar_pdf(self, ruta_pdf: str, categoria: str = "General") -> int:
        """
        Lee un archivo PDF, extrae su texto, lo divide en párrafos y guarda
        cada párrafo en la base de datos exactamente como si el usuario lo
        hubiera escrito a mano en el Cuaderno de apuntes.

        Devuelve la cantidad de párrafos/fragmentos que se guardaron.
        Lanza RuntimeError si el soporte de PDF no está disponible
        (falta instalar 'pdfplumber') o ImportError/Exception si el
        archivo no se pudo leer.
        """
        if not _HAS_PDF:
            raise RuntimeError(
                "Falta instalar la librería 'pdfplumber'. "
                "Ejecuta: pip install pdfplumber"
            )

        texto = extraer_texto_pdf(ruta_pdf)
        parrafos = dividir_en_parrafos(texto)

        for parrafo in parrafos:
            self.guardar_en_el_cerebro(parrafo, categoria)

        return len(parrafos)


    def obtener_todos_apuntes(self) -> list:
        """Devuelve todos los apuntes ordenados por fecha descendente.
        Cada elemento es un dict: {id, texto, categoria, fecha}
        """
        rows = self._conn.execute(
            "SELECT id, texto, categoria, fecha FROM apuntes ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def eliminar_apunte_por_id(self, apunte_id: int):
        """Elimina un apunte por su id (forma segura y directa)."""
        self._conn.execute("DELETE FROM apuntes WHERE id = ?", (apunte_id,))
        self._conn.commit()

    def actualizar_apunte(self, apunte_id: int, nuevo_texto: str, nueva_categoria: str):
        """Actualiza el texto y la categoría de un apunte existente.
        Si hay embeddings disponibles, regenera el embedding.
        """
        nuevo_blob = None
        if _HAS_EMBEDDINGS and hasattr(self, "_emb"):
            try:
                nuevo_blob = self._emb.encode(nuevo_texto)
            except Exception:
                pass

        if nuevo_blob is not None:
            self._conn.execute(
                "UPDATE apuntes SET texto = ?, categoria = ?, embedding = ? WHERE id = ?",
                (nuevo_texto, nueva_categoria, nuevo_blob, apunte_id)
            )
        else:
            self._conn.execute(
                "UPDATE apuntes SET texto = ?, categoria = ? WHERE id = ?",
                (nuevo_texto, nueva_categoria, apunte_id)
            )
        self._conn.commit()

    def eliminar_apunte(self, texto: str):
        """Elimina el primer apunte cuyo texto coincida exactamente."""
        self._conn.execute(
            "DELETE FROM apuntes WHERE id = "
            "(SELECT id FROM apuntes WHERE texto = ? LIMIT 1)",
            (texto,)
        )
        self._conn.commit()

    def buscar_con_ia(self, consulta: str) -> list:
        """
        Búsqueda semántica: usa sentence-transformers para encontrar apuntes
        por significado, no por palabras exactas.
        Devuelve lista de dicts: {'texto', 'categoria', 'score', 'tipo_busqueda'}
        """
        rows = self._conn.execute(
            "SELECT id, texto, categoria, embedding FROM apuntes"
        ).fetchall()

        if not rows:
            return []

        # ── Búsqueda semántica ────────────────────────────────────────────────
        if _HAS_EMBEDDINGS and hasattr(self, "_emb"):
            # Si hay apuntes sin embedding (guardados antes de instalar la lib),
            # los indexamos ahora silenciosamente.
            sin_emb = [r for r in rows if r["embedding"] is None]
            if sin_emb:
                self._emb.reindexar_todos()
                rows = self._conn.execute(
                    "SELECT id, texto, categoria, embedding FROM apuntes"
                ).fetchall()
            try:
                return self._emb.search(consulta, rows, top_k=5)
            except Exception:
                pass

        # ── Fallback: búsqueda por coincidencia de palabras ───────────────────
        palabras   = consulta.lower().split()
        resultados = []
        for row in rows:
            texto_lower = row["texto"].lower()
            matches     = sum(1 for w in palabras if w in texto_lower)
            if matches > 0:
                score = round(matches / max(len(palabras), 1), 2)
                resultados.append({
                    "texto":          row["texto"],
                    "categoria":      row["categoria"],
                    "score":          score,
                    "tipo_busqueda":  "textual",
                })

        resultados.sort(key=lambda x: x["score"], reverse=True)
        return resultados[:5]

    # ═══════════════════════════════════════════════════════════════════════════
    #  POMODORO — ACUMULADOR TEMPORAL
    # ═══════════════════════════════════════════════════════════════════════════

    def guardar_pomodoro(self, minutos: int):
        """
        Suma minutos al acumulador temporal de la sesión actual.
        Se llama automáticamente cada vez que un temporizador llega a 0.
        """
        self._conn.execute(
            "INSERT INTO pomodoro_temp (minutos) VALUES (?)", (minutos,)
        )
        self._conn.commit()

    def obtener_texto_estadisticas(self) -> str:
        """
        Devuelve el tiempo acumulado temporal como string legible.
        Ejemplo: '1 h 25 min'
        """
        total = self._conn.execute(
            "SELECT COALESCE(SUM(minutos), 0) FROM pomodoro_temp"
        ).fetchone()[0]
        h, m = divmod(int(total), 60)
        return f"{h} h {m} min"

    def consolidar_sesion_actual(self) -> bool:
        """
        Guarda el acumulado temporal como una nueva 'Sesión de concentración N'
        y limpia el acumulador.
        Devuelve True si había tiempo que guardar, False si el acumulador estaba vacío.
        """
        total = self._conn.execute(
            "SELECT COALESCE(SUM(minutos), 0) FROM pomodoro_temp"
        ).fetchone()[0]

        if int(total) <= 0:
            return False

        # Número de la siguiente sesión
        n = self._conn.execute(
            "SELECT COUNT(*) FROM sesiones_concentracion"
        ).fetchone()[0]
        nombre = f"Sesión de concentración {n + 1}"

        self._conn.execute(
            "INSERT INTO sesiones_concentracion (nombre, minutos_totales) VALUES (?, ?)",
            (nombre, int(total))
        )
        self._conn.execute("DELETE FROM pomodoro_temp")
        self._conn.commit()
        return True

    def borrar_historial_pomodoro(self):
        """Elimina todo el acumulador temporal (sin guardar como sesión)."""
        self._conn.execute("DELETE FROM pomodoro_temp")
        self._conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    #  SESIONES GUARDADAS  (para EstadisticasPanel)
    # ═══════════════════════════════════════════════════════════════════════════

    def obtener_sesiones_guardadas(self) -> list:
        """
        Devuelve todas las sesiones de concentración guardadas, ordenadas por id.
        Cada elemento es un dict: {'id', 'nombre', 'minutos', 'fecha'}
        """
        rows = self._conn.execute(
            "SELECT id, nombre, minutos_totales, fecha "
            "FROM sesiones_concentracion ORDER BY id"
        ).fetchall()

        return [
            {
                "id":      row["id"],
                "nombre":  row["nombre"],
                "minutos": row["minutos_totales"],
                "fecha":   row["fecha"],
            }
            for row in rows
        ]

    def borrar_sesion(self, session_id: int):
        """Elimina una sesión guardada por su id."""
        self._conn.execute(
            "DELETE FROM sesiones_concentracion WHERE id = ?", (session_id,)
        )
        self._conn.commit()

    # ═══════════════════════════════════════════════════════════════════════════
    #  FLASHCARDS  (repaso con repetición espaciada estilo Leitner)
    # ═══════════════════════════════════════════════════════════════════════════

    # Tope máximo del intervalo de repaso (en días)
    _INTERVALO_MAXIMO = 30

    def crear_flashcard(self, pregunta: str, respuesta: str, categoria: str = "General"):
        """Crea una nueva flashcard. Empieza con intervalo = 1 día,
        así aparece de inmediato en el próximo repaso."""
        self._conn.execute(
            "INSERT INTO flashcards (pregunta, respuesta, categoria) VALUES (?, ?, ?)",
            (pregunta, respuesta, categoria)
        )
        self._conn.commit()

    def obtener_flashcards_pendientes(self) -> list:
        """
        Devuelve las flashcards cuya fecha de repaso ya llegó (o pasó),
        ordenadas por fecha de revisión. Cada elemento es un dict:
        {'id', 'pregunta', 'respuesta', 'categoria', 'intervalo_dias'}
        """
        rows = self._conn.execute(
            "SELECT id, pregunta, respuesta, categoria, intervalo_dias "
            "FROM flashcards WHERE proxima_revision <= date('now') "
            "ORDER BY proxima_revision"
        ).fetchall()

        return [dict(row) for row in rows]

    def responder_flashcard(self, flashcard_id: int, acierto: bool):
        """
        Aplica repetición espaciada tipo Leitner:
        - Si acierto=True  -> duplica el intervalo actual (con un tope máximo).
        - Si acierto=False -> resetea el intervalo a 1 día.
        En ambos casos, recalcula 'proxima_revision' = hoy + nuevo intervalo.
        """
        row = self._conn.execute(
            "SELECT intervalo_dias FROM flashcards WHERE id = ?", (flashcard_id,)
        ).fetchone()

        if row is None:
            return

        if acierto:
            nuevo_intervalo = min(row["intervalo_dias"] * 2, self._INTERVALO_MAXIMO)
        else:
            nuevo_intervalo = 1

        self._conn.execute(
            "UPDATE flashcards SET intervalo_dias = ?, "
            "proxima_revision = date('now', '+' || ? || ' days') WHERE id = ?",
            (nuevo_intervalo, nuevo_intervalo, flashcard_id)
        )
        self._conn.commit()

    def obtener_todas_flashcards(self) -> list:
        """Devuelve todas las flashcards, sin filtrar por fecha de repaso."""
        rows = self._conn.execute(
            "SELECT id, pregunta, respuesta, categoria, intervalo_dias, "
            "proxima_revision FROM flashcards ORDER BY id"
        ).fetchall()

        return [dict(row) for row in rows]

    def eliminar_flashcard(self, flashcard_id: int):
        """Elimina una flashcard por su id."""
        self._conn.execute("DELETE FROM flashcards WHERE id = ?", (flashcard_id,))
        self._conn.commit()

    def contar_flashcards_pendientes(self) -> int:
        """Cantidad de flashcards listas para repasar hoy."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM flashcards WHERE proxima_revision <= date('now')"
        ).fetchone()[0]


    def exportar_apuntes_html(self, ruta_destino: str) -> int:
        """
        Exporta todos los apuntes a un archivo HTML autónomo.
        Si el texto almacenado ya es HTML (empieza con <!DOCTYPE o <html),
        se inserta tal cual; de lo contrario se envuelve en un <p>.
        Devuelve la cantidad de apuntes exportados.
        """
        rows = self._conn.execute(
            "SELECT texto, categoria, fecha FROM apuntes ORDER BY categoria, fecha"
        ).fetchall()

        if not rows:
            return 0

        from collections import defaultdict
        from datetime import datetime
        import html as html_lib

        grupos = defaultdict(list)
        for row in rows:
            grupos[row["categoria"]].append(row)

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

        def _wrap(texto: str) -> str:
            """Devuelve bloque HTML para insertar en el documento."""
            t = texto.strip()
            if t.lower().startswith("<!doctype") or t.lower().startswith("<html"):
                # Extraer solo el <body> para evitar doble DOCTYPE
                import re
                body = re.search(r"<body[^>]*>(.*?)</body>", t,
                                 re.IGNORECASE | re.DOTALL)
                return body.group(1).strip() if body else f"<p>{html_lib.escape(t)}</p>"
            if t.startswith("<"):
                return t  # HTML parcial (Qt lo genera así)
            return f"<p>{html_lib.escape(t)}</p>"

        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html>\n<html lang='es'>\n<head>\n")
            f.write("<meta charset='UTF-8'>\n")
            f.write("<title>Mis Apuntes — NeuroCore AI</title>\n")
            f.write("""<style>
  body { font-family: 'Segoe UI', sans-serif; max-width: 860px;
         margin: 40px auto; color: #1F2937; line-height: 1.6; }
  h1 { color: #1A73E8; } h2 { color: #374151; border-bottom: 1px solid #E5E7EB; padding-bottom:6px; }
  .nota { background:#F9FAFB; border:1px solid #E5E7EB; border-radius:10px;
           padding:14px 18px; margin-bottom:16px; }
  .meta { font-size:0.8em; color:#9CA3AF; margin-top:8px; }
  ul { margin: 4px 0 4px 20px; }
</style>\n""")
            f.write("</head>\n<body>\n")
            f.write(f"<h1>📓 Mis Apuntes</h1>\n")
            f.write(f"<p><em>Exportado el {ahora}</em></p>\n<hr>\n")

            for categoria, apuntes in sorted(grupos.items()):
                f.write(f"<h2>{html_lib.escape(categoria)}</h2>\n")
                for apunte in apuntes:
                    fecha = str(apunte["fecha"])[:16] if apunte["fecha"] else ""
                    f.write('<div class="nota">\n')
                    f.write(_wrap(apunte["texto"]))
                    if fecha:
                        f.write(f'\n<div class="meta">{fecha}</div>')
                    f.write("\n</div>\n")

            f.write("</body>\n</html>\n")

        return len(rows)

    def exportar_apuntes_md(self, ruta_destino: str) -> int:
        """
        Exporta todos los apuntes a Markdown.
        Si el texto es HTML enriquecido (generado por Qt), lo convierte
        a Markdown básico usando expresiones regulares (sin dependencias externas).
        Devuelve la cantidad de apuntes exportados.
        """
        rows = self._conn.execute(
            "SELECT texto, categoria, fecha FROM apuntes ORDER BY categoria, fecha"
        ).fetchall()

        if not rows:
            return 0

        from collections import defaultdict
        from datetime import datetime
        import re, html as html_lib

        grupos = defaultdict(list)
        for row in rows:
            grupos[row["categoria"]].append(row)

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

        def _html_to_md(texto: str) -> str:
            """Convierte HTML de Qt a Markdown básico."""
            t = texto.strip()
            if not t.startswith("<"):
                return t  # ya es texto plano

            # Extraer cuerpo si es documento completo
            body_m = re.search(r"<body[^>]*>(.*?)</body>", t,
                                re.IGNORECASE | re.DOTALL)
            if body_m:
                t = body_m.group(1).strip()

            # Headings
            t = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1", t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1", t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1", t, flags=re.IGNORECASE | re.DOTALL)

            # Negritas / cursivas / subrayado
            t = re.sub(r"<b>(.*?)</b>",       r"**\1**", t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<strong>(.*?)</strong>", r"**\1**", t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r'<span[^>]*font-weight:600[^>]*>(.*?)</span>', r"**\1**",
                       t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r'<span[^>]*font-weight:700[^>]*>(.*?)</span>', r"**\1**",
                       t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<i>(.*?)</i>",       r"*\1*",   t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<em>(.*?)</em>",     r"*\1*",   t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r'<span[^>]*font-style:italic[^>]*>(.*?)</span>', r"*\1*",
                       t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<u>(.*?)</u>",       r"<u>\1</u>",  t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r'<span[^>]*text-decoration: underline[^>]*>(.*?)</span>',
                       r"<u>\1</u>", t, flags=re.IGNORECASE | re.DOTALL)

            # Listas
            t = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1", t, flags=re.IGNORECASE | re.DOTALL)
            t = re.sub(r"<[uo]l[^>]*>", "", t, flags=re.IGNORECASE)
            t = re.sub(r"</[uo]l>",     "", t, flags=re.IGNORECASE)

            # Párrafos y saltos
            t = re.sub(r"<br\s*/?>",           "\n",  t, flags=re.IGNORECASE)
            t = re.sub(r"<p[^>]*>(.*?)</p>",   r"\1\n", t, flags=re.IGNORECASE | re.DOTALL)

            # Quitar spans sobrantes
            t = re.sub(r"<span[^>]*>", "", t, flags=re.IGNORECASE)
            t = re.sub(r"</span>",     "", t, flags=re.IGNORECASE)

            # Quitar cualquier tag restante
            t = re.sub(r"<[^>]+>", "", t)

            # Decodificar entidades HTML
            t = html_lib.unescape(t)

            # Limpiar líneas en blanco excesivas
            t = re.sub(r"\n{3,}", "\n\n", t).strip()
            return t

        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write("# 📓 Mis Apuntes\n")
            f.write(f"*Exportado el {ahora}*\n\n")
            f.write("---\n\n")

            for categoria, apuntes in sorted(grupos.items()):
                f.write(f"## {categoria}\n\n")
                for apunte in apuntes:
                    fecha = str(apunte["fecha"])[:16] if apunte["fecha"] else ""
                    contenido_md = _html_to_md(apunte["texto"])
                    f.write(contenido_md)
                    if fecha:
                        f.write(f"\n\n*_{fecha}_*")
                    f.write("\n\n---\n\n")

        return len(rows)

    def exportar_apuntes_txt(self, ruta_destino: str) -> int:
        """
        Exporta todos los apuntes a texto plano (sin formato).
        Devuelve la cantidad de apuntes exportados.
        """
        rows = self._conn.execute(
            "SELECT texto, categoria, fecha FROM apuntes ORDER BY categoria, fecha"
        ).fetchall()

        if not rows:
            return 0

        from collections import defaultdict
        from datetime import datetime
        import re, html as html_lib

        grupos = defaultdict(list)
        for row in rows:
            grupos[row["categoria"]].append(row)

        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

        def _strip_html(texto: str) -> str:
            t = texto.strip()
            if not t.startswith("<"):
                return t
            t = re.sub(r"<br\s*/?>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"<p[^>]*>", "", t, flags=re.IGNORECASE)
            t = re.sub(r"</p>", "\n", t, flags=re.IGNORECASE)
            t = re.sub(r"<li[^>]*>", "- ", t, flags=re.IGNORECASE)
            t = re.sub(r"<[^>]+>", "", t)
            t = html_lib.unescape(t)
            return re.sub(r"\n{3,}", "\n\n", t).strip()

        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(f"MIS APUNTES — Exportado el {ahora}\n")
            f.write("=" * 50 + "\n\n")
            for categoria, apuntes in sorted(grupos.items()):
                f.write(f"[{categoria.upper()}]\n\n")
                for apunte in apuntes:
                    fecha = str(apunte["fecha"])[:16] if apunte["fecha"] else ""
                    f.write(_strip_html(apunte["texto"]))
                    if fecha:
                        f.write(f"\n({fecha})")
                    f.write("\n\n" + "-" * 30 + "\n\n")

        return len(rows)

    # ═══════════════════════════════════════════════════════════════
    #  CURSOS
    # ═══════════════════════════════════════════════════════════════

    def crear_curso(self, nombre: str) -> int:
        """Crea un curso nuevo. Devuelve su id."""
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO cursos (nombre) VALUES (?)", (nombre.strip(),)
        )
        self._conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        return self._conn.execute(
            "SELECT id FROM cursos WHERE nombre = ?", (nombre.strip(),)
        ).fetchone()["id"]

    def obtener_cursos(self) -> list:
        rows = self._conn.execute(
            "SELECT id, nombre FROM cursos ORDER BY nombre"
        ).fetchall()
        return [dict(r) for r in rows]

    def eliminar_curso(self, curso_id: int):
        self._conn.execute("DELETE FROM cursos WHERE id = ?", (curso_id,))
        self._conn.commit()

    def renombrar_curso(self, curso_id: int, nuevo_nombre: str):
        self._conn.execute(
            "UPDATE cursos SET nombre = ? WHERE id = ?", (nuevo_nombre.strip(), curso_id)
        )
        self._conn.commit()

    # ═══════════════════════════════════════════════════════════════
    #  TEMAS
    # ═══════════════════════════════════════════════════════════════

    def crear_tema(self, nombre: str, curso_id: int) -> int:
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO temas (nombre, curso_id) VALUES (?, ?)",
            (nombre.strip(), curso_id)
        )
        self._conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        return self._conn.execute(
            "SELECT id FROM temas WHERE nombre = ? AND curso_id = ?",
            (nombre.strip(), curso_id)
        ).fetchone()["id"]

    def obtener_temas(self, curso_id: int) -> list:
        rows = self._conn.execute(
            "SELECT id, nombre FROM temas WHERE curso_id = ? ORDER BY nombre",
            (curso_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def eliminar_tema(self, tema_id: int):
        self._conn.execute("DELETE FROM temas WHERE id = ?", (tema_id,))
        self._conn.commit()

    def renombrar_tema(self, tema_id: int, nuevo_nombre: str):
        self._conn.execute(
            "UPDATE temas SET nombre = ? WHERE id = ?", (nuevo_nombre.strip(), tema_id)
        )
        self._conn.commit()

    # ═══════════════════════════════════════════════════════════════
    #  FLASHCARDS  (metodos extendidos con curso/tema)
    # ═══════════════════════════════════════════════════════════════

    def crear_flashcard_v2(self, pregunta: str, respuesta: str,
                           curso_id: int, tema_id: int) -> int:
        cur = self._conn.execute(
            "INSERT INTO flashcards (pregunta, respuesta, categoria, curso_id, tema_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (pregunta, respuesta, "General", curso_id, tema_id)
        )
        self._conn.commit()
        return cur.lastrowid

    def obtener_flashcards_por_tema(self, tema_id: int) -> list:
        rows = self._conn.execute(
            "SELECT id, pregunta, respuesta, categoria, intervalo_dias, proxima_revision "
            "FROM flashcards WHERE tema_id = ? ORDER BY id",
            (tema_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def obtener_flashcards_pendientes_por_tema(self, tema_id: int) -> list:
        rows = self._conn.execute(
            "SELECT id, pregunta, respuesta, categoria, intervalo_dias "
            "FROM flashcards WHERE tema_id = ? AND proxima_revision <= date('now') "
            "ORDER BY proxima_revision",
            (tema_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def contar_flashcards_por_tema(self, tema_id: int) -> dict:
        total = self._conn.execute(
            "SELECT COUNT(*) FROM flashcards WHERE tema_id = ?", (tema_id,)
        ).fetchone()[0]
        pendientes = self._conn.execute(
            "SELECT COUNT(*) FROM flashcards WHERE tema_id = ? AND proxima_revision <= date('now')",
            (tema_id,)
        ).fetchone()[0]
        return {"total": total, "pendientes": pendientes}

