# core/embeddings.py  –  NeuroCore AI
# Encapsula sentence-transformers para búsqueda semántica real.

import io
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"   # ~22 MB, rápido, excelente para español + inglés


def _vec_to_blob(vec: np.ndarray) -> bytes:
    """Serializa un numpy array float32 a bytes (para guardarlo en SQLite BLOB)."""
    buf = io.BytesIO()
    np.save(buf, vec.astype(np.float32))
    return buf.getvalue()


def _blob_to_vec(blob: bytes) -> np.ndarray:
    """Deserializa bytes de SQLite a numpy array float32."""
    return np.load(io.BytesIO(blob)).astype(np.float32)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Similitud coseno entre dos vectores. Devuelve un valor entre -1 y 1."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class EmbeddingManager:
    """
    Gestiona la codificación de textos y la búsqueda semántica.

    Uso típico en BrainService:
        self._emb = EmbeddingManager(conn)
        blob = self._emb.encode("mi texto")        # guardar en BD
        resultados = self._emb.search("consulta", rows, top_k=5)
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn  = conn
        self._model = SentenceTransformer(MODEL_NAME)

    # ── Codificación ──────────────────────────────────────────────────────────

    def encode(self, texto: str) -> bytes:
        """
        Convierte un texto en un vector y lo serializa a bytes listos para
        guardarse en un campo BLOB de SQLite.
        """
        # Limpiar HTML básico antes de encodear (el texto puede venir del editor)
        texto_plano = _strip_html(texto)
        vec = self._model.encode(texto_plano, normalize_embeddings=True)
        return _vec_to_blob(vec)

    # ── Búsqueda semántica ────────────────────────────────────────────────────

    def search(self, consulta: str, rows: list, top_k: int = 5) -> list:
        """
        Busca los 'top_k' apuntes más similares semánticamente a la consulta.

        Parámetros:
            consulta  – texto libre escrito por el usuario
            rows      – lista de sqlite3.Row con campos: id, texto, categoria, embedding
            top_k     – cuántos resultados devolver

        Devuelve lista de dicts:
            {'texto', 'categoria', 'score', 'tipo_busqueda'}
            donde score está en [0, 1] y tipo_busqueda es 'semantica'.
        """
        query_vec = self._model.encode(
            _strip_html(consulta), normalize_embeddings=True
        )

        resultados = []
        for row in rows:
            blob = row["embedding"]
            if blob is None:
                continue
            try:
                doc_vec = _blob_to_vec(blob)
            except Exception:
                continue

            sim = _cosine_similarity(query_vec, doc_vec)
            # Normalizamos de [-1,1] a [0,1] para mostrarlo como porcentaje
            score_01 = max(0.0, min(1.0, (sim - 0.12) / 0.33))
            resultados.append({
                "texto":          row["texto"],
                "categoria":      row["categoria"],
                "score":          round(score_01, 4),
                "tipo_busqueda":  "semantica",
            })

        resultados.sort(key=lambda x: x["score"], reverse=True)
        return resultados[:top_k]

    # ── Re-indexación ─────────────────────────────────────────────────────────

    def reindexar_todos(self) -> int:
        """
        Genera embeddings para todos los apuntes que todavía no tienen uno.
        Devuelve la cantidad de apuntes procesados.
        """
        rows = self._conn.execute(
            "SELECT id, texto FROM apuntes WHERE embedding IS NULL"
        ).fetchall()

        for row in rows:
            try:
                blob = self.encode(row["texto"])
                self._conn.execute(
                    "UPDATE apuntes SET embedding = ? WHERE id = ?",
                    (blob, row["id"])
                )
            except Exception:
                pass

        self._conn.commit()
        return len(rows)


# ── Utilidad interna ──────────────────────────────────────────────────────────

def _strip_html(texto: str) -> str:
    """Elimina tags HTML para encodear texto limpio (sin dependencias externas)."""
    import re, html as html_lib
    t = texto.strip()
    if not t.startswith("<"):
        return t
    t = re.sub(r"<br\s*/?>",        " ",  t, flags=re.IGNORECASE)
    t = re.sub(r"<p[^>]*>",         " ",  t, flags=re.IGNORECASE)
    t = re.sub(r"<[^>]+>",          "",   t)
    t = html_lib.unescape(t)
    return re.sub(r"\s+", " ", t).strip()
