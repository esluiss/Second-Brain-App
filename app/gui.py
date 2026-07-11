# app/gui.py  –  NeuroCore AI  |  PyQt6  |  Material Design 3
# Requiere:  pip install PyQt6

import os
import sys
import math
import statistics as _stats_lib
from pathlib import Path

# ── QApplication DEBE existir antes que cualquier QWidget ─────────────────────
from PyQt6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication(sys.argv)
# ──────────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QSlider,
    QFrame, QStackedWidget, QSizePolicy, QGraphicsOpacityEffect,
    QScrollArea, QFileDialog, QToolBar, QMessageBox,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QRectF, QSize, pyqtSignal, QObject, QThread,
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen,
    QLinearGradient, QTextCharFormat, QTextListFormat, QTextCursor,
    QAction, QKeySequence,
)

# Asegurar que la raíz del proyecto esté en sys.path,
# tanto si se ejecuta gui.py directo como desde main.py
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from services.brain_service import BrainService

# El asistente de IA (Groq + búsqueda web) es opcional: si falta 'requests'
# o el usuario no configuró su API key, la app sigue funcionando con
# normalidad y solo el panel de Asistente IA mostrará un aviso.
try:
    from core.groq_assistant import responder_con_busqueda as _ia_responder_con_busqueda
    _HAS_IA = True
except Exception:
    _HAS_IA = False


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER — QMessageBox con tema
# ═══════════════════════════════════════════════════════════════════════════════

def _msgbox_style() -> str:
    """Devuelve el stylesheet para aplicar el tema actual a un QMessageBox."""
    return f"""
        QMessageBox {{
            background-color: {c("surface")};
            color: {c("text")};
        }}
        QMessageBox QLabel {{
            color: {c("text")};
            background: transparent;
            font-size: 13px;
        }}
        QMessageBox QPushButton {{
            background: {c("surface2")};
            color: {c("text")};
            border: 1px solid {c("border")};
            border-radius: 8px;
            padding: 6px 18px;
            font-size: 13px;
            min-width: 80px;
        }}
        QMessageBox QPushButton:hover {{
            background: {c("primary_t")};
            color: {c("active_text")};
            border-color: {c("primary")};
        }}
        QMessageBox QPushButton:pressed {{
            background: {c("primary")};
            color: #ffffff;
        }}
    """


# ═══════════════════════════════════════════════════════════════════════════════
#  PALETAS
# ═══════════════════════════════════════════════════════════════════════════════

LIGHT = {
    "bg":           "#F3F4F6",
    "sidebar":      "#FFFFFF",
    "surface":      "#FFFFFF",
    "surface2":     "#F8F9FA",
    "border":       "#E5E7EB",
    "primary":      "#1A73E8",
    "primary_h":    "#1557B0",
    "primary_t":    "#E8F0FE",
    "on_primary":   "#FFFFFF",
    "text":         "#1F2937",
    "text2":        "#6B7280",
    "text3":        "#9CA3AF",
    "success":      "#188038",
    "success_bg":   "#E6F4EA",
    "danger":       "#D93025",
    "danger_bg":    "#FCE8E6",
    "danger_h":     "#B02314",
    "active_item":  "#E8F0FE",
    "active_text":  "#1A73E8",
    "ring_track":   "#E8EAED",
    "ring_fg":      "#1A73E8",
}

DARK = {
    "bg":           "#0F1117",
    "sidebar":      "#1C1E26",
    "surface":      "#1C1E26",
    "surface2":     "#252730",
    "border":       "#2D2F3A",
    "primary":      "#8AB4F8",
    "primary_h":    "#AFC8FF",
    "primary_t":    "#1E3050",
    "on_primary":   "#0F1117",
    "text":         "#E8EAED",
    "text2":        "#9AA0A6",
    "text3":        "#5F6368",
    "success":      "#81C995",
    "success_bg":   "#0D2B1A",
    "danger":       "#F28B82",
    "danger_bg":    "#2D1212",
    "danger_h":     "#EE675C",
    "active_item":  "#1E3050",
    "active_text":  "#8AB4F8",
    "ring_track":   "#2D2F3A",
    "ring_fg":      "#8AB4F8",
}

_T = LIGHT.copy()


def c(key: str) -> str:
    return _T[key]


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def set_font(widget, size=13, bold=False, family="Segoe UI"):
    f = QFont(family, size)
    f.setBold(bold)
    widget.setFont(f)
    return widget


def make_label(text, size=13, bold=False, color_key="text", parent=None):
    w = QLabel(text, parent)
    set_font(w, size, bold)
    w.setStyleSheet(f"color: {c(color_key)}; background: transparent; border: none;")
    return w


def h_line():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {c('border')}; border: none;")
    return line


# ═══════════════════════════════════════════════════════════════════════════════
#  FADE-IN
# ═══════════════════════════════════════════════════════════════════════════════

class FadeIn(QObject):
    def __init__(self, widget, duration=350):
        super().__init__(widget)
        self.fx = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(self.fx)
        self.anim = QPropertyAnimation(self.fx, b"opacity")
        self.anim.setDuration(duration)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANILLO POMODORO
# ═══════════════════════════════════════════════════════════════════════════════

class RingWidget(QWidget):
    def __init__(self, size=240, parent=None, color=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._fraction = 1.0
        self._color = color  # None = usa el color del tema (ring_fg)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_fraction(self, v: float):
        self._fraction = max(0.0, min(1.0, v))
        self.update()

    def set_color(self, color: str):
        self._color = color
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        m = 16
        rect = QRect(m, m, self._size - 2*m, self._size - 2*m)

        pen_track = QPen(QColor(c("ring_track")), 13, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap)
        p.setPen(pen_track)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        if self._fraction > 0:
            pen_fg = QPen(QColor(self._color or c("ring_fg")), 13, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap)
            p.setPen(pen_fg)
            span = int(self._fraction * 360 * 16)
            p.drawArc(rect, 90 * 16, -span)
        p.end()


# ═══════════════════════════════════════════════════════════════════════════════
#  BOTÓN NAVEGACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class NavButton(QPushButton):
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}   {text}", parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        set_font(self, 14)
        self._apply_style()

    def _apply_style(self):
        if self.isChecked():
            bg, fg = c("active_item"), c("active_text")
        else:
            bg, fg = "transparent", c("text2")
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: none;
                border-radius: 10px;
                text-align: left;
                padding-left: 8px;
            }}
            QPushButton:hover {{
                background: {c("active_item")};
                color: {c("active_text")};
            }}
        """)

    def setChecked(self, v):
        super().setChecked(v)
        self._apply_style()

    def refresh(self):
        self._apply_style()


# ═══════════════════════════════════════════════════════════════════════════════
#  BOTONES PRIMARIO / GHOST
# ═══════════════════════════════════════════════════════════════════════════════

def primary_btn(text, w=None, h=42, danger=False):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if w:
        btn.setFixedWidth(w)
    btn.setFixedHeight(h)
    set_font(btn, 13, bold=True)
    style_primary(btn, danger)
    return btn


def style_primary(btn, danger=False):
    bg  = c("danger")   if danger else c("primary")
    bgh = c("danger_h") if danger else c("primary_h")
    fg  = c("on_primary")
    r   = btn.height() // 2
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {bg};
            color: {fg};
            border: none;
            border-radius: {r}px;
            padding: 0 22px;
        }}
        QPushButton:hover {{ background: {bgh}; }}
        QPushButton:pressed {{ padding-top: 1px; }}
    """)


def ghost_btn(text, w=None, h=42, danger=False):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if w:
        btn.setFixedWidth(w)
    btn.setFixedHeight(h)
    set_font(btn, 13)
    style_ghost(btn, danger)
    return btn


def style_ghost(btn, danger=False):
    fg  = c("danger") if danger else c("text2")
    bgh = c("danger_bg") if danger else c("surface2")
    r   = btn.height() // 2
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {fg};
            border: 1.5px solid {fg};
            border-radius: {r}px;
            padding: 0 20px;
        }}
        QPushButton:hover {{ background: {bgh}; }}
        QPushButton:pressed {{ padding-top: 1px; }}
    """)


# ═══════════════════════════════════════════════════════════════════════════════
#  CARD
# ═══════════════════════════════════════════════════════════════════════════════

class Card(QFrame):
    def __init__(self, parent=None, radius=18):
        super().__init__(parent)
        self._r = radius
        self.refresh()

    def refresh(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {c("surface")};
                border: 1px solid {c("border")};
                border-radius: {self._r}px;
            }}
        """)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENCABEZADO
# ═══════════════════════════════════════════════════════════════════════════════

class SectionHeader(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(62)
        self._title = title
        lay = QHBoxLayout(self)
        lay.setContentsMargins(28, 0, 28, 0)
        self._lbl = QLabel(title)
        f = QFont("Segoe UI", 19)
        f.setBold(True)
        self._lbl.setFont(f)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._lbl)
        self.refresh()

    def refresh(self):
        self.setStyleSheet(f"background: {c('surface')}; border-bottom: 1px solid {c('border')};")
        self._lbl.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")


# ═══════════════════════════════════════════════════════════════════════════════
#  GRÁFICO DE BARRAS VERTICALES (para EstadisticasPanel)
# ═══════════════════════════════════════════════════════════════════════════════

class BarChartWidget(QWidget):
    """Gráfico de barras verticales pintado con QPainter. Sin dependencias externas."""

    COLOR_DESCANSO = "#F4B400"   # ámbar, distinto del azul primario (estudio)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions = []   # lista de dicts {'nombre': str, 'minutos': int, 'minutos_descanso': int}
        self.setMinimumHeight(270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_data(self, sessions: list):
        """Recibe la lista de sesiones y redibuja."""
        self._sessions = sessions
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        # ── Sin datos ──────────────────────────────────────────────────────────
        if not self._sessions:
            p.setPen(QColor(c("text2")))
            p.setFont(QFont("Segoe UI", 12))
            p.drawText(QRect(0, 0, W, H),
                       Qt.AlignmentFlag.AlignCenter,
                       "Sin sesiones guardadas todavía")
            p.end()
            return

        # ── Márgenes ───────────────────────────────────────────────────────────
        PAD_L, PAD_R, PAD_T, PAD_B = 54, 20, 42, 56
        chart_w = W - PAD_L - PAD_R
        chart_h = H - PAD_T - PAD_B

        valores_estudio  = [s["minutos"] for s in self._sessions]
        valores_descanso = [s.get("minutos_descanso", 0) for s in self._sessions]
        max_val = max(valores_estudio + valores_descanso + [1])
        n       = len(self._sessions)
        slot_w  = chart_w / n
        group_w = max(20.0, min(96.0, slot_w * 0.62))
        bar_w   = max(6.0, group_w / 2 - 2)

        # ── Líneas de cuadrícula horizontales ─────────────────────────────────
        grid_steps = 4
        for i in range(1, grid_steps + 1):
            ratio = i / grid_steps
            gy = int(PAD_T + chart_h * (1 - ratio))
            p.setPen(QPen(QColor(c("border")), 1, Qt.PenStyle.DashLine))
            p.drawLine(PAD_L, gy, W - PAD_R, gy)
            # Etiqueta eje Y
            lbl_str = str(int(max_val * ratio))
            p.setPen(QColor(c("text2")))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRect(0, gy - 9, PAD_L - 6, 18),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       lbl_str)

        # ── Ejes ──────────────────────────────────────────────────────────────
        axis_pen = QPen(QColor(c("text2")), 1.5)
        p.setPen(axis_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(PAD_L, PAD_T, PAD_L, H - PAD_B)
        p.drawLine(PAD_L, H - PAD_B, W - PAD_R, H - PAD_B)

        # ── Colores ──────────────────────────────────────────────────────────
        color_estudio = QColor(c("primary"))
        color_estudio.setAlpha(210)
        color_descanso = QColor(self.COLOR_DESCANSO)
        color_descanso.setAlpha(210)

        # ── Leyenda (arriba a la derecha) ───────────────────────────────────
        leg_x = W - PAD_R - 176
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color_estudio)
        p.drawRoundedRect(QRectF(leg_x, 8, 12, 12), 3, 3)
        p.setPen(QColor(c("text2")))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRect(int(leg_x) + 18, 4, 78, 20),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Estudio")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color_descanso)
        p.drawRoundedRect(QRectF(leg_x + 88, 8, 12, 12), 3, 3)
        p.setPen(QColor(c("text2")))
        p.drawText(QRect(int(leg_x) + 88 + 18, 4, 78, 20),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Descanso")

        # ── Barras (agrupadas: estudio + descanso por sesión) ─────────────────
        for i, s in enumerate(self._sessions):
            x_center = PAD_L + slot_w * i + slot_w / 2
            gx       = x_center - group_w / 2

            m_estudio  = s["minutos"]
            m_descanso = s.get("minutos_descanso", 0)

            # Barra de estudio
            bx1 = gx
            bh1 = max(4.0, chart_h * m_estudio / max_val) if m_estudio > 0 else 0.0
            by1 = H - PAD_B - bh1
            if bh1 > 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color_estudio)
                p.drawRoundedRect(QRectF(bx1, by1, bar_w, bh1), 4, 4)
                p.setPen(QColor(c("text")))
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                p.drawText(QRect(int(bx1 - 8), int(by1) - 18, int(bar_w + 16), 16),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                           f"{m_estudio}m")

            # Barra de descanso
            bx2 = gx + bar_w + 4
            bh2 = max(4.0, chart_h * m_descanso / max_val) if m_descanso > 0 else 0.0
            by2 = H - PAD_B - bh2
            if bh2 > 0:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(color_descanso)
                p.drawRoundedRect(QRectF(bx2, by2, bar_w, bh2), 4, 4)
                p.setPen(QColor(c("text")))
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                p.drawText(QRect(int(bx2 - 8), int(by2) - 18, int(bar_w + 16), 16),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                           f"{m_descanso}m")

            # Etiqueta eje X  (S1, S2, …)
            p.setPen(QColor(c("text2")))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(QRect(int(gx - 10), H - PAD_B + 6, int(group_w + 20), 22),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       f"S{i + 1}")

        p.end()


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL POMODORO
# ═══════════════════════════════════════════════════════════════════════════════

