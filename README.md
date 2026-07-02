# 🧠 NeuroCore AI — Second Brain App

**Aplicación de escritorio para gestión de conocimiento personal (PKM), construida con Python y PyQt6.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/DB-SQLite3-003B57?logo=sqlite&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-yellow)
![Licencia](https://img.shields.io/badge/Uso-Académico-lightgrey)

---

## 📋 Tabla de contenidos

1. [Descripción general](#-descripción-general)
2. [Características principales](#-características-principales)
3. [Arquitectura del proyecto](#-arquitectura-del-proyecto)
4. [Principios de Programación Orientada a Objetos aplicados](#-principios-de-programación-orientada-a-objetos-aplicados)
5. [Patrones de diseño](#-patrones-de-diseño)
6. [Tecnologías utilizadas](#-tecnologías-utilizadas)
7. [Estructura del proyecto](#-estructura-del-proyecto)
8. [Modelo de datos](#-modelo-de-datos)
9. [Instalación y ejecución](#-instalación-y-ejecución)
10. [Estado de pruebas](#-estado-de-pruebas)
11. [Limitaciones conocidas y trabajo futuro](#-limitaciones-conocidas-y-trabajo-futuro)
12. [Autor](#-autor)

---

## 📖 Descripción general

**NeuroCore AI** (nombre interno del proyecto: *Second Brain App*) es una aplicación de escritorio desarrollada en **Python** con interfaz gráfica **PyQt6**, pensada como un "segundo cerebro" digital para estudiantes: un espacio único donde tomar apuntes, convertirlos en material de repaso, gestionar el tiempo de estudio y realizar búsquedas inteligentes sobre el propio conocimiento acumulado.

El proyecto se desarrolló como ejercicio práctico del curso de **Programación Orientada a Objetos**, aplicando una arquitectura en capas (GUI → Servicios → Núcleo → Persistencia) y los cuatro pilares de la POO: **encapsulamiento, abstracción, herencia y polimorfismo**, además de patrones de diseño estándar de la industria como **Observer** (señales/slots de Qt) y **Worker Thread**.

---

## ✨ Características principales

La aplicación se organiza en **6 módulos** accesibles desde una barra lateral de navegación:

| Módulo | Descripción |
|---|---|
| ⏱ **Enfoque** | Temporizador Pomodoro con anillo de progreso dibujado a mano (`QPainter`), registro y acumulación de sesiones de concentración. |
| 📓 **Cuaderno** | Editor de texto enriquecido (negrita, cursiva, subrayado, listas, tamaño de fuente) para tomar apuntes por categoría/curso. Permite importar PDFs (extracción y fragmentación automática de texto) y exportar los apuntes a **HTML**, **Markdown** o **texto plano**. |
| 🧠 **Buscador IA** | Motor de búsqueda semántica sobre los apuntes guardados: convierte cada apunte y cada consulta en un vector numérico (*embedding*) y recupera los más relevantes por similitud de coseno, en lugar de una simple coincidencia de palabras. |
| 🃏 **Flashcards** | Sistema de tarjetas de estudio con **repetición espaciada** (algoritmo estilo Leitner): cada acierto duplica el intervalo de repaso; cada fallo lo reinicia a 1 día. |
| 🎙️ **Notas de Voz** | Grabación de audio y transcripción automática a texto mediante *Whisper* (OpenAI), ejecutada en un hilo secundario para no bloquear la interfaz. |
| 📊 **Estadísticas** | Panel de analítica con resumen numérico y gráfico de barras (dibujado manualmente) del tiempo de estudio por sesión. |

Adicionalmente, toda la aplicación cuenta con un **sistema de temas claro/oscuro** conmutable en tiempo real.

---

## 🏗 Arquitectura del proyecto

El proyecto sigue una **arquitectura en capas**, que separa la interfaz gráfica de la lógica de negocio y esta, a su vez, del acceso a datos:

```
┌─────────────────────────────────────────────┐
│                CAPA DE PRESENTACIÓN           │
│   app/gui.py  (paneles, widgets, ventana      │
│   principal — PyQt6)                          │
└───────────────────┬───────────────────────────┘
                     │  usa
┌───────────────────▼───────────────────────────┐
│                CAPA DE SERVICIOS               │
│   services/brain_service.py                    │
│   (BrainService: reglas de negocio, SQL,        │
│   orquesta embeddings y lectura de PDF)         │
└───────┬───────────────────────────┬─────────────┘
        │ usa                       │ usa
┌───────▼─────────┐        ┌────────▼──────────┐
│  CAPA DE NÚCLEO   │        │  CAPA DE NÚCLEO    │
│ core/embeddings.py│        │ core/pdf_reader.py │
│ (EmbeddingManager) │        │ (extracción PDF)   │
└───────┬─────────┘        └───────────────────┘
        │
┌───────▼─────────┐
│   PERSISTENCIA    │
│  SQLite3 (data/    │
│  brain.db)         │
└───────────────────┘
```

**Punto de entrada:** `app/main.py` inicializa la aplicación Qt (`_app`), aplica la fuente global y lanza `VentanaPrincipal`, que a su vez instancia un único `BrainService` compartido por todos los paneles (inyección de dependencia simple vía constructor).

---

## 🎯 Principios de Programación Orientada a Objetos aplicados

| Principio | Cómo se aplica en el proyecto |
|---|---|
| **Encapsulamiento** | `BrainService` oculta por completo el acceso a SQLite: ningún panel de la GUI ejecuta SQL directamente, todo pasa por métodos públicos como `guardar_en_el_cerebro()`, `responder_flashcard()`, etc. Los atributos internos (`_conn`, `_emb`) usan el prefijo `_` para señalar que son de uso interno de la clase. |
| **Abstracción** | La GUI no sabe *cómo* se calcula una similitud semántica ni *cómo* se parte un PDF en párrafos; solo invoca `self.cerebro.ingestar_pdf(...)` o `self._emb.search(...)`. El "cómo" queda oculto detrás de una interfaz simple. |
| **Herencia** | Todos los widgets personalizados heredan de clases base de PyQt6 y extienden su comportamiento, por ejemplo: `class CuadernoPanel(QWidget)`, `class VentanaPrincipal(QMainWindow)`, `class NavButton(QPushButton)`, `class PDFIngestWorker(QThread)`, `class WhisperWorker(QObject)`. En total el proyecto define **21 clases**, la gran mayoría por especialización de clases de Qt. |
| **Polimorfismo** | Varias clases sobrescriben (*override*) métodos heredados para cambiar su comportamiento por defecto, por ejemplo `paintEvent()` en `RingWidget` (anillo del Pomodoro) y `BarChartWidget` (gráfico de estadísticas), donde cada widget dibuja algo completamente distinto usando la misma interfaz `QPainter`. |
| **Composición** | `VentanaPrincipal` no hereda de cada panel, sino que los **compone**: crea una instancia de `PomodoroPanel`, `CuadernoPanel`, `BuscadorPanel`, `FlashcardsPanel`, `NotasVozPanel` y `EstadisticasPanel`, y los intercambia dentro de un `QStackedWidget` según el botón de navegación pulsado. |
| **Responsabilidad única (SRP)** | Cada clase de servicio tiene una única responsabilidad: `EmbeddingManager` solo sabe de vectores y similitud; `BrainService` solo sabe de persistencia y reglas de negocio; los *Workers* (`PDFIngestWorker`, `WhisperWorker`, `GrabacionWorker`) solo ejecutan una tarea pesada en segundo plano. |

---

## 🧩 Patrones de diseño

- **Observer (Señales y slots de Qt):** la comunicación entre componentes se hace mediante `pyqtSignal`, evitando el acoplamiento directo entre clases. Ejemplos: `PDFIngestWorker.exito`, `CuadernoPanel.convertir_en_flashcard`, `WhisperWorker.terminado`.
- **Worker Thread (concurrencia):** las tareas lentas (leer un PDF grande, transcribir audio con Whisper, grabar sonido) se ejecutan en hilos separados (`QThread` / `QObject` movido a un hilo) para que la interfaz nunca se congele.
- **Repository / Service Layer:** `BrainService` actúa como capa intermedia entre la GUI y la base de datos, centralizando todas las consultas SQL en un solo lugar.
- **Fallback opcional (Optional Dependency):** tanto los embeddings semánticos como la ingesta de PDF se importan dentro de bloques `try/except` — si la librería no está instalada, la función se desactiva de forma controlada en vez de romper toda la aplicación.

---

## 🛠 Tecnologías utilizadas

| Categoría | Herramienta |
|---|---|
| Lenguaje | Python 3.10+ |
| Interfaz gráfica | PyQt6 |
| Base de datos | SQLite3 (módulo estándar `sqlite3`, sin ORM) |
| Procesamiento de PDF | `pdfplumber` |
| Búsqueda semántica | `sentence-transformers` (modelo `all-MiniLM-L6-v2`) + similitud de coseno con `numpy` |
| Transcripción de voz | `openai-whisper` + `sounddevice` / `soundfile` |

---

## 📁 Estructura del proyecto

```
Second-Brain-App/
├── app/
│   ├── main.py         # Punto de entrada de la aplicación
│   ├── config.py        # Configuración centralizada (rutas, BD)
│   └── gui.py            # Toda la interfaz: ventana principal + 6 paneles
├── core/
│   ├── embeddings.py     # EmbeddingManager: vectorización y búsqueda semántica
│   ├── memory.py         # DatabaseManager (módulo de persistencia inicial/legado)
│   └── pdf_reader.py     # Extracción y fragmentación de texto de PDFs
├── services/
│   └── brain_service.py  # BrainService: lógica de negocio central de la app
├── tests/                # Carpeta reservada para pruebas unitarias
├── data/                 # Base de datos SQLite generada en tiempo de ejecución
├── requirements.txt
└── README.md
```

> **Nota:** `core/memory.py` (`DatabaseManager`) corresponde a una primera versión del módulo de persistencia, previa a la implementación de `BrainService`. Se conserva en el repositorio como referencia histórica del proceso de diseño, pero la aplicación actual utiliza exclusivamente `BrainService`.

---

## 🗄 Modelo de datos

La base de datos SQLite (`data/brain.db`) gestionada por `BrainService` contiene las siguientes tablas principales:

| Tabla | Propósito |
|---|---|
| `apuntes` | Notas del Cuaderno, con su categoría y embedding semántico opcional. |
| `flashcards` | Tarjetas de estudio, con intervalo de repaso y próxima fecha de revisión. |
| `cursos` / `temas` | Organización jerárquica de contenidos (curso → tema) compartida entre módulos. |
| `sesiones_concentracion` | Historial de sesiones de estudio consolidadas (Pomodoro). |
| `pomodoro_temp` | Acumulador temporal de minutos durante una sesión activa. |

---

## ⚙️ Instalación y ejecución

**Requisitos previos:** Python 3.10 o superior instalado.

```bash
# 1. Clonar o descomprimir el proyecto
cd Second-Brain-App

# 2. (Recomendado) Crear un entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python -m app.main
```

Al iniciar, la aplicación crea automáticamente la carpeta `data/` y el archivo `brain.db` si no existen, por lo que no requiere ninguna configuración manual de base de datos.

---

## 🧪 Estado de pruebas

El proyecto incluye una carpeta `tests/` preparada para alojar pruebas unitarias (por ejemplo, con `pytest`) sobre la capa de servicios (`BrainService`, `EmbeddingManager`, `pdf_reader`), que son las más adecuadas para probar de forma aislada al no depender de la interfaz gráfica. Actualmente no contiene casos de prueba implementados; se considera el siguiente paso natural del proyecto.

---

## 🔭 Limitaciones conocidas y trabajo futuro

- No hay pruebas unitarias automatizadas todavía.
- La búsqueda semántica y la transcripción de voz dependen de modelos que se descargan la primera vez que se usan (requieren conexión a internet en el primer uso).
- El módulo `core/memory.py` es código legado sin uso activo; queda pendiente removerlo o documentarlo formalmente como archivado.
- Posibles mejoras futuras: sincronización en la nube, exportación de flashcards, integración con modelos de lenguaje para generación automática de resúmenes.

---

## 👤 Autor

**Diego** — Proyecto desarrollado para el curso de **Programación Orientada a Objetos**.
Universidad: *[completar]* · Ciclo/Semestre: *[completar]* · Docente: *[completar]*
