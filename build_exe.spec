# build_exe.spec
# ─────────────────────────────────────────────────────────────────────────
# Spec de PyInstaller para "Second Brain AI".
#
# CÓMO USARLO (en Windows, con Python 3.10/3.11 de 64 bits):
#   1) pip install -r requirements.txt
#   2) pip install pyinstaller
#   3) pyinstaller build_exe.spec
#   4) El ejecutable queda en  dist\Second Brain AI\Second Brain AI.exe
#
# NOTA: este .spec usa collect_all() para las librerías más problemáticas
# de congelar (torch, sentence-transformers, whisper, sounddevice). Esto
# hace el build más grande pero mucho más confiable: evita el típico
# "ModuleNotFoundError" o "FileNotFoundError: assets/mel_filters.npz"
# que da PyInstaller con estas librerías si se usan los valores por defecto.
# ─────────────────────────────────────────────────────────────────────────

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Librerías que necesitan TODO su contenido (código + datos + binarios .dll/.pyd)
# para funcionar una vez congeladas.
for pkg in ["torch", "sentence_transformers", "transformers", "tokenizers",
            "huggingface_hub", "whisper", "sounddevice", "soundfile",
            "pdfplumber"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print(f"[build_exe.spec] Aviso: no se pudo recolectar '{pkg}': {e}")

a = Analysis(
    ["app/main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["customtkinter"],  # no se usa realmente en el proyecto
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Second Brain AI",
    debug=False,
    strip=False,
    upx=False,          # UPX suele romper torch/PyQt6; se deja desactivado
    console=False,      # sin consola negra detrás de la ventana
    icon=None,          # pon aquí la ruta a un .ico si tienes uno
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="Second Brain AI",
)