class PomodoroPanel(QWidget):
    sesion_guardada = pyqtSignal()

    ESTUDIO_SEG  = 25 * 60
    DESCANSO_SEG = 5  * 60

    def __init__(self, cerebro, parent=None):
        super().__init__(parent)
        self.cerebro = cerebro

        self._tiempo_inicial = self.ESTUDIO_SEG
        self._segundos       = self.ESTUDIO_SEG
        self._corriendo      = False
        self._en_descanso    = False
        self._seg_descanso   = self.DESCANSO_SEG
        self._descanso_registrado = True   # no hay descanso en curso al iniciar

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        self._timer_descanso = QTimer(self)
        self._timer_descanso.setInterval(1000)
        self._timer_descanso.timeout.connect(self._tick_descanso)

        self._timer_reloj = QTimer(self)
        self._timer_reloj.setInterval(1000)
        self._timer_reloj.timeout.connect(self._actualizar_reloj)
        self._timer_reloj.start()

        self._player     = None
        self._playlist   = []
        self._music_dir  = None

        self._build()

    # ─────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = SectionHeader("Zona de enfoque")
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.bg_widget)
        vbox.setContentsMargins(32, 28, 32, 28)
        vbox.setSpacing(18)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # ── Card principal: ambos contadores lado a lado ──────────
        self.card = Card()
        self.card.setMaximumWidth(860)
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(40, 28, 40, 28)
        cl.setSpacing(0)

        # Hora actual centrada
        self.lbl_hora_actual = make_label("00:00:00", 14, color_key="text2")
        self.lbl_hora_actual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.lbl_hora_actual)
        cl.addSpacing(16)

        # Fila de los dos contadores
        timers_row = QHBoxLayout()
        timers_row.setSpacing(24)
        timers_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # ── Bloque CONCENTRACIÓN ────────────────────────────────
        col_estudio = QVBoxLayout()
        col_estudio.setSpacing(6)
        col_estudio.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        lbl_titulo_estudio = make_label("📚  Concentración", 12, bold=True, color_key="primary")
        lbl_titulo_estudio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_estudio.addWidget(lbl_titulo_estudio)

        ring_container = QWidget()
        ring_container.setFixedSize(200, 200)
        ring_container.setStyleSheet("background: transparent;")
        self.ring = RingWidget(200, ring_container)
        self.lbl_clock = QLabel("25:00", ring_container)
        set_font(self.lbl_clock, 38, bold=True)
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clock.setFixedSize(200, 200)
        self.lbl_clock.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        col_estudio.addWidget(ring_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.lbl_estado = make_label("Listo para comenzar", 12, color_key="text2")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_estudio.addWidget(self.lbl_estado)

        timers_row.addLayout(col_estudio)

        # ── Separador vertical ──────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {c('border')}; border: none;")
        timers_row.addWidget(sep)

        # ── Bloque DESCANSO ─────────────────────────────────────
        col_descanso = QVBoxLayout()
        col_descanso.setSpacing(6)
        col_descanso.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.lbl_titulo_descanso = make_label("☕  Descanso", 12, bold=True, color_key="text3")
        self.lbl_titulo_descanso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_descanso.addWidget(self.lbl_titulo_descanso)

        ring_descanso_container = QWidget()
        ring_descanso_container.setFixedSize(200, 200)
        ring_descanso_container.setStyleSheet("background: transparent;")
        self.ring_descanso = RingWidget(200, ring_descanso_container, color="#555566")
        self.lbl_descanso_clock = QLabel("05:00", ring_descanso_container)
        set_font(self.lbl_descanso_clock, 38, bold=True)
        self.lbl_descanso_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_descanso_clock.setFixedSize(200, 200)
        self.lbl_descanso_clock.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        col_descanso.addWidget(ring_descanso_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.lbl_descanso_estado = make_label("Espera tu descanso", 12, color_key="text3")
        self.lbl_descanso_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col_descanso.addWidget(self.lbl_descanso_estado)

        timers_row.addLayout(col_descanso)
        cl.addLayout(timers_row)
        cl.addSpacing(20)

        # Estadísticas
        stat_lay = QHBoxLayout()
        stat_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.lbl_horas = make_label("Tiempo enfocado: 0 h 0 min", 13, color_key="primary")
        stat_lay.addWidget(self.lbl_horas)
        self.btn_borrar_stat = QPushButton(" 🗑 ")
        self.btn_borrar_stat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_borrar_stat.setStyleSheet(
            f"color: {c('danger')}; background: transparent; border: none; font-size: 15px;"
        )
        self.btn_borrar_stat.clicked.connect(self._borrar_estadisticas)
        stat_lay.addWidget(self.btn_borrar_stat)
        cl.addLayout(stat_lay)
        self._actualizar_estadisticas()
        cl.addSpacing(20)

        # Botones principales
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.btn_start = primary_btn("  ▶  Iniciar", w=150, h=44)
        self.btn_start.clicked.connect(self._toggle)
        self.btn_reset = ghost_btn("↺  Reiniciar", w=140, h=44)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_saltar_descanso = primary_btn("▶  Continuar estudio", w=190, h=44)
        self.btn_saltar_descanso.clicked.connect(self._saltar_descanso)
        self.btn_saltar_descanso.setVisible(False)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_saltar_descanso)
        cl.addLayout(btn_row)
        cl.addSpacing(16)

        # Config minutos
        self.cfg_frame = QFrame()
        self.cfg_frame.setStyleSheet(f"""
            QFrame {{ background: {c("surface2")}; border: 1px solid {c("border")}; border-radius: 12px; }}
        """)
        cfg_lay = QHBoxLayout(self.cfg_frame)
        cfg_lay.setContentsMargins(18, 10, 18, 10)
        cfg_lay.setSpacing(10)
        cfg_lay.addWidget(make_label("📚 Estudio:", 13, color_key="text2"))
        self.entry_min = QLineEdit("25")
        self.entry_min.setFixedSize(52, 34)
        self.entry_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_font(self.entry_min, 13)
        self._style_entry(self.entry_min)
        cfg_lay.addWidget(self.entry_min)
        cfg_lay.addWidget(make_label("min   ☕ Descanso:", 13, color_key="text2"))
        self.entry_descanso = QLineEdit("5")
        self.entry_descanso.setFixedSize(52, 34)
        self.entry_descanso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_font(self.entry_descanso, 13)
        self._style_entry(self.entry_descanso)
        cfg_lay.addWidget(self.entry_descanso)
        cfg_lay.addWidget(make_label("min", 13, color_key="text2"))
        self.btn_apply = primary_btn("Aplicar", w=110, h=34)
        self.btn_apply.clicked.connect(self._apply_time)
        cfg_lay.addWidget(self.btn_apply)
        cl.addWidget(self.cfg_frame, alignment=Qt.AlignmentFlag.AlignHCenter)

        vbox.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── Card música ─────────────────────────────────────────
        self.card_musica = Card()
        self.card_musica.setMaximumWidth(900)
        cm = QVBoxLayout(self.card_musica)
        cm.setContentsMargins(32, 22, 32, 22)
        cm.setSpacing(12)

        cm.addWidget(make_label("🎵  Música de fondo", 14, bold=True))

        # Fila 1: carpeta + archivo suelto + combo
        fila_musica = QHBoxLayout()
        fila_musica.setSpacing(8)
        self.btn_elegir_musica = ghost_btn("📁  Carpeta", w=140, h=40)
        self.btn_elegir_musica.clicked.connect(self._elegir_carpeta_musica)
        fila_musica.addWidget(self.btn_elegir_musica)
        self.btn_subir_archivo = ghost_btn("🎵  Archivo", w=140, h=40)
        self.btn_subir_archivo.clicked.connect(self._subir_archivo_musica)
        fila_musica.addWidget(self.btn_subir_archivo)
        self.combo_musica = QComboBox()
        self.combo_musica.setMinimumWidth(180)
        self.combo_musica.setFixedHeight(36)
        self._style_combo_musica()
        self.combo_musica.addItem("— sin canciones —")
        self.combo_musica.currentIndexChanged.connect(self._cambiar_cancion)
        fila_musica.addWidget(self.combo_musica, stretch=1)
        cm.addLayout(fila_musica)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        ctrl_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.btn_play_pause_music = ghost_btn("▶", w=54, h=42)
        self.btn_prev_music  = ghost_btn("⏮", w=54, h=42)
        self.btn_next_music  = ghost_btn("⏭", w=54, h=42)
        self.btn_play_pause_music.clicked.connect(self._music_toggle)
        self.btn_prev_music.clicked.connect(self._music_prev)
        self.btn_next_music.clicked.connect(self._music_next)
        for b in (self.btn_prev_music, self.btn_play_pause_music, self.btn_next_music):
            ctrl_row.addWidget(b)
        self.lbl_cancion_actual = make_label("Sin reproducción", 11, color_key="text2")
        self.lbl_cancion_actual.setWordWrap(True)
        ctrl_row.addWidget(self.lbl_cancion_actual, stretch=1)
        cm.addLayout(ctrl_row)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(8)
        vol_row.addWidget(make_label("🔊", 13))
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(60)
        self.slider_vol.setFixedWidth(160)
        self._style_slider()
        self.slider_vol.valueChanged.connect(self._cambiar_volumen)
        vol_row.addWidget(self.slider_vol)
        self.lbl_vol = make_label("60%", 11, color_key="text2")
        vol_row.addWidget(self.lbl_vol)
        vol_row.addStretch()
        cm.addLayout(vol_row)

        vbox.addWidget(self.card_musica, alignment=Qt.AlignmentFlag.AlignHCenter)

        scroll.setWidget(self.bg_widget)
        root.addWidget(scroll)
        FadeIn(self.bg_widget)
        self._actualizar_reloj()
        self._init_player()

    # ─────────────────────────────────────────────────────────────
    def _actualizar_reloj(self):
        from datetime import datetime
        self.lbl_hora_actual.setText(f"🕐  {datetime.now().strftime('%H:%M:%S')}")

    # ── Estudio ──────────────────────────────────────────────────
    def _toggle(self):
        if not self._corriendo:
            self._corriendo = True
            self._timer.start()
            self.btn_start.setText("  ⏸  Pausar")
            style_primary(self.btn_start, danger=True)
            self.lbl_estado.setText("En sesión de enfoque…")
            if self._playlist:
                self._music_play()
        else:
            self._corriendo = False
            self._timer.stop()
            self.btn_start.setText("  ▶  Reanudar")
            style_primary(self.btn_start, danger=False)
            self.lbl_estado.setText("En pausa")
            self._music_pause()

    def _tick(self):
        if self._segundos > 0:
            self._segundos -= 1
            m, s = divmod(self._segundos, 60)
            self.lbl_clock.setText(f"{m:02d}:{s:02d}")
            self.ring.set_fraction(self._segundos / self._tiempo_inicial)
        else:
            self._timer.stop()
            self._corriendo = False
            self._music_pause()
            self._reproducir_sonido_fin()
            self.cerebro.guardar_pomodoro(self._tiempo_inicial // 60)
            self._actualizar_estadisticas()
            self.btn_start.setText("  ▶  Iniciar")
            style_primary(self.btn_start, danger=False)
            self.btn_start.setEnabled(False)
            self.lbl_estado.setText("✓ ¡Sesión completa!")
            self._iniciar_descanso()

    def _reset(self):
        if self._en_descanso:
            self._registrar_descanso_transcurrido()
        self._timer.stop()
        self._timer_descanso.stop()
        self._corriendo    = False
        self._en_descanso  = False
        self._segundos     = self._tiempo_inicial
        self._seg_descanso = self.DESCANSO_SEG
        self._descanso_registrado = True
        m = self._tiempo_inicial // 60
        self.lbl_clock.setText(f"{m:02d}:00")
        self.ring.set_fraction(1.0)
        m_d, s_d = divmod(self.DESCANSO_SEG, 60)
        self.lbl_descanso_clock.setText(f"{m_d:02d}:{s_d:02d}")
        self.ring_descanso.set_fraction(1.0)
        self.ring_descanso.set_color("#555566")
        self.lbl_titulo_descanso.setStyleSheet(f"color: {c('text3')}; background: transparent; border: none;")
        self.lbl_descanso_clock.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_descanso_estado.setText("Espera tu descanso")
        self.btn_start.setText("  ▶  Iniciar")
        style_primary(self.btn_start, danger=False)
        self.btn_start.setEnabled(True)
        self.btn_saltar_descanso.setVisible(False)
        self.lbl_estado.setText("Listo para comenzar")
        self._music_pause()

    def _apply_time(self):
        try:
            mins = int(self.entry_min.text())
            mins_descanso = int(self.entry_descanso.text())
            if mins > 0:
                self._tiempo_inicial = mins * 60
            if mins_descanso > 0:
                self.DESCANSO_SEG = mins_descanso * 60
            self._reset()   # _reset ya usa self.DESCANSO_SEG para actualizar el label
        except ValueError:
            pass

    # ── Descanso ─────────────────────────────────────────────────
    def _iniciar_descanso(self):
        self._en_descanso  = True
        self._seg_descanso = self.DESCANSO_SEG
        self._descanso_registrado = False
        self.ring_descanso.set_fraction(1.0)
        self.ring_descanso.set_color("#5B9BD5")   # azul suave = activo
        self.lbl_titulo_descanso.setStyleSheet(f"color: {c('primary')}; background: transparent; border: none;")
        self.lbl_descanso_clock.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_descanso_estado.setText("☕ Descansa — música pausada")
        self.btn_saltar_descanso.setVisible(True)
        self._timer_descanso.start()

    def _tick_descanso(self):
        if self._seg_descanso > 0:
            self._seg_descanso -= 1
            m, s = divmod(self._seg_descanso, 60)
            self.lbl_descanso_clock.setText(f"{m:02d}:{s:02d}")
            self.ring_descanso.set_fraction(self._seg_descanso / self.DESCANSO_SEG)
        else:
            self._timer_descanso.stop()
            self.lbl_descanso_estado.setText("⏰ ¡Descanso listo! ¿Continúas?")
            self.lbl_descanso_clock.setText("00:00")
            # El descanso se completó entero: lo registramos ya mismo, sin
            # esperar a que el usuario presione "Continuar estudio". Así,
            # si guarda las estadísticas justo en este momento, el
            # descanso ya cuenta.
            self._registrar_descanso_transcurrido()

    def _registrar_descanso_transcurrido(self):
        """Guarda en el acumulador el descanso realmente transcurrido
        (completo o interrumpido) y evita registrarlo dos veces."""
        if self._descanso_registrado:
            return
        segundos_transcurridos = self.DESCANSO_SEG - self._seg_descanso
        minutos_descanso = segundos_transcurridos // 60
        if minutos_descanso > 0:
            self.cerebro.guardar_descanso(minutos_descanso)
            self._actualizar_estadisticas()
        self._descanso_registrado = True

    def _saltar_descanso(self):
        self._timer_descanso.stop()
        self._en_descanso = False
        self.btn_saltar_descanso.setVisible(False)

        # Guardar el tiempo de descanso realmente transcurrido, salvo que ya
        # se haya registrado (por ejemplo, si el descanso terminó solo).
        self._registrar_descanso_transcurrido()

        self._segundos = self._tiempo_inicial
        m = self._tiempo_inicial // 60
        self.lbl_clock.setText(f"{m:02d}:00")
        self.ring.set_fraction(1.0)
        self.ring_descanso.set_fraction(1.0)
        self.ring_descanso.set_color("#555566")
        self.lbl_titulo_descanso.setStyleSheet(f"color: {c('text3')}; background: transparent; border: none;")
        self.lbl_descanso_clock.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_descanso_estado.setText("Espera tu descanso")
        m_d2, s_d2 = divmod(self.DESCANSO_SEG, 60)
        self.lbl_descanso_clock.setText(f"{m_d2:02d}:{s_d2:02d}")
        self.btn_start.setEnabled(True)
        self.btn_start.setText("  ▶  Iniciar")
        style_primary(self.btn_start, danger=False)
        self.lbl_estado.setText("Listo para comenzar")

    # ── Música ───────────────────────────────────────────────────
    def _init_player(self):
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            self._audio_output.setVolume(0.6)
            self._player.mediaStatusChanged.connect(self._on_media_status)
            self._player.playbackStateChanged.connect(self._actualizar_boton_play_pause)
        except Exception:
            self._player = None

    def _elegir_carpeta_musica(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de música")
        if not carpeta:
            return
        exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
        nuevas = sorted(
            [p for p in Path(carpeta).iterdir() if p.suffix.lower() in exts],
            key=lambda p: p.name
        )
        if not nuevas:
            self.lbl_cancion_actual.setText("No se encontraron archivos de audio")
            return
        self._agregar_a_playlist(nuevas)

    def _subir_archivo_musica(self):
        """Permite seleccionar uno o varios archivos de audio sueltos."""
        rutas, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar archivo(s) de música", "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)"
        )
        if not rutas:
            return
        self._agregar_a_playlist([Path(r) for r in rutas])

    def _agregar_a_playlist(self, paths: list):
        """Agrega rutas a la playlist y actualiza el combo."""
        # Evitar duplicados
        existentes = {str(p) for p in self._playlist}
        nuevas = [p for p in paths if str(p) not in existentes]
        self._playlist.extend(nuevas)
        self.combo_musica.blockSignals(True)
        self.combo_musica.clear()
        for p in self._playlist:
            self.combo_musica.addItem(p.name)
        self.combo_musica.blockSignals(False)
        if nuevas:
            # Seleccionar la primera nueva
            idx = self._playlist.index(nuevas[0])
            self.combo_musica.setCurrentIndex(idx)
            self._cargar_cancion(idx)

    def _cargar_cancion(self, idx):
        if not self._player or idx < 0 or idx >= len(self._playlist):
            return
        from PyQt6.QtCore import QUrl
        self._player.setSource(QUrl.fromLocalFile(str(self._playlist[idx])))
        self.lbl_cancion_actual.setText(self._playlist[idx].name)
        self._player.play()

    def _cambiar_cancion(self, idx):
        if self._playlist:
            self._cargar_cancion(idx)

    def _music_toggle(self):
        if not self._player:
            return
        from PyQt6.QtMultimedia import QMediaPlayer
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._music_pause()
        else:
            self._music_play()

    def _actualizar_boton_play_pause(self, _state=None):
        if not self._player:
            return
        from PyQt6.QtMultimedia import QMediaPlayer
        en_reproduccion = self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.btn_play_pause_music.setText("⏸" if en_reproduccion else "▶")

    def _music_play(self):
        if self._player and self._playlist:
            self._player.play()

    def _music_pause(self):
        if self._player:
            self._player.pause()

    def _music_prev(self):
        if not self._playlist: return
        idx = max(0, self.combo_musica.currentIndex() - 1)
        self.combo_musica.setCurrentIndex(idx)

    def _music_next(self):
        if not self._playlist: return
        idx = (self.combo_musica.currentIndex() + 1) % len(self._playlist)
        self.combo_musica.setCurrentIndex(idx)

    def _cambiar_volumen(self, val):
        self.lbl_vol.setText(f"{val}%")
        if self._player:
            self._audio_output.setVolume(val / 100)

    def _on_media_status(self, status):
        try:
            from PyQt6.QtMultimedia import QMediaPlayer
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                self._music_next()
        except Exception:
            pass

    def _reproducir_sonido_fin(self):
        import threading, platform
        def _play():
            try:
                if platform.system() == "Windows":
                    import winsound
                    for _ in range(3):
                        winsound.Beep(880, 200)
                        import time; time.sleep(0.1)
            except Exception:
                pass
            QApplication.beep()
        threading.Thread(target=_play, daemon=True).start()

    # ── Estadísticas ─────────────────────────────────────────────
    def _actualizar_estadisticas(self):
        try:
            self.lbl_horas.setText(f"Tiempo enfocado: {self.cerebro.obtener_texto_estadisticas()}")
        except Exception:
            self.lbl_horas.setText("Tiempo enfocado: 0 h 0 min")

    def _borrar_estadisticas(self):
        # Si hay un descanso en curso (aún contando) que todavía no se
        # registró, sumamos el tiempo transcurrido hasta ahora antes de
        # guardar o borrar, para no perderlo.
        if self._en_descanso:
            self._registrar_descanso_transcurrido()

        box = QMessageBox(self)
        box.setWindowTitle("Historial de Enfoque")
        box.setText("¿Desea guardar el tiempo acumulado como sesión oficial?")
        box.setIcon(QMessageBox.Icon.Question)
        btn_si      = box.addButton("  Sí, guardar  ",            QMessageBox.ButtonRole.YesRole)
        btn_no      = box.addButton("  No, borrar sin guardar  ", QMessageBox.ButtonRole.NoRole)
        _btn_cancel = box.addButton("  Cancelar  ",               QMessageBox.ButtonRole.RejectRole)
        box.setStyleSheet(f"""
            QMessageBox {{ background: {c('surface')}; color: {c('text')}; }}
            QLabel {{ color: {c('text')}; background: transparent; font-size: 13px; }}
            QPushButton {{
                background: {c('surface2')}; color: {c('text')};
                border: 1px solid {c('border')}; border-radius: 8px;
                padding: 6px 18px; font-size: 13px; min-width: 80px;
            }}
            QPushButton:hover {{ background: {c('primary_t')}; border-color: {c('primary')}; }}
        """)
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_si:
            exito = self.cerebro.consolidar_sesion_actual()
            self.lbl_estado.setText("✓ ¡Sesión guardada!" if exito else "No hay tiempo suficiente")
            if exito:
                self.sesion_guardada.emit()
            self._actualizar_estadisticas()
        elif clicked == btn_no:
            self.cerebro.borrar_historial_pomodoro()
            self._actualizar_estadisticas()
            self.lbl_estado.setText("Tiempo temporal reiniciado")

    # ── Estilos ───────────────────────────────────────────────────
    def _style_entry(self, w):
        w.setStyleSheet(f"""
            QLineEdit {{
                background: {c("surface")}; color: {c("text")};
                border: 1px solid {c("border")}; border-radius: 8px; padding: 2px 6px;
            }}
            QLineEdit:focus {{ border-color: {c("primary")}; }}
        """)

    def _style_combo_musica(self):
        self.combo_musica.setStyleSheet(f"""
            QComboBox {{
                background: {c("surface2")}; color: {c("text")};
                border: 1px solid {c("border")}; border-radius: 8px;
                padding: 4px 10px; font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background: {c("surface")}; color: {c("text")};
                border: 1px solid {c("border")}; selection-background-color: {c("primary_t")};
            }}
        """)

    def _style_slider(self):
        self.slider_vol.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {c('border')}; height: 4px; border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {c('primary')}; width: 14px; height: 14px;
                border-radius: 7px; margin: -5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {c('primary')}; border-radius: 2px;
            }}
        """)

    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        self.header.refresh()
        self.card.refresh()
        self.card_musica.refresh()
        self.lbl_clock.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_hora_actual.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_estado.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.ring.update()
        self.ring_descanso.update()
        style_primary(self.btn_start)
        style_ghost(self.btn_reset)
        style_primary(self.btn_apply)
        style_primary(self.btn_saltar_descanso)
        style_ghost(self.btn_elegir_musica)
        style_ghost(self.btn_play_pause_music)
        style_ghost(self.btn_prev_music)
        style_ghost(self.btn_next_music)
        self._style_entry(self.entry_min)
        self._style_entry(self.entry_descanso)
        style_ghost(self.btn_subir_archivo)
        self._style_combo_musica()
        self._style_slider()
        self.btn_borrar_stat.setStyleSheet(
            f"color: {c('danger')}; background: transparent; border: none; font-size: 15px;"
        )
        self.cfg_frame.setStyleSheet(f"""
            QFrame {{ background: {c("surface2")}; border: 1px solid {c("border")}; border-radius: 12px; }}
        """)



# ═══════════════════════════════════════════════════════════════════════════════
#  HILO DE TRABAJO: INGESTA DE PDF
# ═══════════════════════════════════════════════════════════════════════════════

class PDFIngestWorker(QThread):
    """
    Procesa un PDF en un hilo separado para no congelar la interfaz
    mientras se extrae el texto (los PDFs grandes pueden tardar varios
    segundos).
    """
    exito = pyqtSignal(int, str)   # (cantidad_de_fragmentos, nombre_archivo)
    error = pyqtSignal(str)        # mensaje de error

    def __init__(self, cerebro, ruta_pdf: str, categoria: str, parent=None):
        super().__init__(parent)
        self.cerebro = cerebro
        self.ruta_pdf = ruta_pdf
        self.categoria = categoria

    def run(self):
        try:
            cantidad = self.cerebro.ingestar_pdf(self.ruta_pdf, self.categoria)
            nombre = os.path.basename(self.ruta_pdf)
            self.exito.emit(cantidad, nombre)
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  EDITOR DE TEXTO ENRIQUECIDO  (barra de herramientas + QTextEdit con HTML)
# ═══════════════════════════════════════════════════════════════════════════════

class RichTextEditor(QWidget):
    """
    Editor con mini-barra de herramientas: Negrita, Cursiva, Subrayado, Lista.
    Expone la misma API básica que QTextEdit:
      .toPlainText()  .toHtml()  .clear()  .setPlainText()  .setHtml()
    """

    def __init__(self, min_height=180, parent=None):
        super().__init__(parent)
        self._build(min_height)

    # ── Construcción ──────────────────────────────────────────────────────────
    def _build(self, min_height):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ─ Barra de herramientas ─────────────────────────────────────────────
        self.toolbar = QFrame()
        self.toolbar.setFixedHeight(40)
        self._style_toolbar()
        tb_lay = QHBoxLayout(self.toolbar)
        tb_lay.setContentsMargins(8, 4, 8, 4)
        tb_lay.setSpacing(4)

        self._btn_bold      = self._make_tb_btn("B",  "Negrita (Ctrl+B)",   bold=True)
        self._btn_italic    = self._make_tb_btn("I",  "Cursiva (Ctrl+I)",   italic=True)
        self._btn_underline = self._make_tb_btn("U",  "Subrayado (Ctrl+U)", underline=True)
        self._btn_list      = self._make_tb_btn("☰",  "Lista con viñetas",  size=15)

        for btn in (self._btn_bold, self._btn_italic,
                    self._btn_underline, self._btn_list):
            tb_lay.addWidget(btn)

        # Separador
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {c('border')}; border: none;")
        tb_lay.addWidget(sep)

        # Selector de tamaño de fuente
        self._font_size_combo = QComboBox()
        self._font_size_combo.addItems(["11", "12", "13", "14", "16", "18", "22"])
        self._font_size_combo.setCurrentText("14")
        self._font_size_combo.setFixedSize(60, 28)
        self._font_size_combo.setToolTip("Tamaño de fuente")
        set_font(self._font_size_combo, 11)
        self._font_size_combo.currentTextChanged.connect(self._apply_font_size)
        tb_lay.addWidget(self._font_size_combo)

        tb_lay.addStretch()
        root.addWidget(self.toolbar)

        # ─ Área de texto ──────────────────────────────────────────────────────
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.setMinimumHeight(min_height)
        set_font(self.editor, 14)
        self._style_editor()
        root.addWidget(self.editor)

        # Atajos de teclado
        self._shortcut_bold      = QAction(self)
        self._shortcut_bold.setShortcut(QKeySequence("Ctrl+B"))
        self._shortcut_bold.triggered.connect(self._toggle_bold)
        self.addAction(self._shortcut_bold)

        self._shortcut_italic    = QAction(self)
        self._shortcut_italic.setShortcut(QKeySequence("Ctrl+I"))
        self._shortcut_italic.triggered.connect(self._toggle_italic)
        self.addAction(self._shortcut_italic)

        self._shortcut_underline = QAction(self)
        self._shortcut_underline.setShortcut(QKeySequence("Ctrl+U"))
        self._shortcut_underline.triggered.connect(self._toggle_underline)
        self.addAction(self._shortcut_underline)

        # Conectar botones
        self._btn_bold.clicked.connect(self._toggle_bold)
        self._btn_italic.clicked.connect(self._toggle_italic)
        self._btn_underline.clicked.connect(self._toggle_underline)
        self._btn_list.clicked.connect(self._toggle_list)

        # Actualizar estado de botones al mover el cursor
        self.editor.cursorPositionChanged.connect(self._sync_toolbar_state)

    # ── Creación de botones de barra ──────────────────────────────────────────
    def _make_tb_btn(self, label, tooltip, bold=False, italic=False,
                     underline=False, size=13):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setFixedSize(30, 28)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        f = QFont("Segoe UI", size)
        f.setBold(bold)
        f.setItalic(italic)
        f.setUnderline(underline)
        btn.setFont(f)
        self._refresh_tb_btn(btn)
        return btn

    def _refresh_tb_btn(self, btn):
        if btn.isChecked():
            bg = c("primary_t")
            fg = c("active_text")
            border = c("primary")
        else:
            bg = "transparent"
            fg = c("text2")
            border = c("border")
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {c("primary_t")};
                color: {c("active_text")};
                border-color: {c("primary")};
            }}
        """)

    # ── Estilos ───────────────────────────────────────────────────────────────
    def _style_toolbar(self):
        self.toolbar.setStyleSheet(f"""
            QFrame {{
                background: {c("surface2")};
                border: 1px solid {c("border")};
                border-bottom: none;
                border-radius: 10px 10px 0 0;
            }}
        """)

    def _style_editor(self):
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                background: {c("surface2")};
                color: {c("text")};
                border: 1px solid {c("border")};
                border-top: none;
                border-radius: 0 0 10px 10px;
                padding: 12px;
            }}
            QTextEdit:focus {{
                border-color: {c("primary")};
            }}
        """)
        # Toolbar border must match editor focus — re-apply to keep consistent
        self._style_toolbar()

    def refresh_theme(self):
        self._style_toolbar()
        self._style_editor()
        for btn in (self._btn_bold, self._btn_italic,
                    self._btn_underline, self._btn_list):
            self._refresh_tb_btn(btn)
        # Combo
        self._font_size_combo.setStyleSheet(f"""
            QComboBox {{
                background: {c("surface")};
                color: {c("text")};
                border: 1px solid {c("border")};
                border-radius: 6px;
                padding: 0 4px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox QAbstractItemView {{
                background: {c("surface")};
                color: {c("text")};
                border: 1px solid {c("border")};
                selection-background-color: {c("primary_t")};
                selection-color: {c("active_text")};
            }}
        """)

    # ── Acciones de formato ───────────────────────────────────────────────────
    def _toggle_bold(self):
        fmt = QTextCharFormat()
        cursor = self.editor.textCursor()
        current_weight = cursor.charFormat().fontWeight()
        new_weight = QFont.Weight.Normal if current_weight == QFont.Weight.Bold else QFont.Weight.Bold
        fmt.setFontWeight(new_weight)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self._sync_toolbar_state()

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        current = self.editor.currentCharFormat().fontItalic()
        fmt.setFontItalic(not current)
        self.editor.mergeCurrentCharFormat(fmt)
        self._sync_toolbar_state()

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        current = self.editor.currentCharFormat().fontUnderline()
        fmt.setFontUnderline(not current)
        self.editor.mergeCurrentCharFormat(fmt)
        self._sync_toolbar_state()

    def _toggle_list(self):
        cursor = self.editor.textCursor()
        current_list = cursor.currentList()
        if current_list:
            # Quitar lista: convertir el bloque a párrafo normal
            block_fmt = cursor.blockFormat()
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
            # Separar del QTextList
            lst = cursor.currentList()
            if lst:
                lst.remove(cursor.block())
            self._btn_list.setChecked(False)
        else:
            # Crear lista con viñetas
            list_fmt = QTextListFormat()
            list_fmt.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_fmt)
            self._btn_list.setChecked(True)
        self._refresh_tb_btn(self._btn_list)

    def _apply_font_size(self, size_str: str):
        try:
            size = int(size_str)
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            self.editor.mergeCurrentCharFormat(fmt)
            self.editor.setFocus()
        except ValueError:
            pass

    def _sync_toolbar_state(self):
        """Actualiza el estado checked de los botones según el cursor actual."""
        fmt = self.editor.currentCharFormat()
        self._btn_bold.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self._btn_italic.setChecked(fmt.fontItalic())
        self._btn_underline.setChecked(fmt.fontUnderline())
        self._btn_list.setChecked(bool(self.editor.textCursor().currentList()))
        for btn in (self._btn_bold, self._btn_italic,
                    self._btn_underline, self._btn_list):
            self._refresh_tb_btn(btn)

    # ── API pública compatible con QTextEdit ──────────────────────────────────
    def toPlainText(self) -> str:
        return self.editor.toPlainText()

    def toHtml(self) -> str:
        return self.editor.toHtml()

    def clear(self):
        self.editor.clear()

    def setPlainText(self, text: str):
        self.editor.setPlainText(text)

    def setHtml(self, html: str):
        self.editor.setHtml(html)

    def setFocus(self):
        self.editor.setFocus()


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL CUADERNO
# ═══════════════════════════════════════════════════════════════════════════════

class CuadernoPanel(QWidget):
    convertir_en_flashcard = pyqtSignal(str)

    def __init__(self, cerebro, parent=None):
        super().__init__(parent)
        self.cerebro = cerebro
        self._pdf_worker = None
        self._apunte_editando_id = None  # None = nuevo apunte; int = modo edición
        self._build()

    # ════════════════════════════════════════════════════════════════
    #  CONSTRUCCIÓN
    # ════════════════════════════════════════════════════════════════
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = SectionHeader("Cuaderno de apuntes")
        root.addWidget(self.header)

        # Tabs: Escribir | Mis apuntes
        self.tab_bar = QWidget()
        self.tab_bar.setFixedHeight(52)
        self.tab_bar.setStyleSheet(f"background: {c('surface')}; border-bottom: 1px solid {c('border')};")
        tb_lay = QHBoxLayout(self.tab_bar)
        tb_lay.setContentsMargins(60, 8, 60, 8)
        tb_lay.setSpacing(8)
        tb_lay.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_tab_escribir  = ghost_btn("  ✏️  Escribir",    w=150, h=36)
        self.btn_tab_historial = ghost_btn("  📋  Mis apuntes", w=160, h=36)
        self.btn_tab_escribir.clicked.connect(lambda: self._cambiar_tab(0))
        self.btn_tab_historial.clicked.connect(lambda: self._cambiar_tab(1))
        tb_lay.addWidget(self.btn_tab_escribir)
        tb_lay.addWidget(self.btn_tab_historial)
        tb_lay.addStretch()
        root.addWidget(self.tab_bar)

        # Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.stack.addWidget(self._build_vista_escribir())   # 0
        self.stack.addWidget(self._build_vista_historial())  # 1
        root.addWidget(self.stack)

        self._cambiar_tab(0)

    # ════════════════════════════════════════════════════════════════
    #  VISTA 0 — ESCRIBIR
    # ════════════════════════════════════════════════════════════════
    def _build_vista_escribir(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {c('bg')};")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.bg_widget)
        vbox.setContentsMargins(60, 36, 60, 36)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.card = Card()
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(0)

        self.lbl_titulo = make_label("Escribe tu apunte", 14, bold=True)
        cl.addWidget(self.lbl_titulo)
        cl.addSpacing(10)

        self.text_box = RichTextEditor(min_height=180)
        self._style_textbox()
        cl.addWidget(self.text_box)
        cl.addSpacing(18)

        self.lbl_cat = make_label("Categoría", 13, color_key="text2")
        cl.addWidget(self.lbl_cat)
        cl.addSpacing(6)

        self.combo = QComboBox()
        self.combo.setFixedHeight(38)
        self.combo.setFixedWidth(220)
        set_font(self.combo, 13)
        self._style_combo()
        cl.addWidget(self.combo)
        cl.addSpacing(22)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.btn_save   = primary_btn("  💾  Guardar",         w=140, h=44)
        self.btn_cancel = ghost_btn("  ✖  Salir de edición",   w=190, h=44, danger=True)
        self.btn_pdf    = ghost_btn("  📄  Subir PDF",          w=160, h=44)
        self.btn_flash  = ghost_btn("  🃏  Flashcard",          w=148, h=44)
        self.btn_export = ghost_btn("  📤  Exportar",           w=148, h=44)
        self.btn_save.clicked.connect(self._save)
        self.btn_cancel.clicked.connect(self._cancelar_edicion)
        self.btn_pdf.clicked.connect(self._subir_pdf)
        self.btn_flash.clicked.connect(self._enviar_a_flashcard)
        self.btn_export.clicked.connect(self._exportar)
        self.btn_cancel.hide()           # solo visible en modo edición
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_pdf)
        btn_row.addWidget(self.btn_flash)
        btn_row.addWidget(self.btn_export)
        cl.addLayout(btn_row)
        cl.addSpacing(16)

        self.lbl_msg = QLabel("")
        set_font(self.lbl_msg, 13)
        self.lbl_msg.setStyleSheet("background: transparent; border: none;")
        cl.addWidget(self.lbl_msg)

        vbox.addWidget(self.card)
        scroll.setWidget(self.bg_widget)
        outer.addWidget(scroll)
        FadeIn(self.bg_widget)
        self._refrescar_categorias(mantener_seleccion=False)
        return w

    # ════════════════════════════════════════════════════════════════
    #  CATEGORÍAS (compartidas con los "cursos" de Flashcards)
    # ════════════════════════════════════════════════════════════════
    def _refrescar_categorias(self, mantener_seleccion: bool = True):
        """Repuebla el combo de categoría desde los cursos de Flashcards."""
        anterior = self.combo.currentText() if mantener_seleccion else None
        self.combo.blockSignals(True)
        self.combo.clear()
        cursos = self.cerebro.obtener_cursos()

        if not cursos:
            self.combo.addItem("— Crea un curso en Flashcards —")
            self.combo.setEnabled(False)
            if hasattr(self, "btn_save"):
                self.btn_save.setEnabled(False)
                self.btn_pdf.setEnabled(False)
        else:
            self.combo.setEnabled(True)
            for curso in cursos:
                self.combo.addItem(curso["nombre"])
            if anterior:
                idx = self.combo.findText(anterior)
                if idx >= 0:
                    self.combo.setCurrentIndex(idx)
            if hasattr(self, "btn_save"):
                self.btn_save.setEnabled(True)
                self.btn_pdf.setEnabled(True)

        self.combo.blockSignals(False)

    def actualizar_categorias(self):
        """Punto de entrada público: llamado cuando cambian los cursos en Flashcards."""
        self._refrescar_categorias()

    # ════════════════════════════════════════════════════════════════
    #  VISTA 1 — HISTORIAL DE APUNTES
    # ════════════════════════════════════════════════════════════════
    def _build_vista_historial(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: {c('bg')};")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.hist_bg = QWidget()
        self.hist_bg.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.hist_bg)
        vbox.setContentsMargins(60, 28, 60, 36)
        vbox.setSpacing(0)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Cabecera con buscador y contador
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self.lbl_hist_titulo = make_label("Todos los apuntes", 16, bold=True)
        top_row.addWidget(self.lbl_hist_titulo)
        top_row.addStretch()

        self.input_filtro = QLineEdit()
        self.input_filtro.setPlaceholderText("🔎  Filtrar…")
        self.input_filtro.setFixedHeight(36)
        self.input_filtro.setFixedWidth(200)
        set_font(self.input_filtro, 13)
        self.input_filtro.textChanged.connect(self._filtrar_apuntes)
        self._style_input_filtro()
        top_row.addWidget(self.input_filtro)

        vbox.addLayout(top_row)
        vbox.addSpacing(8)

        self.lbl_conteo = make_label("", 12, color_key="text2")
        vbox.addWidget(self.lbl_conteo)
        vbox.addSpacing(16)

        # Contenedor de tarjetas
        self.hist_cards_widget = QWidget()
        self.hist_cards_widget.setStyleSheet("background: transparent;")
        self.hist_cards_vlay = QVBoxLayout(self.hist_cards_widget)
        self.hist_cards_vlay.setContentsMargins(0, 0, 0, 0)
        self.hist_cards_vlay.setSpacing(10)
        self.hist_cards_vlay.setAlignment(Qt.AlignmentFlag.AlignTop)
        vbox.addWidget(self.hist_cards_widget)

        scroll.setWidget(self.hist_bg)
        outer.addWidget(scroll)
        return w

    def _cargar_historial(self):
        """Carga todos los apuntes y los renderiza como tarjetas."""
        self._todos_apuntes = self.cerebro.obtener_todos_apuntes()
        self._filtrar_apuntes(self.input_filtro.text())

    def _filtrar_apuntes(self, texto_filtro: str = ""):
        """Re-renderiza las tarjetas según el filtro de texto."""
        filtro = texto_filtro.strip().lower()
        apuntes = self._todos_apuntes if hasattr(self, '_todos_apuntes') else []

        if filtro:
            import re, html as html_lib
            def _plain(t):
                t2 = re.sub(r"<[^>]+>", " ", t)
                return html_lib.unescape(t2).lower()
            apuntes = [a for a in apuntes if filtro in _plain(a["texto"]) or filtro in a["categoria"].lower()]

        # Limpiar tarjetas existentes
        while self.hist_cards_vlay.count():
            item = self.hist_cards_vlay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = len(self._todos_apuntes) if hasattr(self, '_todos_apuntes') else 0
        visibles = len(apuntes)
        if filtro:
            self.lbl_conteo.setText(f"{visibles} de {total} apuntes")
        else:
            self.lbl_conteo.setText(f"{total} apunte{'s' if total != 1 else ''} guardado{'s' if total != 1 else ''}")

        if not apuntes:
            lbl = make_label(
                "No hay apuntes todavía. ¡Escribe tu primero en la pestaña Escribir!" if not filtro
                else "Ningún apunte coincide con el filtro.",
                13, color_key="text2"
            )
            lbl.setWordWrap(True)
            self.hist_cards_vlay.addWidget(lbl)
            return

        for apunte in apuntes:
            self.hist_cards_vlay.addWidget(self._make_apunte_card(apunte))

    def _make_apunte_card(self, apunte: dict) -> QFrame:
        """Crea una tarjeta visual para un apunte con botones de acción."""
        import re, html as html_lib

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {c('surface')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {c('primary')};
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 14)
        lay.setSpacing(8)

        # ── Fila superior: categoría + fecha + botones ────────────
        top = QHBoxLayout()
        top.setSpacing(8)

        # Badge categoría
        lbl_cat = QLabel(f"  {apunte['categoria']}  ")
        set_font(lbl_cat, 11)
        lbl_cat.setStyleSheet(f"""
            background: {c('primary_t')}; color: {c('active_text')};
            border-radius: 8px; border: none; padding: 2px 2px;
        """)
        top.addWidget(lbl_cat)

        # Fecha
        fecha = str(apunte.get("fecha", ""))[:16]
        if fecha:
            lbl_fecha = make_label(fecha, 11, color_key="text2")
            top.addWidget(lbl_fecha)

        top.addStretch()

        # Botón editar (carga en el editor)
        btn_edit = QPushButton("  ✏️  Editar")
        btn_edit.setFixedHeight(30)
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.setStyleSheet(f"""
            QPushButton {{
                background: {c('surface2')}; color: {c('text')};
                border: 1px solid {c('border')}; border-radius: 8px;
                font-size: 12px; padding: 0 10px;
            }}
            QPushButton:hover {{ border-color: {c('primary')}; color: {c('active_text')}; }}
        """)
        btn_edit.clicked.connect(lambda _, a=apunte: self._editar_apunte(a))
        top.addWidget(btn_edit)

        # Botón eliminar
        btn_del = QPushButton("  🗑")
        btn_del.setFixedSize(32, 30)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("Eliminar apunte")
        btn_del.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {c('danger')}; border: none;
                          border-radius: 8px; font-size: 14px; }}
            QPushButton:hover {{ background: {c('danger_bg')}; }}
        """)
        btn_del.clicked.connect(lambda _, aid=apunte["id"]: self._eliminar_apunte(aid))
        top.addWidget(btn_del)

        lay.addLayout(top)

        # ── Texto del apunte (preview con formato rich text) ──────────
        texto_raw = apunte["texto"]

        # Construir un preview HTML limpio:
        # 1. Quitar bloques <style> (CSS interno de Qt, no aporta visualmente)
        import re, html as html_lib
        sin_style = re.sub(r"<style[^>]*>.*?</style>", "", texto_raw,
                           flags=re.IGNORECASE | re.DOTALL)
        # 2. Truncar a ~220 chars de texto plano para medir longitud,
        #    pero mostrar HTML para que conserve negrita/cursiva/etc.
        texto_plano = re.sub(r"<[^>]+>", "", html_lib.unescape(
            re.sub(r"<br\s*/?>|</p>", " ", sin_style, flags=re.IGNORECASE)
        ))
        texto_plano = re.sub(r"\s+", " ", texto_plano).strip()
        necesita_corte = len(texto_plano) > 220

        if necesita_corte:
            # Recortar el HTML por contenido de texto, no por caracteres HTML
            acumulado = 0
            partes    = re.split(r"(<[^>]+>)", sin_style)
            resultado = []
            cortado   = False
            for parte in partes:
                if parte.startswith("<"):        # es un tag → lo copiamos tal cual
                    resultado.append(parte)
                else:                            # texto visible
                    restante = 220 - acumulado
                    if len(parte) <= restante:
                        resultado.append(parte)
                        acumulado += len(parte)
                    else:
                        resultado.append(parte[:restante].rsplit(" ", 1)[0] + "…")
                        cortado = True
                        break
            html_preview = "".join(resultado)
            if cortado:
                html_preview += "</p>"
        else:
            html_preview = sin_style

        lbl_texto = QLabel()
        lbl_texto.setTextFormat(Qt.TextFormat.RichText)
        lbl_texto.setText(html_preview)
        lbl_texto.setWordWrap(True)
        set_font(lbl_texto, 13)
        lbl_texto.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        lay.addWidget(lbl_texto)

        return card

    def _editar_apunte(self, apunte: dict):
        """Carga el apunte en el editor en modo edición."""
        self._apunte_editando_id = apunte["id"]
        self._cambiar_tab(0)
        self.text_box.setHtml(apunte["texto"])
        self._refrescar_categorias(mantener_seleccion=False)
        idx = self.combo.findText(apunte["categoria"])
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        elif apunte["categoria"]:
            # La categoría original ya no existe como curso (fue eliminado).
            # La insertamos temporalmente para no perder el dato al editar.
            self.combo.insertItem(0, apunte["categoria"])
            self.combo.setCurrentIndex(0)
        self.btn_save.setText("  💾  Actualizar")
        self.lbl_titulo.setText(f"Editando apunte — {apunte['categoria']}")
        self.btn_cancel.show()

    def _eliminar_apunte(self, apunte_id: int):
        """Elimina el apunte por id y refresca la lista."""
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)

        box.setStyleSheet(_msgbox_style())
        box.setWindowTitle("Eliminar apunte")
        box.setText("¿Eliminar este apunte permanentemente?")
        box.setIcon(QMessageBox.Icon.Warning)
        btn_si  = box.addButton("  Sí, eliminar  ", QMessageBox.ButtonRole.YesRole)
        box.addButton("  Cancelar  ",               QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == btn_si:
            self.cerebro.eliminar_apunte_por_id(apunte_id)
            self._cargar_historial()

    # ════════════════════════════════════════════════════════════════
    #  NAVEGACIÓN DE TABS
    # ════════════════════════════════════════════════════════════════
    def _cambiar_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        style_primary(self.btn_tab_escribir)  if idx == 0 else style_ghost(self.btn_tab_escribir)
        style_primary(self.btn_tab_historial) if idx == 1 else style_ghost(self.btn_tab_historial)
        if idx == 1:
            self._cargar_historial()

    # ════════════════════════════════════════════════════════════════
    #  GUARDAR
    # ════════════════════════════════════════════════════════════════
    def _save(self):
        texto_plano = self.text_box.toPlainText().strip()
        if not texto_plano:
            return
        html = self.text_box.toHtml()
        categoria = self.combo.currentText()

        if self._apunte_editando_id is not None:
            # Modo edición: actualizar el apunte existente
            self.cerebro.actualizar_apunte(self._apunte_editando_id, html, categoria)
            self._apunte_editando_id = None
            self.btn_save.setText("  💾  Guardar")
            self.lbl_titulo.setText("Escribe tu apunte")
            self.btn_cancel.hide()
            self.text_box.clear()
            self._flash("✓  Apunte actualizado correctamente", "success")
        else:
            # Modo nuevo: crear apunte
            self.cerebro.guardar_en_el_cerebro(html, categoria)
            self.text_box.clear()
            self._flash("✓  Guardado correctamente", "success")

    def _cancelar_edicion(self):
        """Descarta la edición en curso y vuelve al estado normal."""
        self._apunte_editando_id = None
        self.text_box.clear()
        self.btn_save.setText("  💾  Guardar")
        self.lbl_titulo.setText("Escribe tu apunte")
        self.btn_cancel.hide()
        self._flash("Edición cancelada", "danger")

    def _delete(self):
        texto = self.text_box.toPlainText().strip()
        if texto:
            self.cerebro.eliminar_apunte(texto)
            self.text_box.clear()
            self._flash("🗑  Apunte eliminado", "danger")

    # ════════════════════════════════════════════════════════════════
    #  INGESTA DE PDF
    # ════════════════════════════════════════════════════════════════
    def _subir_pdf(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un PDF", "", "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.setText("  ⏳  Procesando…")
        categoria = self.combo.currentText()
        self._pdf_worker = PDFIngestWorker(self.cerebro, ruta, categoria, self)
        self._pdf_worker.exito.connect(self._pdf_exito)
        self._pdf_worker.error.connect(self._pdf_error)
        self._pdf_worker.start()

    def _pdf_exito(self, cantidad, nombre_archivo):
        self.btn_pdf.setEnabled(True)
        self.btn_pdf.setText("  📄  Subir PDF")
        if cantidad > 0:
            self._flash(f"✓  '{nombre_archivo}': {cantidad} fragmentos guardados", "success")
        else:
            self._flash(f"⚠  No se pudo extraer texto de '{nombre_archivo}'", "danger")

    def _pdf_error(self, mensaje):
        self.btn_pdf.setEnabled(True)
        self.btn_pdf.setText("  📄  Subir PDF")
        self._flash(f"✗  Error al leer el PDF: {mensaje}", "danger")

    # ════════════════════════════════════════════════════════════════
    #  FLASHCARD / EXPORTAR
    # ════════════════════════════════════════════════════════════════
    def _enviar_a_flashcard(self):
        texto = self.text_box.toPlainText().strip()
        if not texto:
            self._flash("⚠  Escribe un apunte antes de convertirlo en flashcard", "danger")
            return
        self.convertir_en_flashcard.emit(texto)

    def _exportar(self):
        ruta, filtro = QFileDialog.getSaveFileName(
            self, "Exportar apuntes", "mis_apuntes.html",
            "HTML enriquecido (*.html);;Markdown (*.md);;Texto plano (*.txt)"
        )
        if not ruta:
            return
        try:
            if filtro.startswith("HTML"):
                cantidad = self.cerebro.exportar_apuntes_html(ruta)
            elif filtro.startswith("Markdown"):
                cantidad = self.cerebro.exportar_apuntes_md(ruta)
            else:
                cantidad = self.cerebro.exportar_apuntes_txt(ruta)
            if cantidad == 0:
                self._flash("⚠  No hay apuntes guardados para exportar", "danger")
            else:
                self._flash(f"✓  {cantidad} apuntes exportados", "success")
        except Exception as e:
            self._flash(f"✗  Error al exportar: {e}", "danger")

    # ════════════════════════════════════════════════════════════════
    #  ESTILOS
    # ════════════════════════════════════════════════════════════════
    def _style_textbox(self):
        self.text_box.refresh_theme()

    def _style_combo(self):
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background: {c("surface2")}; color: {c("text")};
                border: 1px solid {c("border")}; border-radius: 8px; padding: 0 12px;
            }}
            QComboBox:hover {{ border-color: {c("primary")}; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox QAbstractItemView {{
                background: {c("surface")}; color: {c("text")};
                border: 1px solid {c("border")};
                selection-background-color: {c("primary_t")};
                selection-color: {c("active_text")};
                border-radius: 8px; padding: 4px;
            }}
        """)

    def _style_input_filtro(self):
        self.input_filtro.setStyleSheet(f"""
            QLineEdit {{
                background: {c("surface2")}; color: {c("text")};
                border: 1px solid {c("border")}; border-radius: 8px; padding: 0 12px;
            }}
            QLineEdit:focus {{ border-color: {c("primary")}; }}
        """)

    def _flash(self, msg, kind):
        fg = c("success") if kind == "success" else c("danger")
        bg = c("success_bg") if kind == "success" else c("danger_bg")
        self.lbl_msg.setText(msg)
        self.lbl_msg.setStyleSheet(
            f"color: {fg}; background: {bg}; border-radius: 8px; padding: 6px 12px; border: none;"
        )
        QTimer.singleShot(2800, lambda: (
            self.lbl_msg.setText(""),
            self.lbl_msg.setStyleSheet("background: transparent; border: none;")
        ))

    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        self.hist_bg.setStyleSheet(f"background: {c('bg')};")
        self.header.refresh()
        self.card.refresh()
        self.lbl_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_cat.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_hist_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_conteo.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.text_box.refresh_theme()
        self._style_combo()
        self._style_input_filtro()
        style_primary(self.btn_save)
        style_ghost(self.btn_pdf)
        style_ghost(self.btn_flash)
        style_ghost(self.btn_export)
        style_ghost(self.btn_cancel, danger=True)
        self.tab_bar.setStyleSheet(f"background: {c('surface')}; border-bottom: 1px solid {c('border')};")
        if hasattr(self, "_todos_apuntes"):
            self._filtrar_apuntes(self.input_filtro.text())
        self._cambiar_tab(self.stack.currentIndex())


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL BUSCADOR
# ═══════════════════════════════════════════════════════════════════════════════

class BuscadorPanel(QWidget):
    def __init__(self, cerebro, parent=None):
        super().__init__(parent)
        self.cerebro = cerebro
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = SectionHeader("Buscador inteligente")
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.bg_widget)
        vbox.setContentsMargins(60, 36, 60, 36)
        vbox.setSpacing(20)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Card de búsqueda ──────────────────────────────────────
        self.card_search = Card()
        cl = QVBoxLayout(self.card_search)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(0)

        self.lbl_titulo_buscador = make_label("Busca por significado, no por palabras exactas", 14, bold=True)
        cl.addWidget(self.lbl_titulo_buscador)
        cl.addSpacing(6)

        lbl_sub = make_label(
            "La IA entiende la idea detrás de tu búsqueda. "
            "Ejemplo: busca \u201ccómo ganar dinero con mi app\u201d y encuentra \u201cestrategias de monetización\u201d.",
            12, color_key="text2"
        )
        lbl_sub.setWordWrap(True)
        cl.addWidget(lbl_sub)
        cl.addSpacing(20)

        # Barra de búsqueda
        self.search_frame = QFrame()
        self.search_frame.setFixedHeight(52)
        self._style_search_frame()
        sf_lay = QHBoxLayout(self.search_frame)
        sf_lay.setContentsMargins(18, 0, 10, 0)
        sf_lay.setSpacing(8)

        self.lbl_lupa = QLabel("🔍")
        set_font(self.lbl_lupa, 16)
        self.lbl_lupa.setStyleSheet(f"background: transparent; border: none; color: {c('text2')};")
        sf_lay.addWidget(self.lbl_lupa)

        self.entry_search = QLineEdit()
        self.entry_search.setPlaceholderText("Pregúntale a tu cerebro…")
        set_font(self.entry_search, 14)
        self.entry_search.returnPressed.connect(self._search)
        self._style_search_entry()
        sf_lay.addWidget(self.entry_search)

        self.btn_search = primary_btn("Buscar", w=92, h=38)
        self.btn_search.clicked.connect(self._search)
        sf_lay.addWidget(self.btn_search)
        cl.addWidget(self.search_frame)

        vbox.addWidget(self.card_search)

        # ── Área de resultados ────────────────────────────────────
        self.lbl_estado = make_label("", 13, color_key="text2")
        self.lbl_estado.setWordWrap(True)
        vbox.addWidget(self.lbl_estado)

        # Contenedor de tarjetas de resultado
        self.resultados_widget = QWidget()
        self.resultados_widget.setStyleSheet("background: transparent;")
        self.resultados_vlay = QVBoxLayout(self.resultados_widget)
        self.resultados_vlay.setContentsMargins(0, 0, 0, 0)
        self.resultados_vlay.setSpacing(10)
        self.resultados_vlay.setAlignment(Qt.AlignmentFlag.AlignTop)
        vbox.addWidget(self.resultados_widget)

        scroll.setWidget(self.bg_widget)
        root.addWidget(scroll)
        FadeIn(self.bg_widget)

    # ── Búsqueda ──────────────────────────────────────────────────
    def _search(self):
        q = self.entry_search.text().strip()
        if not q:
            return

        self.lbl_estado.setText("⏳  Buscando…")
        self._limpiar_resultados()
        QApplication.processEvents()

        resultados = self.cerebro.buscar_con_ia(q)

        if not resultados:
            self.lbl_estado.setText("Sin resultados. Prueba con otros términos o escribe más apuntes.")
            return

        tipo = resultados[0].get("tipo_busqueda", "textual")
        if tipo == "semantica":
            self.lbl_estado.setText(
                f"✦  Búsqueda semántica activa — {len(resultados)} resultado(s) por significado"
            )
            self.lbl_estado.setStyleSheet(
                f"color: {c('primary')}; background: transparent; border: none; font-size: 13px;"
            )
        else:
            self.lbl_estado.setText(
                f"🔤  Búsqueda por palabras — {len(resultados)} resultado(s)   "
                "(instala sentence-transformers para búsqueda semántica)"
            )
            self.lbl_estado.setStyleSheet(
                f"color: {c('text2')}; background: transparent; border: none; font-size: 13px;"
            )

        for i, r in enumerate(resultados):
            self.resultados_vlay.addWidget(self._make_result_card(i + 1, r))

    def _limpiar_resultados(self):
        while self.resultados_vlay.count():
            item = self.resultados_vlay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _make_result_card(self, rank: int, resultado: dict) -> QFrame:
        """Crea una tarjeta visual para un resultado de búsqueda."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {c('surface')};
                border: 1px solid {c('border')};
                border-radius: 12px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(8)

        # ── Fila superior: rank + categoría + score ───────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Número de resultado
        lbl_rank = QLabel(f"#{rank}")
        lbl_rank.setFixedSize(28, 28)
        lbl_rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_font(lbl_rank, 11, bold=True)
        lbl_rank.setStyleSheet(f"""
            background: {c('primary_t')}; color: {c('active_text')};
            border-radius: 14px; border: none;
        """)
        top_row.addWidget(lbl_rank)

        # Badge categoría
        lbl_cat = QLabel(f"  {resultado['categoria']}  ")
        set_font(lbl_cat, 11)
        lbl_cat.setStyleSheet(f"""
            background: {c('surface2')}; color: {c('text2')};
            border-radius: 8px; border: none; padding: 2px 4px;
        """)
        top_row.addWidget(lbl_cat)

        top_row.addStretch()

        # Score como porcentaje con color semáforo (colores adaptativos al tema)
        score = resultado.get("score", 0)
        pct   = int(score * 100)
        if pct >= 75:
            score_color = c("success")
            score_bg    = c("success_bg")
            score_icon  = "●"
        elif pct >= 50:
            score_color = c("text2")
            score_bg    = c("surface2")
            score_icon  = "●"
        else:
            score_color = c("danger")
            score_bg    = c("danger_bg")
            score_icon  = "●"

        tipo = resultado.get("tipo_busqueda", "textual")
        tipo_lbl = "Semántico" if tipo == "semantica" else "Textual"

        lbl_score = QLabel(f"  {score_icon} {pct}% · {tipo_lbl}  ")
        set_font(lbl_score, 11, bold=True)
        lbl_score.setStyleSheet(f"""
            background: {score_bg}; color: {score_color};
            border-radius: 10px; border: none; padding: 2px 4px;
        """)
        top_row.addWidget(lbl_score)
        lay.addLayout(top_row)

        # ── Barra de similitud ────────────────────────────────────
        barra_outer = QFrame()
        barra_outer.setFixedHeight(6)
        barra_outer.setStyleSheet(f"""
            background: {c('border')}; border-radius: 3px; border: none;
        """)
        barra_inner = QFrame(barra_outer)
        barra_inner.setFixedHeight(6)
        # Ancho se ajusta al padre; usamos resizeEvent vía setProperty
        barra_inner._score_pct = pct
        if pct >= 75:
            bar_color = "#4CAF50"
        elif pct >= 50:
            bar_color = "#FF9800"
        else:
            bar_color = "#F44336"
        barra_inner.setStyleSheet(f"""
            background: {bar_color}; border-radius: 3px; border: none;
        """)
        # Ajustar ancho de la barra con QTimer para que el widget esté renderizado
        def _ajustar_barra(outer=barra_outer, inner=barra_inner, p=pct):
            w = max(4, int(outer.width() * p / 100))
            inner.setFixedWidth(w)
        QTimer.singleShot(50, _ajustar_barra)
        lay.addWidget(barra_outer)

        # ── Texto del apunte (renderizado con formato) ───────────
        texto_raw = resultado["texto"]
        import re, html as html_lib

        # Quitar solo <style> para evitar que Qt lo muestre como texto,
        # pero conservar el resto del HTML para que se renderice con formato
        sin_style = re.sub(r"<style[^>]*>.*?</style>", "", texto_raw,
                           flags=re.DOTALL | re.IGNORECASE)
        sin_style = re.sub(r"<head[^>]*>.*?</head>", "", sin_style,
                           flags=re.DOTALL | re.IGNORECASE)
        sin_style = re.sub(r"<script[^>]*>.*?</script>", "", sin_style,
                           flags=re.DOTALL | re.IGNORECASE)

        # Calcular longitud de texto plano para decidir si recortar
        texto_plano = re.sub(r"<[^>]+>", "", html_lib.unescape(
            re.sub(r"<br\s*/?>|</p>", " ", sin_style, flags=re.IGNORECASE)
        ))
        texto_plano = re.sub(r"\s+", " ", texto_plano).strip()
        necesita_corte = len(texto_plano) > 320

        if necesita_corte:
            # Recortar por contenido visible, respetando tags HTML
            acumulado = 0
            partes = re.split(r"(<[^>]+>)", sin_style)
            resultado_html = []
            for parte in partes:
                if parte.startswith("<"):
                    resultado_html.append(parte)
                else:
                    restante = 320 - acumulado
                    if len(parte) <= restante:
                        resultado_html.append(parte)
                        acumulado += len(parte)
                    else:
                        resultado_html.append(parte[:restante].rsplit(" ", 1)[0] + "…")
                        break
            html_preview = "".join(resultado_html)
        else:
            html_preview = sin_style

        lbl_texto = QLabel()
        lbl_texto.setTextFormat(Qt.TextFormat.RichText)
        lbl_texto.setText(html_preview)
        lbl_texto.setWordWrap(True)
        set_font(lbl_texto, 13)
        lbl_texto.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        lay.addWidget(lbl_texto)

        return card

    # ── Estilos ───────────────────────────────────────────────────
    def _style_search_frame(self):
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background: {c("surface2")};
                border: 1.5px solid {c("border")};
                border-radius: 26px;
            }}
        """)

    def _style_search_entry(self):
        self.entry_search.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {c("text")};
                border: none;
                padding: 0;
            }}
        """)

    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        self.header.refresh()
        self.card_search.refresh()
        self._style_search_frame()
        self._style_search_entry()
        style_primary(self.btn_search)
        self.lbl_lupa.setStyleSheet(f"background: transparent; border: none; color: {c('text2')};")
        self.lbl_titulo_buscador.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_estado.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none; font-size: 13px;")
        self._limpiar_resultados()


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL FLASHCARDS
# ═══════════════════════════════════════════════════════════════════════════════

