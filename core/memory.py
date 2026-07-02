import sqlite3
from app.config import Config

class DatabaseManager:
    def __init__(self):
        # Usamos la ruta que definimos en el archivo de configuración
        self.conn = sqlite3.connect(Config.DB_PATH)
        self.cursor = self.conn.cursor()
        self._crear_tablas()

    def _crear_tablas(self):
        # Creamos la tabla si no existe (id, contenido del estudio, y categoría)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS recuerdos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contenido TEXT NOT NULL,
                categoria TEXT
            )
        ''')

        # === NUEVA TABLA PARA LOS POMODOROS ===
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sesiones_estudio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                duracion INTEGER
            )
        ''')
        self.conn.commit()

        # === NUEVA TABLA PARA SESIONES AGRUPADAS Y CONSOLIDADAS ===
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sesiones_guardadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    duracion_total INTEGER NOT NULL,
                    fecha TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        self.conn.commit()

    # === NUEVOS MÉTODOS AL FINAL DE LA CLASE ===
    def insertar_sesion_estudio(self, duracion_minutos):
        """Guarda un registro de un Pomodoro completado."""
        self.cursor.execute('INSERT INTO sesiones_estudio (duracion) VALUES (?)', (duracion_minutos,))
        self.conn.commit()

    def obtener_total_minutos_estudio(self):
        """Suma todos los minutos guardados en la tabla."""
        self.cursor.execute('SELECT SUM(duracion) FROM sesiones_estudio')
        resultado = self.cursor.fetchone()[0]
        return resultado if resultado else 0

    def guardar(self, texto, categoria="General"):
        self.cursor.execute('INSERT INTO recuerdos (contenido, categoria) VALUES (?, ?)', (texto, categoria))
        self.conn.commit()

    def obtener_todos(self):
        self.cursor.execute('SELECT * FROM recuerdos')
        return self.cursor.fetchall()

    def eliminar_apunte(self, contenido_texto):
        """Elimina un apunte de la base de datos buscando su contenido exacto."""
        # Ejecutamos el borrado en la tabla 'recuerdos' buscando en la columna 'contenido'
        self.cursor.execute("DELETE FROM recuerdos WHERE contenido = ?", (contenido_texto,))
        self.conn.commit()

    def borrar_sesiones_estudio(self):
        """Borra todo el historial de tiempo enfocado para reiniciar a cero."""
        self.cursor.execute('DELETE FROM sesiones_estudio')
        self.conn.commit()

    def insertar_sesion_guardada(self, nombre, duracion_total):
        """Guarda una sesión consolidada (ej: 'Sesión de concentración 1') con su tiempo total."""
        self.cursor.execute(
            'INSERT INTO sesiones_guardadas (nombre, duracion_total) VALUES (?, ?)',
            (nombre, duracion_total)
        )
        self.conn.commit()

    def obtener_todas_sesiones_guardadas(self):
        """Devuelve una lista con todas las sesiones consolidadas que el usuario guardó."""
        self.cursor.execute('SELECT id, nombre, duracion_total, fecha FROM sesiones_guardadas')
        return self.cursor.fetchall()

    def eliminar_sesion_guardada_por_id(self, id_sesion):
        """Borra una única sesión de la lista si el usuario se arrepiente, usando su ID."""
        self.cursor.execute('DELETE FROM sesiones_guardadas WHERE id = ?', (id_sesion,))
        self.conn.commit()

    def obtener_todos_apuntes(self):
        """Devuelve todos los apuntes como lista de dicts {id, contenido, categoria}."""
        self.cursor.execute('SELECT id, contenido, categoria FROM recuerdos ORDER BY categoria, id')
        rows = self.cursor.fetchall()
        return [{"id": r[0], "contenido": r[1], "categoria": r[2]} for r in rows]
