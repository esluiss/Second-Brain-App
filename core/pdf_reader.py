# core/pdf_reader.py
"""
Utilidades para "ingestar" archivos PDF dentro del Second Brain.

Flujo:
    1. extraer_texto_pdf(ruta)      -> texto plano de todo el documento
    2. dividir_en_parrafos(texto)   -> lista de fragmentos listos para
                                        guardarse en la base de datos, igual
                                        que si el usuario los hubiera escrito
                                        a mano en el Cuaderno.
"""

import re

import pdfplumber

# Tamaños por defecto para los fragmentos guardados
MIN_CARACTERES = 40     # descarta fragmentos demasiado cortos (núm. de página, etc.)
MAX_CARACTERES = 800    # divide bloques muy largos en trozos más pequeños


def extraer_texto_pdf(ruta_pdf: str) -> str:
    """
    Abre un PDF y devuelve TODO su texto como un único string.
    Cada página se separa con un doble salto de línea para que,
    al dividir en párrafos, no se mezclen páginas distintas.
    """
    paginas_texto = []

    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text()
            if texto_pagina:
                paginas_texto.append(texto_pagina)

    return "\n\n".join(paginas_texto)


def dividir_en_parrafos(texto: str,
                        min_caracteres: int = MIN_CARACTERES,
                        max_caracteres: int = MAX_CARACTERES) -> list:
    """
    Divide un texto largo en fragmentos "tipo párrafo" listos para guardar.

    1. Usa los dobles saltos de línea como separadores naturales de párrafo
       y junta las líneas sueltas de cada bloque en una sola línea (los PDFs
       suelen cortar el texto línea por línea).
    2. Muchos PDFs (diapositivas, libros, escaneos) NO tienen líneas en
       blanco entre párrafos: toda una página puede salir como un solo
       bloque enorme. Para esos casos, los bloques que superan
       `max_caracteres` se vuelven a dividir agrupando oraciones completas
       hasta llenar ese tamaño.
    3. Descarta fragmentos demasiado cortos (números de página, encabezados
       sueltos, viñetas vacías, etc.) usando `min_caracteres`.

    Devuelve una lista de strings, cada uno listo para guardarse como
    un "apunte" independiente en el cerebro.
    """
    if not texto:
        return []

    bloques = texto.split("\n\n")
    fragmentos = []

    for bloque in bloques:
        # Unimos las líneas del bloque en un solo párrafo limpio
        lineas = [linea.strip() for linea in bloque.splitlines()]
        parrafo = " ".join(linea for linea in lineas if linea)

        if not parrafo:
            continue

        if len(parrafo) <= max_caracteres:
            if len(parrafo) >= min_caracteres:
                fragmentos.append(parrafo)
        else:
            # Bloque demasiado grande -> lo partimos por oraciones
            fragmentos.extend(
                _dividir_por_oraciones(parrafo, min_caracteres, max_caracteres)
            )

    return fragmentos


def _dividir_por_oraciones(texto: str, min_caracteres: int, max_caracteres: int) -> list:
    """
    Agrupa oraciones consecutivas hasta acercarse a `max_caracteres`,
    sin cortar ninguna oración a la mitad.
    """
    oraciones = re.split(r'(?<=[.!?])\s+', texto)
    fragmentos = []
    actual = ""

    for oracion in oraciones:
        oracion = oracion.strip()
        if not oracion:
            continue

        if not actual:
            actual = oracion
        elif len(actual) + 1 + len(oracion) <= max_caracteres:
            actual += " " + oracion
        else:
            if len(actual) >= min_caracteres:
                fragmentos.append(actual)
            actual = oracion

    if actual and len(actual) >= min_caracteres:
        fragmentos.append(actual)

    return fragmentos