class FlashcardsPanel(QWidget):
    """
    Panel reorganizado: Cursos → Temas → Flashcards + Sesión de estudio.
    Vista 0: Biblioteca  (árbol cursos/temas)
    Vista 1: Crear       (formulario con selector de curso y tema)
    Vista 2: Sesión      (repaso de flashcards de un tema)
    """

    # Se emite cada vez que se crea o elimina un curso, para que otras
    # secciones (Cuaderno, Notas de Voz) mantengan su lista de categorías
    # sincronizada con los cursos de Flashcards.
    cursos_actualizados = pyqtSignal()

    def __init__(self, cerebro, parent=None):
        super().__init__(parent)
        self.cerebro = cerebro
        self._tab_activo = 0
        # sesión de estudio
        self._cola = []
        self._idx = 0
        self._tema_sesion_id = None
        self._tema_sesion_nombre = ""
        # contexto de crear
        self._curso_crear_id = None
        self._tema_crear_id = None
        self._build()

    # ════════════════════════════════════════════════════════════════
    #  CONSTRUCCIÓN GENERAL
    # ════════════════════════════════════════════════════════════════
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = SectionHeader("Flashcards")
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.bg_widget)
        vbox.setContentsMargins(60, 36, 60, 36)
        vbox.setSpacing(20)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Tabs
        tab_row = QHBoxLayout()
        tab_row.setSpacing(10)
        tab_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.btn_tab_biblio = ghost_btn("  📚  Biblioteca", w=160, h=42)
        self.btn_tab_crear  = ghost_btn("  ➕  Crear",      w=130, h=42)
        self.btn_tab_biblio.clicked.connect(lambda: self._cambiar_tab(0))
        self.btn_tab_crear.clicked.connect(lambda:  self._cambiar_tab(1))
        tab_row.addWidget(self.btn_tab_biblio)
        tab_row.addWidget(self.btn_tab_crear)
        vbox.addLayout(tab_row)

        # Stack
        self.inner_stack = QStackedWidget()
        self.inner_stack.setStyleSheet("background: transparent;")
        self.vista_biblio  = self._build_vista_biblio()
        self.vista_crear   = self._build_vista_crear()
        self.vista_sesion  = self._build_vista_sesion()
        self.inner_stack.addWidget(self.vista_biblio)   # 0
        self.inner_stack.addWidget(self.vista_crear)    # 1
        self.inner_stack.addWidget(self.vista_sesion)   # 2
        vbox.addWidget(self.inner_stack)

        scroll.setWidget(self.bg_widget)
        root.addWidget(scroll)
        FadeIn(self.bg_widget)
        self._cambiar_tab(0)

    # ════════════════════════════════════════════════════════════════
    #  VISTA 0 – BIBLIOTECA  (cursos → temas → flashcards)
    # ════════════════════════════════════════════════════════════════
    def _build_vista_biblio(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # ── Fila: nuevo curso ─────────────────────────────────────
        self.card_nuevo_curso = Card()
        row_nc = QHBoxLayout(self.card_nuevo_curso)
        row_nc.setContentsMargins(24, 18, 24, 18)
        row_nc.setSpacing(12)

        self.input_nuevo_curso = QLineEdit()
        self.input_nuevo_curso.setPlaceholderText("Nombre del nuevo curso…")
        self.input_nuevo_curso.setFixedHeight(38)
        set_font(self.input_nuevo_curso, 13)
        self._style_input(self.input_nuevo_curso)

        self.btn_add_curso = primary_btn("  ＋  Añadir curso", w=170, h=38)
        self.btn_add_curso.clicked.connect(self._crear_curso)

        row_nc.addWidget(self.input_nuevo_curso, stretch=1)
        row_nc.addWidget(self.btn_add_curso)
        lay.addWidget(self.card_nuevo_curso)

        # ── Lista de cursos ───────────────────────────────────────
        self.card_cursos = Card()
        self.cursos_vlay = QVBoxLayout(self.card_cursos)
        self.cursos_vlay.setContentsMargins(0, 8, 0, 8)
        self.cursos_vlay.setSpacing(0)
        self.cursos_vlay.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.card_cursos)

        lay.addStretch()
        return w

    def _limpiar_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._limpiar_layout(item.layout())

    def _cargar_biblioteca(self):
        self._limpiar_layout(self.cursos_vlay)
        cursos = self.cerebro.obtener_cursos()

        if not cursos:
            lbl = make_label(
                "Todavía no tienes cursos.\nCrea uno arriba para organizar tus flashcards.",
                13, color_key="text2"
            )
            lbl.setWordWrap(True)
            lbl.setContentsMargins(24, 20, 24, 20)
            self.cursos_vlay.addWidget(lbl)
            return

        for curso in cursos:
            self.cursos_vlay.addWidget(self._make_curso_widget(curso))

    def _make_curso_widget(self, curso: dict) -> QWidget:
        """Bloque expandible de un curso con sus temas."""
        contenedor = QWidget()
        contenedor.setStyleSheet("background: transparent;")
        vlay = QVBoxLayout(contenedor)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # ── Cabecera del curso ────────────────────────────────────
        cab = QWidget()
        cab.setFixedHeight(52)
        cab.setStyleSheet(f"""
            QWidget {{
                background: {c('surface2')};
                border-bottom: 1px solid {c('border')};
            }}
        """)
        cab_lay = QHBoxLayout(cab)
        cab_lay.setContentsMargins(24, 0, 12, 0)
        cab_lay.setSpacing(10)

        self._arrow = {}   # no la usamos globalmente, estado local
        arrow_lbl = QLabel("▶")
        set_font(arrow_lbl, 10)
        arrow_lbl.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")

        lbl_nombre = make_label(f"📘  {curso['nombre']}", 14, bold=True)

        # Botones del curso
        btn_del_curso = QPushButton("🗑")
        btn_del_curso.setFixedSize(30, 30)
        btn_del_curso.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_curso.setStyleSheet(
            f"QPushButton{{color:{c('danger')};background:transparent;border:none;font-size:14px;border-radius:6px;}}"
            f"QPushButton:hover{{background:{c('danger_bg')};}}"
        )
        btn_del_curso.setToolTip("Eliminar curso")

        cab_lay.addWidget(arrow_lbl)
        cab_lay.addWidget(lbl_nombre, stretch=1)
        cab_lay.addWidget(btn_del_curso)

        # ── Área de temas (colapsable) ────────────────────────────
        temas_area = QWidget()
        temas_area.setStyleSheet("background: transparent;")
        temas_vlay = QVBoxLayout(temas_area)
        temas_vlay.setContentsMargins(32, 8, 16, 12)
        temas_vlay.setSpacing(8)

        # Fila añadir tema
        row_tema = QHBoxLayout()
        row_tema.setSpacing(8)
        input_tema = QLineEdit()
        input_tema.setPlaceholderText("Nombre del nuevo tema…")
        input_tema.setFixedHeight(34)
        set_font(input_tema, 12)
        self._style_input(input_tema)
        btn_add_tema = primary_btn("  ＋  Tema", w=110, h=34)
        btn_add_tema.clicked.connect(
            lambda _, cid=curso["id"], inp=input_tema: self._crear_tema(cid, inp)
        )
        row_tema.addWidget(input_tema, stretch=1)
        row_tema.addWidget(btn_add_tema)
        temas_vlay.addLayout(row_tema)

        # Temas existentes
        temas = self.cerebro.obtener_temas(curso["id"])
        for tema in temas:
            temas_vlay.addWidget(self._make_tema_row(tema, curso))

        if not temas:
            lbl_empty = make_label("Sin temas todavía. Agrega uno arriba.", 12, color_key="text3")
            temas_vlay.addWidget(lbl_empty)

        # Toggle expandir/colapsar
        temas_area.setVisible(False)
        def _toggle(_checked=False, area=temas_area, arr=arrow_lbl):
            vis = not area.isVisible()
            area.setVisible(vis)
            arr.setText("▼" if vis else "▶")

        cab.mousePressEvent = lambda e: _toggle()
        arrow_lbl.mousePressEvent = lambda e: _toggle()
        lbl_nombre.mousePressEvent = lambda e: _toggle()

        # Eliminar curso
        btn_del_curso.clicked.connect(
            lambda _, cid=curso["id"], nombre=curso["nombre"]: self._confirmar_borrar_curso(cid, nombre)
        )

        vlay.addWidget(cab)
        vlay.addWidget(temas_area)
        return contenedor

    def _make_tema_row(self, tema: dict, curso: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background: {c('primary_t')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 8, 8, 8)
        lay.setSpacing(10)

        # Nombre del tema
        lbl = make_label(f"🗂  {tema['nombre']}", 13, bold=True, color_key="active_text")
        lay.addWidget(lbl, stretch=1)

        # Contador
        stats = self.cerebro.contar_flashcards_por_tema(tema["id"])
        pendientes = stats["pendientes"]
        total = stats["total"]
        chip_txt = f"{pendientes} pendientes / {total} total"
        chip = make_label(chip_txt, 11, color_key="text2")
        chip.setFixedWidth(160)
        lay.addWidget(chip)

        # Botón estudiar
        btn_est = primary_btn("  ▶  Estudiar", w=120, h=32)
        btn_est.clicked.connect(
            lambda _, tid=tema["id"], tn=tema["nombre"], cn=curso["nombre"]:
                self._iniciar_sesion(tid, tn, cn)
        )
        lay.addWidget(btn_est)

        # Botón añadir flashcard
        btn_add = ghost_btn("  ＋", w=40, h=32)
        btn_add.setToolTip("Añadir flashcard a este tema")
        btn_add.clicked.connect(
            lambda _, cid=curso["id"], tid=tema["id"], cn=curso["nombre"], tn=tema["nombre"]:
                self._ir_a_crear(cid, tid, cn, tn)
        )
        lay.addWidget(btn_add)

        # Botón eliminar tema
        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(30, 30)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(
            f"QPushButton{{color:{c('danger')};background:transparent;border:none;font-size:13px;border-radius:6px;}}"
            f"QPushButton:hover{{background:{c('danger_bg')};}}"
        )
        btn_del.clicked.connect(
            lambda _, tid=tema["id"], tn=tema["nombre"]: self._confirmar_borrar_tema(tid, tn)
        )
        lay.addWidget(btn_del)
        return row

    # ════════════════════════════════════════════════════════════════
    #  VISTA 1 – CREAR FLASHCARD
    # ════════════════════════════════════════════════════════════════
    def _build_vista_crear(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)

        self.card_crear = Card()
        cl = QVBoxLayout(self.card_crear)
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(0)

        # Destino (curso + tema)
        self.lbl_destino_titulo = make_label("Guardar en", 13, color_key="text2")
        cl.addWidget(self.lbl_destino_titulo)
        cl.addSpacing(8)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(10)

        self.combo_curso_crear = QComboBox()
        self.combo_curso_crear.setFixedHeight(38)
        self.combo_curso_crear.setMinimumWidth(180)
        set_font(self.combo_curso_crear, 13)
        self.combo_curso_crear.currentIndexChanged.connect(self._on_combo_curso_changed)

        self.combo_tema_crear = QComboBox()
        self.combo_tema_crear.setFixedHeight(38)
        self.combo_tema_crear.setMinimumWidth(180)
        set_font(self.combo_tema_crear, 13)

        dest_row.addWidget(self.combo_curso_crear)
        dest_row.addWidget(self.combo_tema_crear)
        dest_row.addStretch()
        cl.addLayout(dest_row)
        cl.addSpacing(22)

        # Pregunta
        self.lbl_pregunta_titulo = make_label("Pregunta (frente de la tarjeta)", 14, bold=True)
        cl.addWidget(self.lbl_pregunta_titulo)
        cl.addSpacing(10)
        self.text_pregunta = QTextEdit()
        self.text_pregunta.setFixedHeight(80)
        set_font(self.text_pregunta, 14)
        cl.addWidget(self.text_pregunta)
        cl.addSpacing(18)

        # Respuesta
        self.lbl_respuesta_titulo = make_label("Respuesta (dorso de la tarjeta)", 14, bold=True)
        cl.addWidget(self.lbl_respuesta_titulo)
        cl.addSpacing(10)
        self.text_respuesta = QTextEdit()
        self.text_respuesta.setFixedHeight(110)
        set_font(self.text_respuesta, 14)
        cl.addWidget(self.text_respuesta)
        cl.addSpacing(22)

        self.btn_guardar_flash = primary_btn("  💾  Guardar flashcard", w=210, h=44)
        self.btn_guardar_flash.clicked.connect(self._guardar_flashcard)
        cl.addWidget(self.btn_guardar_flash)
        cl.addSpacing(10)

        self.lbl_msg_crear = QLabel("")
        set_font(self.lbl_msg_crear, 13)
        self.lbl_msg_crear.setStyleSheet("background: transparent; border: none;")
        cl.addWidget(self.lbl_msg_crear)

        self._style_textboxes()
        self._style_combos()

        lay.addWidget(self.card_crear)
        return w

    def _cargar_combos_crear(self):
        """Rellena los combos de curso y tema en la vista Crear."""
        cursos = self.cerebro.obtener_cursos()
        self.combo_curso_crear.blockSignals(True)
        self.combo_curso_crear.clear()
        if not cursos:
            self.combo_curso_crear.addItem("— sin cursos —")
            self.combo_tema_crear.clear()
            self.combo_tema_crear.addItem("— sin temas —")
            self.combo_curso_crear.blockSignals(False)
            return
        for c_item in cursos:
            self.combo_curso_crear.addItem(c_item["nombre"], c_item["id"])
        # Seleccionar el curso pre-seleccionado si existe
        if self._curso_crear_id is not None:
            for i in range(self.combo_curso_crear.count()):
                if self.combo_curso_crear.itemData(i) == self._curso_crear_id:
                    self.combo_curso_crear.setCurrentIndex(i)
                    break
        self.combo_curso_crear.blockSignals(False)
        self._recargar_temas_combo()
        # Seleccionar tema pre-seleccionado
        if self._tema_crear_id is not None:
            for i in range(self.combo_tema_crear.count()):
                if self.combo_tema_crear.itemData(i) == self._tema_crear_id:
                    self.combo_tema_crear.setCurrentIndex(i)
                    break

    def _on_combo_curso_changed(self, _idx):
        self._recargar_temas_combo()

    def _recargar_temas_combo(self):
        curso_id = self.combo_curso_crear.currentData()
        self.combo_tema_crear.clear()
        if curso_id is None:
            self.combo_tema_crear.addItem("— sin temas —")
            return
        temas = self.cerebro.obtener_temas(curso_id)
        if not temas:
            self.combo_tema_crear.addItem("— sin temas —")
        else:
            for t in temas:
                self.combo_tema_crear.addItem(t["nombre"], t["id"])

    # ════════════════════════════════════════════════════════════════
    #  VISTA 2 – SESIÓN DE ESTUDIO
    # ════════════════════════════════════════════════════════════════
    def _build_vista_sesion(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        # Botón volver
        self.btn_volver_biblio = ghost_btn("  ← Volver a biblioteca", w=210, h=38)
        self.btn_volver_biblio.clicked.connect(lambda: self._cambiar_tab(0))
        lay.addWidget(self.btn_volver_biblio)

        # Card principal de estudio
        self.card_estudio = Card()
        cl = QVBoxLayout(self.card_estudio)
        cl.setContentsMargins(40, 40, 40, 40)
        cl.setSpacing(0)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.lbl_sesion_titulo = make_label("", 12, color_key="primary", bold=True)
        cl.addWidget(self.lbl_sesion_titulo)
        cl.addSpacing(4)

        self.lbl_progreso = make_label("", 12, color_key="text2")
        cl.addWidget(self.lbl_progreso)
        cl.addSpacing(18)

        self.lbl_pregunta = make_label("", 18, bold=True)
        self.lbl_pregunta.setWordWrap(True)
        cl.addWidget(self.lbl_pregunta)
        cl.addSpacing(20)

        self.h_respuesta = h_line()
        self.h_respuesta.hide()
        cl.addWidget(self.h_respuesta)
        cl.addSpacing(16)

        self.lbl_respuesta = make_label("", 15, color_key="text2")
        self.lbl_respuesta.setWordWrap(True)
        self.lbl_respuesta.hide()
        cl.addWidget(self.lbl_respuesta)
        cl.addSpacing(30)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_mostrar   = primary_btn("  👁  Mostrar respuesta", w=220, h=46)
        self.btn_no_sabia  = ghost_btn(  "  ❌  No lo sabía",       w=160, h=46, danger=True)
        self.btn_si_sabia  = primary_btn("  ✅  Lo sabía",           w=160, h=46)

        self.btn_mostrar.clicked.connect(self._mostrar_respuesta)
        self.btn_no_sabia.clicked.connect(lambda: self._responder(False))
        self.btn_si_sabia.clicked.connect(lambda: self._responder(True))

        self.btn_no_sabia.hide()
        self.btn_si_sabia.hide()

        btn_row.addWidget(self.btn_mostrar)
        btn_row.addWidget(self.btn_no_sabia)
        btn_row.addWidget(self.btn_si_sabia)
        cl.addLayout(btn_row)

        lay.addWidget(self.card_estudio)
        return w

    def _iniciar_sesion(self, tema_id: int, tema_nombre: str, curso_nombre: str):
        """Carga las flashcards del tema y arranca la sesión de estudio."""
        self._tema_sesion_id = tema_id
        self._tema_sesion_nombre = tema_nombre
        self._cola = self.cerebro.obtener_flashcards_por_tema(tema_id)
        self._idx = 0
        self.lbl_sesion_titulo.setText(f"📘 {curso_nombre}  ›  🗂 {tema_nombre}")
        self._mostrar_tarjeta_actual()
        # Cambiar al stack de sesión sin tocar los tabs
        self.inner_stack.setCurrentIndex(2)

    def _mostrar_tarjeta_actual(self):
        self.lbl_respuesta.setGraphicsEffect(None)
        self.lbl_respuesta.setText("")
        self.lbl_respuesta.hide()
        self.h_respuesta.hide()
        self.btn_no_sabia.hide()
        self.btn_si_sabia.hide()

        total = len(self._cola)
        if total == 0 or self._idx >= total:
            self.lbl_progreso.setText("")
            self.lbl_pregunta.setText(
                "🎉  ¡Completaste todas las tarjetas de este tema!\n"
                "Pulsa «Volver a biblioteca» para elegir otro tema."
            )
            self.btn_mostrar.hide()
            return

        tarjeta = self._cola[self._idx]
        self.lbl_progreso.setText(f"Tarjeta {self._idx + 1} de {total}")
        self.lbl_pregunta.setText(tarjeta["pregunta"])
        self.btn_mostrar.show()

    def _mostrar_respuesta(self):
        if not self._cola or self._idx >= len(self._cola):
            return
        tarjeta = self._cola[self._idx]
        self.lbl_respuesta.setGraphicsEffect(None)
        self.lbl_respuesta.setText(tarjeta["respuesta"])
        self.h_respuesta.show()
        self.lbl_respuesta.show()
        self.btn_mostrar.hide()
        self.btn_no_sabia.show()
        self.btn_si_sabia.show()

    def _responder(self, acierto: bool):
        if not self._cola or self._idx >= len(self._cola):
            return
        tarjeta = self._cola[self._idx]
        self.cerebro.responder_flashcard(tarjeta["id"], acierto)
        self._idx += 1
        self._mostrar_tarjeta_actual()

    # ════════════════════════════════════════════════════════════════
    #  ACCIONES DE BIBLIOTECA
    # ════════════════════════════════════════════════════════════════
    def _crear_curso(self):
        nombre = self.input_nuevo_curso.text().strip()
        if not nombre:
            return
        self.cerebro.crear_curso(nombre)
        self.input_nuevo_curso.clear()
        self._cargar_biblioteca()
        self.cursos_actualizados.emit()

    def _crear_tema(self, curso_id: int, input_widget: QLineEdit):
        nombre = input_widget.text().strip()
        if not nombre:
            return
        self.cerebro.crear_tema(nombre, curso_id)
        input_widget.clear()
        self._cargar_biblioteca()

    def _ir_a_crear(self, curso_id: int, tema_id: int, curso_nombre: str, tema_nombre: str):
        """Navega a Crear pre-seleccionando curso y tema."""
        self._curso_crear_id = curso_id
        self._tema_crear_id  = tema_id
        self._cambiar_tab(1)

    def _confirmar_borrar_curso(self, curso_id: int, nombre: str):
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)

        box.setStyleSheet(_msgbox_style())
        box.setWindowTitle("Eliminar curso")
        box.setText(f"¿Eliminar el curso «{nombre}» y todos sus temas y flashcards?")
        box.setIcon(QMessageBox.Icon.Warning)
        btn_si = box.addButton("  Sí, eliminar  ", QMessageBox.ButtonRole.YesRole)
        box.addButton("  Cancelar  ", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == btn_si:
            self.cerebro.eliminar_curso(curso_id)
            self._cargar_biblioteca()
            self.cursos_actualizados.emit()

    def _confirmar_borrar_tema(self, tema_id: int, nombre: str):
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)

        box.setStyleSheet(_msgbox_style())
        box.setWindowTitle("Eliminar tema")
        box.setText(f"¿Eliminar el tema «{nombre}» y todas sus flashcards?")
        box.setIcon(QMessageBox.Icon.Warning)
        btn_si = box.addButton("  Sí, eliminar  ", QMessageBox.ButtonRole.YesRole)
        box.addButton("  Cancelar  ", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == btn_si:
            self.cerebro.eliminar_tema(tema_id)
            self._cargar_biblioteca()

    # ════════════════════════════════════════════════════════════════
    #  GUARDAR FLASHCARD
    # ════════════════════════════════════════════════════════════════
    def _guardar_flashcard(self):
        pregunta  = self.text_pregunta.toPlainText().strip()
        respuesta = self.text_respuesta.toPlainText().strip()

        curso_id = self.combo_curso_crear.currentData()
        tema_id  = self.combo_tema_crear.currentData()

        if not pregunta or not respuesta:
            self._flash(self.lbl_msg_crear, "⚠  Completa la pregunta y la respuesta", "danger")
            return
        if not curso_id or not tema_id:
            self._flash(self.lbl_msg_crear, "⚠  Selecciona un curso y un tema", "danger")
            return

        self.cerebro.crear_flashcard_v2(pregunta, respuesta, curso_id, tema_id)
        self.text_pregunta.clear()
        self.text_respuesta.clear()
        self._flash(self.lbl_msg_crear, "✓  Flashcard guardada correctamente", "success")

    # ════════════════════════════════════════════════════════════════
    #  NAVEGACIÓN DE TABS
    # ════════════════════════════════════════════════════════════════
    def _cambiar_tab(self, idx: int):
        self._tab_activo = idx
        self.inner_stack.setCurrentIndex(idx)
        botones = [self.btn_tab_biblio, self.btn_tab_crear]
        for i, btn in enumerate(botones):
            style_primary(btn) if i == idx else style_ghost(btn)
        if idx == 0:
            self._cargar_biblioteca()
        elif idx == 1:
            self._cargar_combos_crear()

    def refrescar(self):
        self._cambiar_tab(self._tab_activo)

    def precargar_respuesta(self, texto: str):
        self._cambiar_tab(1)
        self.text_respuesta.setPlainText(texto)
        self.text_pregunta.setFocus()

    # ════════════════════════════════════════════════════════════════
    #  ESTILOS
    # ════════════════════════════════════════════════════════════════
    def _style_input(self, widget):
        widget.setStyleSheet(f"""
            QLineEdit {{
                background: {c("surface2")};
                color: {c("text")};
                border: 1px solid {c("border")};
                border-radius: 8px;
                padding: 0 12px;
            }}
            QLineEdit:focus {{ border-color: {c("primary")}; }}
        """)

    def _style_textboxes(self):
        estilo = f"""
            QTextEdit {{
                background: {c("surface2")};
                color: {c("text")};
                border: 1px solid {c("border")};
                border-radius: 10px;
                padding: 12px;
            }}
            QTextEdit:focus {{ border-color: {c("primary")}; }}
        """
        self.text_pregunta.setStyleSheet(estilo)
        self.text_respuesta.setStyleSheet(estilo)

    def _style_combos(self):
        estilo = f"""
            QComboBox {{
                background: {c("surface2")};
                color: {c("text")};
                border: 1px solid {c("border")};
                border-radius: 8px;
                padding: 0 12px;
            }}
            QComboBox:hover {{ border-color: {c("primary")}; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox QAbstractItemView {{
                background: {c("surface")};
                color: {c("text")};
                border: 1px solid {c("border")};
                selection-background-color: {c("primary_t")};
                selection-color: {c("active_text")};
                border-radius: 8px;
                padding: 4px;
            }}
        """
        self.combo_curso_crear.setStyleSheet(estilo)
        self.combo_tema_crear.setStyleSheet(estilo)

    def _flash(self, etiqueta: QLabel, msg: str, kind: str):
        fg = c("success") if kind == "success" else c("danger")
        bg = c("success_bg") if kind == "success" else c("danger_bg")
        etiqueta.setText(msg)
        etiqueta.setStyleSheet(
            f"color: {fg}; background: {bg}; border-radius: 8px; padding: 6px 12px; border: none;"
        )
        QTimer.singleShot(2800, lambda: (
            etiqueta.setText(""),
            etiqueta.setStyleSheet("background: transparent; border: none;")
        ))

    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        self.header.refresh()
        self.card_crear.refresh()
        self.card_estudio.refresh()
        self.card_nuevo_curso.refresh()
        self.card_cursos.refresh()

        self.lbl_progreso.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_sesion_titulo.setStyleSheet(f"color: {c('primary')}; background: transparent; border: none;")
        self.lbl_pregunta.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_respuesta.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.h_respuesta.setStyleSheet(f"background: {c('border')}; border: none;")
        self.lbl_pregunta_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_respuesta_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_destino_titulo.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self._style_textboxes()
        self._style_combos()
        self._style_input(self.input_nuevo_curso)
        style_primary(self.btn_add_curso)
        style_ghost(self.btn_no_sabia, danger=True)
        style_primary(self.btn_si_sabia)
        style_primary(self.btn_guardar_flash)
        self._cambiar_tab(self._tab_activo)
        if self._tab_activo == 0:
            self._cargar_biblioteca()



# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL ESTADÍSTICAS  ←  implementación completa
# ═══════════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════════
#  WORKER: Transcripción Whisper en hilo separado
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperWorker(QObject):
    """Corre la transcripción de Whisper en un QThread para no bloquear la UI."""
    terminado   = pyqtSignal(str)   # texto transcripto
    error       = pyqtSignal(str)   # mensaje de error

    def __init__(self, ruta_audio: str):
        super().__init__()
        self._ruta = ruta_audio

    def run(self):
        try:
            import whisper
            modelo = whisper.load_model("small")
            resultado = modelo.transcribe(self._ruta, fp16=False)
            self.terminado.emit(resultado["text"].strip())
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  WORKER: Grabación de audio en hilo separado
# ═══════════════════════════════════════════════════════════════════════════════

class GrabacionWorker(QObject):
    """Graba audio del micrófono usando sounddevice + soundfile."""
    terminado = pyqtSignal(str)   # ruta al archivo .wav grabado
    error     = pyqtSignal(str)

    def __init__(self, ruta_salida: str, segundos: int = 30, sample_rate: int = 16000):
        super().__init__()
        self._ruta        = ruta_salida
        self._segundos    = segundos
        self._sample_rate = sample_rate
        self._detener     = False

    def detener(self):
        self._detener = True

    def run(self):
        try:
            import sounddevice as sd
            import soundfile  as sf
            import numpy      as np

            frames = []
            bloque = int(self._sample_rate * 0.1)   # 100 ms por bloque

            with sd.InputStream(samplerate=self._sample_rate, channels=1, dtype="float32") as stream:
                while not self._detener:
                    data, _ = stream.read(bloque)
                    frames.append(data.copy())

            if frames:
                audio = np.concatenate(frames, axis=0)
                sf.write(self._ruta, audio, self._sample_rate)
                self.terminado.emit(self._ruta)
            else:
                self.error.emit("No se capturó audio.")
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL: Notas de Voz
# ═══════════════════════════════════════════════════════════════════════════════

class NotasVozPanel(QWidget):
    """Panel para grabar notas de voz y transcribirlas con Whisper (local)."""

    def __init__(self, cerebro, parent=None):
        super().__init__(parent)
        self.cerebro         = cerebro
        self._grabando       = False
        self._transcribiendo = False
        self._hilo_grab      = None
        self._worker_grab    = None
        self._hilo_whisper   = None
        self._worker_whisper = None
        self._timer_seg      = QTimer(self)
        self._timer_seg.setInterval(1000)
        self._timer_seg.timeout.connect(self._tick_grabacion)
        self._segundos_grab  = 0
        self._build()

    # ── UI ─────────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # Título
        self.lbl_titulo = QLabel("🎙️  Notas de Voz")
        set_font(self.lbl_titulo, 22, bold=True)
        self.lbl_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        root.addWidget(self.lbl_titulo)

        # Subtítulo
        self.lbl_sub = QLabel("Graba tu idea y Whisper la convierte a texto automáticamente.")
        set_font(self.lbl_sub, 13)
        self.lbl_sub.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        root.addWidget(self.lbl_sub)

        # ── Tarjeta principal ──────────────────────────────────────────────────
        self.card = Card()
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(28, 28, 28, 28)
        card_lay.setSpacing(18)

        # Animación / estado visual — fuente emoji explícita para Windows
        self.lbl_estado = QLabel("🎙️")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _f_emoji = QFont("Segoe UI Emoji", 48)
        _f_emoji.setStyleStrategy(QFont.StyleStrategy.PreferDefault)
        self.lbl_estado.setFont(_f_emoji)
        self.lbl_estado.setStyleSheet("background: transparent; border: none;")
        card_lay.addWidget(self.lbl_estado)

        # Cronómetro — fuente monoespaciada para números nítidos y estables
        self.lbl_tiempo = QLabel("00:00")
        self.lbl_tiempo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _f_timer = QFont("Courier New", 42, QFont.Weight.Bold)
        self.lbl_tiempo.setFont(_f_timer)
        self.lbl_tiempo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none; letter-spacing: 3px;")
        card_lay.addWidget(self.lbl_tiempo)

        # Mensaje de estado
        self.lbl_msg = QLabel("Presiona  Grabar  para empezar")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_font(self.lbl_msg, 13)
        self.lbl_msg.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        card_lay.addWidget(self.lbl_msg)

        # Barra de progreso visual (segmentos animados)
        self.lbl_vu = QLabel("")
        self.lbl_vu.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_font(self.lbl_vu, 18)
        self.lbl_vu.setStyleSheet("background: transparent; border: none; letter-spacing: 2px;")
        card_lay.addWidget(self.lbl_vu)

        # Botón grabar / detener
        self.btn_grabar = QPushButton("  🎙️  Grabar")
        self.btn_grabar.setFixedHeight(48)
        set_font(self.btn_grabar, 14, bold=True)
        style_primary(self.btn_grabar)
        self.btn_grabar.clicked.connect(self._toggle_grabacion)
        card_lay.addWidget(self.btn_grabar)

        root.addWidget(self.card)

        # ── Sección transcripción ──────────────────────────────────────────────
        self.lbl_trans = QLabel("Transcripción")
        set_font(self.lbl_trans, 14, bold=True)
        self.lbl_trans.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        root.addWidget(self.lbl_trans)

        self.txt_transcripcion = QTextEdit()
        self.txt_transcripcion.setPlaceholderText(
            "El texto transcripto aparecerá aquí. Puedes editarlo antes de guardar.")
        self.txt_transcripcion.setMinimumHeight(120)
        self.txt_transcripcion.setStyleSheet(
            f"QTextEdit {{ background: {c('surface')}; color: {c('text')}; "
            f"border: 1.5px solid {c('border')}; border-radius: 10px; padding: 12px; }}"
        )
        set_font(self.txt_transcripcion, 13)
        root.addWidget(self.txt_transcripcion)

        # ── Fila categoría + guardar ───────────────────────────────────────────
        fila = QHBoxLayout()
        fila.setSpacing(12)

        self.lbl_cat = QLabel("Categoría:")
        set_font(self.lbl_cat, 13)
        self.lbl_cat.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        fila.addWidget(self.lbl_cat)

        self.cmb_categoria = QComboBox()
        self.cmb_categoria.setFixedHeight(36)
        set_font(self.cmb_categoria, 13)
        self.cmb_categoria.setStyleSheet(
            f"QComboBox {{ background: {c('surface')}; color: {c('text')}; "
            f"border: 1.5px solid {c('border')}; border-radius: 8px; padding: 4px 10px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: {c('surface')}; color: {c('text')}; "
            f"selection-background-color: {c('primary')}; }}"
        )
        fila.addWidget(self.cmb_categoria)
        fila.addStretch()

        self.btn_guardar = QPushButton("  💾  Guardar en cuaderno")
        self.btn_guardar.setFixedHeight(40)
        set_font(self.btn_guardar, 13, bold=True)
        style_primary(self.btn_guardar)
        self.btn_guardar.setEnabled(False)
        self.btn_guardar.clicked.connect(self._guardar_nota)
        fila.addWidget(self.btn_guardar)

        root.addLayout(fila)

        # ── Aviso dependencias ─────────────────────────────────────────────────
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setWordWrap(True)
        set_font(self.lbl_aviso, 11)
        self.lbl_aviso.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        root.addWidget(self.lbl_aviso)

        self._verificar_dependencias()
        root.addStretch()

        # Timer VU-meter (parpadeo durante grabación)
        self._vu_timer = QTimer(self)
        self._vu_timer.setInterval(400)
        self._vu_timer.timeout.connect(self._animar_vu)
        self._vu_fase = 0

        self._refrescar_categorias(mantener_seleccion=False)

    # ── Categorías (compartidas con los "cursos" de Flashcards) ────────────────
    def _refrescar_categorias(self, mantener_seleccion: bool = True):
        """Repuebla el combo de categoría desde los cursos de Flashcards."""
        anterior = self.cmb_categoria.currentText() if mantener_seleccion else None
        self.cmb_categoria.blockSignals(True)
        self.cmb_categoria.clear()
        cursos = self.cerebro.obtener_cursos()

        if not cursos:
            self.cmb_categoria.addItem("— Crea un curso en Flashcards —")
            self.cmb_categoria.setEnabled(False)
        else:
            self.cmb_categoria.setEnabled(True)
            for curso in cursos:
                self.cmb_categoria.addItem(curso["nombre"])
            if anterior:
                idx = self.cmb_categoria.findText(anterior)
                if idx >= 0:
                    self.cmb_categoria.setCurrentIndex(idx)

        self.cmb_categoria.blockSignals(False)
        # Si no hay cursos disponibles, no se puede guardar la nota todavía.
        if not cursos:
            self.btn_guardar.setEnabled(False)

    def actualizar_categorias(self):
        """Punto de entrada público: llamado cuando cambian los cursos en Flashcards."""
        self._refrescar_categorias()

    # ── Tema ──────────────────────────────────────────────────────────────────
    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.lbl_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_sub.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_trans.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_cat.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_msg.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_aviso.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_tiempo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none; letter-spacing: 3px;")
        self.card.refresh()
        self.txt_transcripcion.setStyleSheet(
            f"QTextEdit {{ background: {c('surface')}; color: {c('text')}; "
            f"border: 1.5px solid {c('border')}; border-radius: 10px; padding: 12px; }}"
        )
        self.cmb_categoria.setStyleSheet(
            f"QComboBox {{ background: {c('surface')}; color: {c('text')}; "
            f"border: 1.5px solid {c('border')}; border-radius: 8px; padding: 4px 10px; }}"
            f"QComboBox::drop-down {{ border: none; }}"
            f"QComboBox QAbstractItemView {{ background: {c('surface')}; color: {c('text')}; "
            f"selection-background-color: {c('primary')}; }}"
        )
        if self._grabando:
            style_primary(self.btn_grabar, danger=True)
        else:
            style_primary(self.btn_grabar)
        style_primary(self.btn_guardar)

    # ── Verificación de dependencias ───────────────────────────────────────────
    def _verificar_dependencias(self):
        faltantes = []
        try:
            import whisper  # noqa
        except (ImportError, Exception):
            faltantes.append("openai-whisper")
        try:
            import sounddevice  # noqa
        except (ImportError, Exception):
            faltantes.append("sounddevice")
        try:
            import soundfile  # noqa
        except (ImportError, Exception):
            faltantes.append("soundfile")

        if faltantes:
            pkgs = "  ".join(f"pip install {p}" for p in faltantes)
            self.lbl_aviso.setText(
                f"⚠️  Faltan dependencias: {', '.join(faltantes)}\n"
                f"Instálalas con:  {pkgs}"
            )
            self.btn_grabar.setEnabled(False)
        else:
            self.lbl_aviso.setText("✅  Whisper listo · modelo small · transcripción local")

    # ── Grabación ──────────────────────────────────────────────────────────────
    def _toggle_grabacion(self):
        if not self._grabando:
            self._iniciar_grabacion()
        else:
            self._detener_grabacion()

    def _iniciar_grabacion(self):
        import tempfile, os as _os
        self._grabando      = True
        self._segundos_grab = 0
        self._ruta_wav      = _os.path.join(tempfile.gettempdir(), "neurocore_voz.wav")

        self.btn_grabar.setText("  ⏹️  Detener")
        style_primary(self.btn_grabar, danger=True)
        self.lbl_estado.setText("🔴")
        self.lbl_msg.setText("Grabando… habla con claridad")
        self.txt_transcripcion.clear()
        self.btn_guardar.setEnabled(False)
        self._timer_seg.start()
        self._vu_timer.start()

        self._worker_grab = GrabacionWorker(self._ruta_wav)
        self._hilo_grab   = QThread()
        self._worker_grab.moveToThread(self._hilo_grab)
        self._hilo_grab.started.connect(self._worker_grab.run)
        self._worker_grab.terminado.connect(self._on_grabacion_lista)
        self._worker_grab.error.connect(self._on_error_grabacion)
        self._hilo_grab.start()

    def _detener_grabacion(self):
        self._grabando = False
        self._timer_seg.stop()
        self._vu_timer.stop()
        self.lbl_vu.setText("")
        self.btn_grabar.setEnabled(False)
        self.lbl_estado.setText("⏳")
        self.lbl_msg.setText("Transcribiendo con Whisper…")
        if self._worker_grab:
            self._worker_grab.detener()

    def _tick_grabacion(self):
        self._segundos_grab += 1
        m, s = divmod(self._segundos_grab, 60)
        self.lbl_tiempo.setText(f"{m:02d}:{s:02d}")

    def _animar_vu(self):
        patrones = [
            "▁▃▅▇▅▃▁",
            "▃▅▇█▇▅▃",
            "▅▇█▇▅▃▁",
            "▇█▇▅▃▁▃",
        ]
        self.lbl_vu.setText(patrones[self._vu_fase % len(patrones)])
        self._vu_fase += 1

    def _on_grabacion_lista(self, ruta_wav: str):
        if self._hilo_grab:
            self._hilo_grab.quit()
            self._hilo_grab.wait()
        self._transcribir(ruta_wav)

    def _on_error_grabacion(self, msg: str):
        if self._hilo_grab:
            self._hilo_grab.quit()
        self.lbl_estado.setText("❌")
        self.lbl_msg.setText(f"Error al grabar: {msg}")
        self.btn_grabar.setText("  🎙️  Grabar")
        style_primary(self.btn_grabar, danger=False)
        self.btn_grabar.setEnabled(True)

    # ── Transcripción ──────────────────────────────────────────────────────────
    def _transcribir(self, ruta_wav: str):
        self._transcribiendo = True
        self._worker_whisper = WhisperWorker(ruta_wav)
        self._hilo_whisper   = QThread()
        self._worker_whisper.moveToThread(self._hilo_whisper)
        self._hilo_whisper.started.connect(self._worker_whisper.run)
        self._worker_whisper.terminado.connect(self._on_transcripcion_lista)
        self._worker_whisper.error.connect(self._on_error_whisper)
        self._hilo_whisper.start()

    def _on_transcripcion_lista(self, texto: str):
        self._transcribiendo = False
        if self._hilo_whisper:
            self._hilo_whisper.quit()
            self._hilo_whisper.wait()
        self.lbl_estado.setText("✅")
        hay_cursos = self.cmb_categoria.isEnabled()
        if hay_cursos:
            self.lbl_msg.setText("¡Transcripción lista! Edita si quieres y guarda.")
        else:
            self.lbl_msg.setText("¡Transcripción lista! Crea un curso en Flashcards para poder guardar.")
        self.txt_transcripcion.setPlainText(texto)
        self.btn_guardar.setEnabled(hay_cursos)
        self.btn_grabar.setText("  🎙️  Nueva grabación")
        style_primary(self.btn_grabar, danger=False)
        self.btn_grabar.setEnabled(True)

    def _on_error_whisper(self, msg: str):
        self._transcribiendo = False
        if self._hilo_whisper:
            self._hilo_whisper.quit()
        self.lbl_estado.setText("❌")
        self.lbl_msg.setText(f"Error en Whisper: {msg}")
        self.btn_grabar.setText("  🎙️  Grabar")
        style_primary(self.btn_grabar, danger=False)
        self.btn_grabar.setEnabled(True)

    # ── Guardar ────────────────────────────────────────────────────────────────
    def _guardar_nota(self):
        texto = self.txt_transcripcion.toPlainText().strip()
        if not texto:
            return
        categoria = self.cmb_categoria.currentText()
        self.cerebro.guardar_en_el_cerebro(texto, categoria)
        self.lbl_msg.setText(f"✅  Nota guardada en '{categoria}'")
        self.txt_transcripcion.clear()
        self.btn_guardar.setEnabled(False)
        self.lbl_estado.setText("🎙️")
        self.lbl_tiempo.setText("00:00")


class EstadisticasPanel(QWidget):
    def __init__(self, cerebro, parent=None):
        super().__init__(parent)
        self.cerebro = cerebro
        self._build()

    # ── Construcción del layout ────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = SectionHeader("Estadísticas de concentración")
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.bg_widget)
        vbox.setContentsMargins(40, 32, 40, 40)
        vbox.setSpacing(20)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Card: resumen estadístico ──────────────────────────────────────────
        self.stats_card = Card()
        sc_lay = QVBoxLayout(self.stats_card)
        sc_lay.setContentsMargins(32, 22, 32, 22)
        sc_lay.setSpacing(10)

        self.lbl_stats_title = make_label("Resumen estadístico", 14, bold=True)
        sc_lay.addWidget(self.lbl_stats_title)

        self.lbl_stats = make_label("Sin sesiones guardadas todavía.", 13, color_key="text2")
        self.lbl_stats.setWordWrap(True)
        sc_lay.addWidget(self.lbl_stats)
        vbox.addWidget(self.stats_card)

        # ── Card: gráfico de barras ────────────────────────────────────────────
        self.chart_card = Card()
        cc_lay = QVBoxLayout(self.chart_card)
        cc_lay.setContentsMargins(32, 22, 32, 28)
        cc_lay.setSpacing(10)

        hdr_chart = QHBoxLayout()
        self.lbl_chart_title = make_label("Tiempo por sesión (minutos)", 14, bold=True)
        hdr_chart.addWidget(self.lbl_chart_title)
        hdr_chart.addStretch()
        self.lbl_chart_hint = make_label("S1 = Sesión 1, S2 = Sesión 2, …", 11, color_key="text3")
        hdr_chart.addWidget(self.lbl_chart_hint)
        cc_lay.addLayout(hdr_chart)

        self.chart = BarChartWidget()
        cc_lay.addWidget(self.chart)
        vbox.addWidget(self.chart_card)

        # ── Card: lista de sesiones ────────────────────────────────────────────
        self.sessions_card = Card()
        sl_lay = QVBoxLayout(self.sessions_card)
        sl_lay.setContentsMargins(32, 22, 32, 22)
        sl_lay.setSpacing(10)

        self.lbl_sessions_title = make_label("Sesiones guardadas", 14, bold=True)
        sl_lay.addWidget(self.lbl_sessions_title)

        self.sessions_container = QWidget()
        self.sessions_container.setStyleSheet("background: transparent;")
        self.sessions_vlay = QVBoxLayout(self.sessions_container)
        self.sessions_vlay.setContentsMargins(0, 0, 0, 0)
        self.sessions_vlay.setSpacing(8)
        self.sessions_vlay.setAlignment(Qt.AlignmentFlag.AlignTop)
        sl_lay.addWidget(self.sessions_container)
        vbox.addWidget(self.sessions_card)

        scroll.setWidget(self.bg_widget)
        root.addWidget(scroll)
        FadeIn(self.bg_widget)

    # ── Carga y refresco de datos ──────────────────────────────────────────────
    def cargar_datos(self):
        """Consulta el cerebro, actualiza gráfico + estadísticas + lista."""
        sessions = self.cerebro.obtener_sesiones_guardadas()

        # ── Gráfico ───────────────────────────────────────────────────────────
        self.chart.set_data(sessions)

        # ── Estadísticas ──────────────────────────────────────────────────────
        if not sessions:
            self.lbl_stats.setText("Sin sesiones guardadas todavía.")
        else:
            values = [s["minutos"] for s in sessions]
            n      = len(values)
            media  = _stats_lib.mean(values)
            desvio = _stats_lib.stdev(values) if n > 1 else 0.0
            varian = _stats_lib.variance(values) if n > 1 else 0.0
            total  = sum(values)
            maximo = max(values)
            minimo = min(values)

            try:
                moda_val = _stats_lib.mode(values)
                moda_str = f"{moda_val} min"
            except _stats_lib.StatisticsError:
                moda_str = "multimodal"

            valores_descanso = [s.get("minutos_descanso", 0) for s in sessions]
            total_descanso   = sum(valores_descanso)
            media_descanso   = _stats_lib.mean(valores_descanso) if valores_descanso else 0.0
            h_desc, m_desc   = divmod(total_descanso, 60)

            h_total, m_total = divmod(total, 60)
            linea1 = (f"Sesiones: {n}   |   Media: {media:.1f} min   |   "
                      f"Desv. estándar: {desvio:.1f} min   |   Moda: {moda_str}")
            linea2 = (f"Varianza: {varian:.1f}   |   Mínimo: {minimo} min   |   "
                      f"Máximo: {maximo} min   |   Total enfocado: {h_total} h {m_total} min")
            linea3 = (f"☕ Descanso total: {h_desc} h {m_desc} min   |   "
                      f"Media de descanso: {media_descanso:.1f} min/sesión")
            self.lbl_stats.setText(f"{linea1}\n{linea2}\n{linea3}")

        # ── Lista de sesiones ─────────────────────────────────────────────────
        # Limpiar filas anteriores
        while self.sessions_vlay.count():
            item = self.sessions_vlay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not sessions:
            lbl_vacio = make_label(
                "No hay sesiones guardadas aún.\n"
                "Completa un pomodoro y guárdalo con el botón 🗑 en la pantalla de Enfoque.",
                13, color_key="text2"
            )
            lbl_vacio.setWordWrap(True)
            self.sessions_vlay.addWidget(lbl_vacio)
        else:
            for s in sessions:
                self.sessions_vlay.addWidget(self._make_session_row(s))

    def _make_session_row(self, session: dict) -> QFrame:
        """Construye la fila visual de una sesión con su botón de borrar."""
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background: {c("surface2")};
                border: 1px solid {c("border")};
                border-radius: 10px;
            }}
        """)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(16, 10, 10, 10)
        lay.setSpacing(12)

        # Número de sesión
        lbl_num = make_label(f"#{session['id']}", 13, bold=True, color_key="primary")
        lbl_num.setFixedWidth(36)
        lay.addWidget(lbl_num)

        # Nombre
        lbl_name = make_label(session["nombre"], 13)
        lay.addWidget(lbl_name, stretch=1)

        # Duración (estudio)
        h, m = divmod(session["minutos"], 60)
        dur_str = f"{h}h {m}min" if h > 0 else f"{m} min"
        lbl_time = make_label(f"📚 {dur_str}", 13, color_key="text2")
        lbl_time.setFixedWidth(88)
        lay.addWidget(lbl_time)

        # Duración (descanso)
        min_descanso = session.get("minutos_descanso", 0)
        h_d, m_d = divmod(min_descanso, 60)
        desc_str = f"{h_d}h {m_d}min" if h_d > 0 else f"{m_d} min"
        lbl_descanso = make_label(f"☕ {desc_str}", 13, color_key="text2")
        lbl_descanso.setFixedWidth(88)
        lay.addWidget(lbl_descanso)

        # Fecha (solo la parte de la fecha, sin hora)
        fecha_raw = session.get("fecha", "")
        if fecha_raw:
            lbl_fecha = make_label(str(fecha_raw)[:10], 11, color_key="text3")
            lbl_fecha.setFixedWidth(88)
            lay.addWidget(lbl_fecha)

        # Botón eliminar esta sesión
        btn_del = QPushButton("🗑")
        btn_del.setFixedSize(34, 34)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(
            f"QPushButton {{ color: {c('danger')}; background: transparent; border: none;"
            f" font-size: 15px; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {c('danger_bg')}; }}"
        )
        btn_del.setToolTip(f"Eliminar {session['nombre']}")
        btn_del.clicked.connect(
            lambda _, sid=session["id"], sn=session["nombre"]: self._confirmar_borrar(sid, sn)
        )
        lay.addWidget(btn_del)
        return row

    def _confirmar_borrar(self, session_id: int, session_name: str):
        """Pide confirmación antes de eliminar una sesión guardada."""
        from PyQt6.QtWidgets import QMessageBox
        box = QMessageBox(self)

        box.setStyleSheet(_msgbox_style())
        box.setWindowTitle("Eliminar sesión")
        box.setText(f"¿Eliminar permanentemente\n\"{session_name}\"?")
        box.setIcon(QMessageBox.Icon.Warning)
        btn_si = box.addButton("  Sí, eliminar  ", QMessageBox.ButtonRole.YesRole)
        box.addButton("  Cancelar  ", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == btn_si:
            self.cerebro.borrar_sesion(session_id)
            self.cargar_datos()

    # ── Tema ──────────────────────────────────────────────────────────────────
    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        self.header.refresh()
        self.stats_card.refresh()
        self.chart_card.refresh()
        self.sessions_card.refresh()
        self.lbl_stats_title.setStyleSheet(
            f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_stats.setStyleSheet(
            f"color: {c('text2')}; background: transparent; border: none;")
        self.lbl_chart_title.setStyleSheet(
            f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_chart_hint.setStyleSheet(
            f"color: {c('text3')}; background: transparent; border: none;")
        self.lbl_sessions_title.setStyleSheet(
            f"color: {c('text')}; background: transparent; border: none;")
        self.chart.update()
        # Recargar filas de sesiones con los nuevos colores
        self.cargar_datos()


# ═══════════════════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def _formatear_respuesta_ia(texto: str) -> str:
    """
    Convierte el texto plano que devuelve el Asistente IA (ya sin LaTeX,
    ver core/groq_assistant.limpiar_formato_ia) en HTML simple apto para
    un QLabel. Solo interpreta lo mínimo indispensable para que se lea
    bien: **negrita** y viñetas con "-". No agrega colores, iconos ni
    nada que el usuario no haya pedido.
    """
    import re as _re
    import html as html_lib

    texto = html_lib.escape(texto)

    # Encabezados "### Texto" -> negrita (sin agregar tamaños ni iconos extra)
    texto = _re.sub(r"^\s{0,3}#{1,6}\s*(.+)$", r"<b>\1</b>", texto, flags=_re.MULTILINE)

    # **negrita** -> <b>negrita</b>
    texto = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)

    # Líneas "- algo" -> "• algo"
    lineas = texto.split("\n")
    lineas = [_re.sub(r"^(\s*)-\s+", r"\1• ", ln) for ln in lineas]
    texto = "\n".join(lineas)

    return texto.replace("\n", "<br>")


class AIWorker(QObject):
    """Ejecuta la consulta a Groq (con búsqueda web previa) en un QThread
    para no congelar la interfaz mientras se espera la respuesta de red."""
    terminado = pyqtSignal(dict)   # {"respuesta": str, "fuentes": [ {titulo,url,resumen}, ... ]}
    error     = pyqtSignal(str)

    def __init__(self, pregunta: str):
        super().__init__()
        self._pregunta = pregunta

    def run(self):
        try:
            resultado = _ia_responder_con_busqueda(self._pregunta)
            self.terminado.emit(resultado)
        except Exception as e:
            self.error.emit(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  PANEL: Asistente IA (Groq + búsqueda web real)
# ═══════════════════════════════════════════════════════════════════════════════

class AsistenteIAPanel(QWidget):
    """
    Chat con IA (Groq) que primero busca en internet (DuckDuckGo) y luego
    responde citando fuentes. Los enlaces mostrados son URLs reales de las
    páginas web encontradas (no redirects de un buscador): se pueden abrir
    directamente en el navegador predeterminado del usuario.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hilo = None
        self._worker = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = SectionHeader("Asistente IA")
        root.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.bg_widget = QWidget()
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        vbox = QVBoxLayout(self.bg_widget)
        vbox.setContentsMargins(60, 36, 60, 36)
        vbox.setSpacing(20)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Card de pregunta ──────────────────────────────────────
        self.card_search = Card()
        cl = QVBoxLayout(self.card_search)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(0)

        self.lbl_titulo = make_label("Pregúntale a la IA (con búsqueda en internet)", 14, bold=True)
        cl.addWidget(self.lbl_titulo)
        cl.addSpacing(6)

        lbl_sub = make_label(
            "La IA (Groq) busca en la web y responde citando sus fuentes, "
            "con enlaces reales que puedes abrir en tu navegador.",
            12, color_key="text2"
        )
        lbl_sub.setWordWrap(True)
        cl.addWidget(lbl_sub)
        cl.addSpacing(20)

        self.search_frame = QFrame()
        self.search_frame.setFixedHeight(52)
        self._style_search_frame()
        sf_lay = QHBoxLayout(self.search_frame)
        sf_lay.setContentsMargins(18, 0, 10, 0)
        sf_lay.setSpacing(8)

        self.lbl_icono = QLabel("💬")
        set_font(self.lbl_icono, 16)
        self.lbl_icono.setStyleSheet(f"background: transparent; border: none; color: {c('text2')};")
        sf_lay.addWidget(self.lbl_icono)

        self.entry_pregunta = QLineEdit()
        self.entry_pregunta.setPlaceholderText("Escribe tu pregunta…")
        set_font(self.entry_pregunta, 14)
        self.entry_pregunta.returnPressed.connect(self._preguntar)
        self._style_search_entry()
        sf_lay.addWidget(self.entry_pregunta)

        self.btn_preguntar = primary_btn("Preguntar", w=110, h=38)
        self.btn_preguntar.clicked.connect(self._preguntar)
        sf_lay.addWidget(self.btn_preguntar)
        cl.addWidget(self.search_frame)

        vbox.addWidget(self.card_search)

        if not _HAS_IA:
            self.lbl_estado = make_label(
                "⚠️  Falta instalar 'requests' (pip install requests) para usar el Asistente IA.",
                13, color_key="danger"
            )
        else:
            self.lbl_estado = make_label("", 13, color_key="text2")
        self.lbl_estado.setWordWrap(True)
        vbox.addWidget(self.lbl_estado)

        # ── Card de respuesta ────────────────────────────────────
        self.card_respuesta = Card()
        self.card_respuesta.setVisible(False)
        rl = QVBoxLayout(self.card_respuesta)
        rl.setContentsMargins(30, 24, 30, 24)
        rl.setSpacing(10)

        self.lbl_respuesta = QLabel("")
        self.lbl_respuesta.setWordWrap(True)
        self.lbl_respuesta.setTextFormat(Qt.TextFormat.RichText)
        set_font(self.lbl_respuesta, 13)
        self.lbl_respuesta.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        rl.addWidget(self.lbl_respuesta)

        vbox.addWidget(self.card_respuesta)

        self.lbl_fuentes_titulo = make_label("Fuentes (páginas web reales)", 12, bold=True, color_key="text2")
        self.lbl_fuentes_titulo.setVisible(False)
        vbox.addWidget(self.lbl_fuentes_titulo)

        self.fuentes_widget = QWidget()
        self.fuentes_widget.setStyleSheet("background: transparent;")
        self.fuentes_vlay = QVBoxLayout(self.fuentes_widget)
        self.fuentes_vlay.setContentsMargins(0, 0, 0, 0)
        self.fuentes_vlay.setSpacing(8)
        self.fuentes_vlay.setAlignment(Qt.AlignmentFlag.AlignTop)
        vbox.addWidget(self.fuentes_widget)

        scroll.setWidget(self.bg_widget)
        root.addWidget(scroll)
        FadeIn(self.bg_widget)

    # ── Lógica ────────────────────────────────────────────────────
    def _preguntar(self):
        if not _HAS_IA:
            return

        pregunta = self.entry_pregunta.text().strip()
        if not pregunta:
            return

        self.btn_preguntar.setEnabled(False)
        self.entry_pregunta.setEnabled(False)
        self.lbl_estado.setText("⏳  Buscando en internet y consultando a la IA…")
        self.lbl_estado.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none; font-size: 13px;")
        self.card_respuesta.setVisible(False)
        self.lbl_fuentes_titulo.setVisible(False)
        self._limpiar_fuentes()
        QApplication.processEvents()

        self._worker = AIWorker(pregunta)
        self._hilo = QThread()
        self._worker.moveToThread(self._hilo)
        self._hilo.started.connect(self._worker.run)
        self._worker.terminado.connect(self._on_respuesta)
        self._worker.error.connect(self._on_error)
        self._hilo.start()

    def _on_respuesta(self, resultado: dict):
        self._finalizar_hilo()
        self.btn_preguntar.setEnabled(True)
        self.entry_pregunta.setEnabled(True)

        fuentes   = resultado.get("fuentes", [])
        respuesta = resultado.get("respuesta", "")

        if fuentes:
            self.lbl_estado.setText(f"✦  Respuesta generada con {len(fuentes)} fuente(s) reales de internet")
            self.lbl_estado.setStyleSheet(f"color: {c('primary')}; background: transparent; border: none; font-size: 13px;")
        else:
            self.lbl_estado.setText("⚠️  No se encontraron páginas web para esta consulta; respuesta generada solo con el conocimiento del modelo")
            self.lbl_estado.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none; font-size: 13px;")

        self.lbl_respuesta.setText(_formatear_respuesta_ia(respuesta))
        self.card_respuesta.setVisible(True)

        self._limpiar_fuentes()
        if fuentes:
            self.lbl_fuentes_titulo.setVisible(True)
            for i, f in enumerate(fuentes, 1):
                self.fuentes_vlay.addWidget(self._make_fuente_card(i, f))

    def _on_error(self, mensaje: str):
        self._finalizar_hilo()
        self.btn_preguntar.setEnabled(True)
        self.entry_pregunta.setEnabled(True)
        self.lbl_estado.setText(f"❌  {mensaje}")
        self.lbl_estado.setStyleSheet(f"color: {c('danger')}; background: transparent; border: none; font-size: 13px;")
        self.card_respuesta.setVisible(False)

    def _finalizar_hilo(self):
        if self._hilo:
            self._hilo.quit()
            self._hilo.wait()
        self._hilo = None
        self._worker = None

    def _limpiar_fuentes(self):
        while self.fuentes_vlay.count():
            item = self.fuentes_vlay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _make_fuente_card(self, rank: int, fuente: dict) -> QFrame:
        """Tarjeta con el enlace REAL de la página web encontrada (no un
        redirect del buscador): se abre en el navegador predeterminado
        del sistema al hacer clic, gracias a setOpenExternalLinks(True)."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {c('surface')};
                border: 1px solid {c('border')};
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)

        import html as html_lib
        titulo  = html_lib.escape(fuente.get("titulo", ""))
        url     = fuente.get("url", "")
        resumen = html_lib.escape(fuente.get("resumen", ""))

        lbl_link = QLabel(
            f'<a href="{html_lib.escape(url)}" style="color:{c("primary")}; text-decoration:none;">'
            f'[{rank}] {titulo}</a>'
        )
        lbl_link.setTextFormat(Qt.TextFormat.RichText)
        lbl_link.setOpenExternalLinks(True)
        lbl_link.setWordWrap(True)
        set_font(lbl_link, 13, bold=True)
        lbl_link.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(lbl_link)

        lbl_url = QLabel(html_lib.escape(url))
        lbl_url.setWordWrap(True)
        set_font(lbl_url, 11)
        lbl_url.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        lay.addWidget(lbl_url)

        if resumen:
            lbl_resumen = QLabel(resumen)
            lbl_resumen.setWordWrap(True)
            set_font(lbl_resumen, 12)
            lbl_resumen.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
            lay.addWidget(lbl_resumen)

        return card

    # ── Estilos ───────────────────────────────────────────────────
    def _style_search_frame(self):
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background: {c("surface2")};
                border: 1.5px solid {c("border")};
                border-radius: 26px;
            }}
        """)

    def _style_search_entry(self):
        self.entry_pregunta.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {c("text")};
                border: none;
                padding: 0;
            }}
        """)

    def refresh_theme(self):
        self.setStyleSheet(f"background: {c('bg')};")
        self.bg_widget.setStyleSheet(f"background: {c('bg')};")
        self.header.refresh()
        self.card_search.refresh()
        self.card_respuesta.refresh()
        self._style_search_frame()
        self._style_search_entry()
        style_primary(self.btn_preguntar)
        self.lbl_icono.setStyleSheet(f"background: transparent; border: none; color: {c('text2')};")
        self.lbl_titulo.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_respuesta.setStyleSheet(f"color: {c('text')}; background: transparent; border: none;")
        self.lbl_fuentes_titulo.setStyleSheet(f"color: {c('text2')}; background: transparent; border: none;")
        self._limpiar_fuentes()


class VentanaPrincipal(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroCore AI")
        self.resize(1020, 680)
        self.setMinimumSize(820, 560)
        self._dark = False
        self.cerebro = BrainService()
        self._active_idx = 0
        self._build()

    def _build(self):
        self.setStyleSheet(f"QMainWindow {{ background: {c('bg')}; }}")

        central = QWidget()
        central.setStyleSheet(f"background: {c('bg')};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ────────────────────────────────────────────────────────────
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setFixedWidth(220)
        self._style_sidebar()
        sb_lay = QVBoxLayout(self.sidebar_frame)
        sb_lay.setContentsMargins(12, 28, 12, 20)
        sb_lay.setSpacing(0)

        # Logo
        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        self.lbl_logo_icon = QLabel("◈")
        set_font(self.lbl_logo_icon, 24)
        self.lbl_logo_icon.setStyleSheet(
            f"color: {c('primary')}; background: transparent; border: none;")
        logo_row.addWidget(self.lbl_logo_icon)
        self.lbl_logo_name = QLabel("NeuroCore")
        set_font(self.lbl_logo_name, 16, bold=True)
        self.lbl_logo_name.setStyleSheet(
            f"color: {c('text')}; background: transparent; border: none;")
        logo_row.addWidget(self.lbl_logo_name)
        logo_row.addStretch()
        sb_lay.addLayout(logo_row)
        sb_lay.addSpacing(16)
        self.sep1 = h_line()
        sb_lay.addWidget(self.sep1)
        sb_lay.addSpacing(12)

        # ── Botones de navegación ─────────────────────────────────────────────
        NAV = [
            ("⏱",  "Enfoque"),
            ("📓",  "Cuaderno"),
            ("🧠",  "Find Notes"),
            ("🃏",  "Flashcards"),
            ("🎙️",  "Notas de Voz"),
            ("💬",  "Asistente IA"),
            ("📊",  "Estadísticas"),
        ]
        self._nav_btns = []
        for i, (ico, txt) in enumerate(NAV):
            btn = NavButton(ico, txt)
            btn.clicked.connect(lambda _, idx=i: self._nav_to(idx))
            sb_lay.addWidget(btn)
            sb_lay.addSpacing(4)
            self._nav_btns.append(btn)

        sb_lay.addStretch()
        self.sep2 = h_line()
        sb_lay.addWidget(self.sep2)
        sb_lay.addSpacing(12)

        self.btn_mode = NavButton("☾", "Modo oscuro")
        self.btn_mode.setCheckable(False)
        self.btn_mode.clicked.connect(self._toggle_theme)
        sb_lay.addWidget(self.btn_mode)

        root.addWidget(self.sidebar_frame)

        # Divisor
        self.div = QFrame()
        self.div.setFixedWidth(1)
        self.div.setStyleSheet(f"background: {c('border')};")
        root.addWidget(self.div)

        # ── Stack de paneles ───────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background: {c('bg')};")

        self.panel_pomodoro     = PomodoroPanel(self.cerebro)
        self.panel_cuaderno     = CuadernoPanel(self.cerebro)
        self.panel_buscador     = BuscadorPanel(self.cerebro)
        self.panel_flashcards   = FlashcardsPanel(self.cerebro)
        self.panel_notas_voz    = NotasVozPanel(self.cerebro)
        self.panel_asistente_ia = AsistenteIAPanel()
        self.panel_estadisticas = EstadisticasPanel(self.cerebro)

        self.stack.addWidget(self.panel_pomodoro)       # índice 0
        self.stack.addWidget(self.panel_cuaderno)       # índice 1
        self.stack.addWidget(self.panel_buscador)       # índice 2
        self.stack.addWidget(self.panel_flashcards)     # índice 3
        self.stack.addWidget(self.panel_notas_voz)      # índice 4
        self.stack.addWidget(self.panel_asistente_ia)   # índice 5
        self.stack.addWidget(self.panel_estadisticas)   # índice 6

        root.addWidget(self.stack)

        # ── Señales entre paneles ──────────────────────────────────────────────
        self.panel_pomodoro.sesion_guardada.connect(self.panel_estadisticas.cargar_datos)
        # El cuaderno puede convertir un apunte en flashcard (abre pestaña Crear)
        self.panel_cuaderno.convertir_en_flashcard.connect(self._ir_a_crear_flashcard)
        # Los cursos se gestionan desde Flashcards y se comparten como
        # "categoría" en Cuaderno y Notas de Voz. Al crear/eliminar un curso,
        # ambos paneles refrescan su lista al instante.
        self.panel_flashcards.cursos_actualizados.connect(self.panel_cuaderno.actualizar_categorias)
        self.panel_flashcards.cursos_actualizados.connect(self.panel_notas_voz.actualizar_categorias)

        self._nav_to(0)

    def _style_sidebar(self):
        self.sidebar_frame.setStyleSheet(
            f"QFrame {{ background: {c('sidebar')}; border: none; }}")

    def _nav_to(self, idx: int):
        self._active_idx = idx
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)
        if idx == 1:
            self.panel_cuaderno.actualizar_categorias()
        if idx == 3:
            self.panel_flashcards.refrescar()
        if idx == 4:
            self.panel_notas_voz.actualizar_categorias()
        if idx == 6:
            self.panel_estadisticas.cargar_datos()

    def _ir_a_crear_flashcard(self, respuesta: str):
        """Recibe el texto del Cuaderno y lo pre-carga en la vista Crear."""
        self.panel_flashcards.precargar_respuesta(respuesta)
        self._nav_to(3)

    def _toggle_theme(self):
        self._dark = not self._dark
        _T.clear()
        _T.update(DARK if self._dark else LIGHT)
        icon = "☀" if self._dark else "☾"
        txt  = "Modo claro" if self._dark else "Modo oscuro"
        self.btn_mode.setText(f"  {icon}   {txt}")
        self._apply_theme()

    def _apply_theme(self):
        # Stylesheet global — cubre scrollbars, tooltips y diálogos del sistema
        _app.setStyleSheet(f"""
            QScrollBar:vertical {{
                background: {c("surface2")}; width: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {c("border")}; border-radius: 4px; min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c("primary")};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {c("surface2")}; height: 8px; border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {c("border")}; border-radius: 4px; min-width: 24px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {c("primary")};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QToolTip {{
                background: {c("surface")}; color: {c("text")};
                border: 1px solid {c("border")}; border-radius: 6px;
                padding: 4px 8px; font-size: 12px;
            }}
        """)
        self.setStyleSheet(f"QMainWindow {{ background: {c('bg')}; }}")
        self.centralWidget().setStyleSheet(f"background: {c('bg')};")
        self._style_sidebar()
        self.lbl_logo_icon.setStyleSheet(
            f"color: {c('primary')}; background: transparent; border: none;")
        self.lbl_logo_name.setStyleSheet(
            f"color: {c('text')}; background: transparent; border: none;")
        self.sep1.setStyleSheet(f"background: {c('border')}; border: none;")
        self.sep2.setStyleSheet(f"background: {c('border')}; border: none;")
        self.div.setStyleSheet(f"background: {c('border')};")
        self.btn_mode.refresh()
        for btn in self._nav_btns:
            btn.refresh()
        self.stack.setStyleSheet(f"background: {c('bg')};")
        self.panel_pomodoro.refresh_theme()
        self.panel_cuaderno.refresh_theme()
        self.panel_buscador.refresh_theme()
        self.panel_flashcards.refresh_theme()
        self.panel_notas_voz.refresh_theme()
        self.panel_asistente_ia.refresh_theme()
        self.panel_estadisticas.refresh_theme()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    _app.setFont(QFont("Segoe UI", 13))
    window = VentanaPrincipal()
    window.show()
    sys.exit(_app.exec())