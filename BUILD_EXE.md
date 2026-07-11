# Cómo compilar Second Brain AI a .exe (Windows)

## Requisito importante
Esto **debe hacerse en una PC con Windows** (no en Mac/Linux). PyInstaller no
hace compilación cruzada: empaqueta para el sistema operativo en el que se
ejecuta. Si compilas en Windows obtienes un `.exe` de Windows; no hay forma
de generar un `.exe` desde Linux o Mac.

Usa Python 3.10 o 3.11 de **64 bits** (mismo Python con el que ya corre tu
proyecto normalmente).

## Pasos rápidos

```bat
build.bat
```

Este script crea un entorno virtual, instala todo, y compila. Al terminar,
el ejecutable queda en:

```
dist\Second Brain AI\Second Brain AI.exe
```

## Pasos manuales (si prefieres hacerlo tú mismo)

```bat
python -m venv venv_build
venv_build\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build_exe.spec
```

## Cosas que ya te dejé resueltas

- **Bug de la base de datos arreglado**: antes, la ruta de `brain.db` se
  calculaba con `__file__`, lo cual se rompe dentro de un `.exe` congelado
  (PyInstaller extrae el proyecto a una carpeta temporal que se borra al
  cerrar la app → perderías tus notas cada vez). Ahora, cuando la app corre
  como `.exe`, guarda la base de datos en
  `%APPDATA%\Second Brain AI\data\brain.db`, que persiste entre sesiones,
  igual que hace cualquier programa de escritorio instalado.
- **`build_exe.spec`**: ya incluye `collect_all()` para las librerías más
  propensas a fallar al congelarse (`torch`, `sentence_transformers`,
  `whisper`, `sounddevice`, etc.), que de otro modo suelen dar errores tipo
  `ModuleNotFoundError` o `FileNotFoundError` con archivos de datos internos.

## Advertencias realistas antes de empezar

1. **El .exe va a pesar varios GB.** El proyecto usa `torch` (para Whisper y
   sentence-transformers), que por sí solo pesa cientos de MB a más de 1 GB.
   Esto es normal para apps con IA local, no es un error tuyo.
2. **La compilación tarda varios minutos** (puede ser 5-15 min dependiendo
   de tu PC) porque PyInstaller tiene que analizar y copiar todas las
   dependencias de `torch`, `transformers`, etc.
3. **Primer arranque necesita internet.** Ni el modelo de Whisper
   (`whisper.load_model("small")`, ~500 MB) ni el modelo de embeddings
   (`all-MiniLM-L6-v2`) se descargan en tiempo de compilación — se descargan
   la primera vez que el usuario usa "Notas de Voz" o "Buscador IA",
   directo desde internet a la caché del usuario. Si necesitas que funcione
   sin internet desde el primer uso, dímelo y armamos una versión que
   pre-descargue y empaquete los modelos dentro del .exe (lo hace bastante
   más pesado, pero funciona offline desde el arranque).
4. **Usa `--onedir` (ya configurado en el .spec), no `--onefile`.** Con
   `--onefile` el .exe se auto-extrae en una carpeta temporal cada vez que
   se abre, lo cual con `torch` de por medio puede tardar 30-60 segundos
   solo en arrancar. Con `--onedir` (carpeta con el .exe + sus archivos al
   lado) el arranque es mucho más rápido. La contra es que tienes que
   distribuir la carpeta completa, no un solo archivo — para eso, comprime
   `dist\Second Brain AI` en un .zip antes de compartirlo.
5. **Micrófono (sounddevice)**: en algunas PCs Windows hace falta tener
   instalado el "Microsoft Visual C++ Redistributable" para que
   `sounddevice`/PortAudio funcione. Es gratis y lo descarga cualquier
   usuario desde la página de Microsoft si llegara a fallar la grabación.

## Problemas comunes y solución

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'X'` al abrir el .exe | Falta agregar 'X' a `hiddenimports` | Agrega `"X"` a la lista `hiddenimports` en `build_exe.spec` y vuelve a compilar |
| La app abre y se cierra sola sin mensaje | Falta una dependencia de datos (assets) | Compila con `console=True` en el `.spec` para ver el error real en una ventana de consola |
| Grabación de voz no funciona en la PC de otro usuario | Falta el Visual C++ Redistributable | Pedirle que lo instale desde microsoft.com |
| El .exe tarda mucho en abrir | Estás usando `--onefile` | Usa `--onedir` (ya es lo que hace `build_exe.spec`) |
| Antivirus marca el .exe como sospechoso | Falso positivo común en apps compiladas con PyInstaller | Agregar excepción, o firmar el ejecutable con un certificado de código si lo vas a distribuir públicamente |
