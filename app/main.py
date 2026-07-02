# app/main.py
import sys
import os

# Esto ayuda a que Python encuentre las carpetas core y services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtGui import QFont
from app.gui import _app, VentanaPrincipal

_app.setFont(QFont("Segoe UI", 13))

window = VentanaPrincipal()
window.show()

sys.exit(_app.exec())
