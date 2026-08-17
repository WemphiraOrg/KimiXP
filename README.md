# 🐾 KimiXP

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3%2B-5865F2?logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/License-GPL--3.0-green)](LICENSE)

**KimiXP** es un bot de Discord desarrollado en Python, enfocado en sistemas de experiencia, niveles, perfiles y administración de servidores.

El proyecto es **Open Source** y está pensado para que otras personas puedan utilizarlo, aprender de su código, modificarlo y contribuir a su desarrollo.

> 🚧 KimiXP se encuentra en desarrollo activo. Algunas partes del proyecto pueden cambiar con el tiempo.

---

## 📋 Tabla de Contenidos

- [✨ Características](#-características)
- [📁 Estructura del proyecto](#-estructura-del-proyecto)
- [⚠️ Antes de instalar](#-antes-de-instalar)
- [🚀 Instalación](#-instalación)
- [🛠️ Desarrollo](#-desarrollo)
- [🤝 Contribuir](#-contribuir)
- [🛟 Soporte](#-soporte)
- [🐛 Reportar errores](#-reportar-errores)
- [📜 Licencia](#-licencia)
- [👤 Desarrollador](#-desarrollador)
- [📌 Estado del proyecto](#-estado-del-proyecto)
- [💙 Gracias](#-gracias)

---

## ✨ Características

| Característica | Descripción |
|----------------|-------------|
| ⬆️ Sistema de XP y niveles | Gana experiencia y sube de nivel |
| 👤 Perfiles de usuario | Visualiza tu perfil y estadísticas |
| 🏆 Sistema de rangos | Desbloquea rangos según tu nivel |
| ⚙️ Administración | Comandos para moderar y gestionar el servidor |
| 🗄️ Base de datos | Persistencia de datos con SQLite |
| 🔧 Configuración | Variables de entorno para fácil configuración |
| 🧩 Arquitectura modular | Cogs para organizar comandos |
| 🔓 Código abierto | Modifica y contribuye libremente |

---

## 📁 Estructura del proyecto

```
KimiXP/
├── cogs/                 # Comandos y funcionalidades
│   ├── leveling.py      # Sistema de niveles y experiencia
│   ├── profile.py       # Perfiles de usuario
│   ├── admin.py         # Comandos de administración
│   └── help.py          # Sistema de ayuda
│
├── database/             # Lógica de base de datos
│   ├── database.py      # Conexión y operaciones
│   └── schema.sql       # Esquema de tablas
│
├── utils/                # Funciones auxiliares
│   └── config.py        # Configuración y variables
│
├── main.py              # Punto de entrada
├── requirements.txt     # Dependencias
├── .env.example         # Variables de entorno de ejemplo
├── LICENSE              # Licencia GPL-3.0
├── CONTRIBUTING.md      # Guía de contribución
└── README.md           # Este archivo
```

> La estructura puede cambiar a medida que KimiXP siga evolucionando.

---

## ⚠️ Antes de instalar

KimiXP está desarrollado principalmente para personas que tengan conocimientos básicos de **Python, Git y bots de Discord**.

No necesitas ser un experto para utilizarlo, pero algunas partes pueden requerir conocimientos técnicos y configuración manual.

### 📚 Conocimientos recomendados

| Tema | Descripción |
|------|-------------|
| 🐍 Python | Lenguaje base del proyecto |
| 🌿 Git | Control de versiones |
| ⚙️ Variables de entorno | Configuración sensible (`.env`) |
| 🤖 Discord API | Bots y aplicaciones de Discord |
| 📦 pip | Instalación de paquetes |
| 🖥️ Consola | Configuración básica del sistema |

> 💡 Si estás empezando, puedes utilizar KimiXP como una oportunidad para aprender.

---

## 🚀 Instalación

### 1. Clonar el repositorio

Si tienes Git instalado:

```bash
git clone https://github.com/WemphiraOrg/KimiXP.git
cd KimiXP
```

También puedes descargar el repositorio directamente como archivo ZIP desde GitHub.

---

### 2. Instalar dependencias

Dentro de la carpeta de KimiXP:

```bash
pip install -r requirements.txt
```

Esto instalará todas las librerías necesarias para ejecutar el proyecto.

**Dependencias principales:**

- `discord.py` — Librería para la API de Discord
- `python-dotenv` — Gestión de variables de entorno
- Otras dependencias en `requirements.txt`

---

### 3. Configurar variables de entorno

Copia `.env.example` y crea un archivo llamado `.env`:

```bash
# En Windows (PowerShell)
Copy-Item .env.example .env

# En Linux/macOS
cp .env.example .env
```

**Ejemplo de configuración (`.env`):**

```env
DISCORD_TOKEN=tu_token_aquí
```

Completa las variables necesarias para ejecutar KimiXP.

> 🔒 **Importante:** Nunca publiques tu token de Discord, contraseñas, claves API u otros datos sensibles. El archivo `.env` no debería subirse al repositorio.

---

### 4. Ejecutar KimiXP

Una vez configurado todo:

```bash
python main.py
```

Si la configuración es correcta, KimiXP iniciará y se conectará a Discord.

---

## 🛠️ Desarrollo

KimiXP utiliza una arquitectura modular para mantener sus diferentes funciones separadas.

| Directorio | Propósito |
|------------|-----------|
| `cogs/` | Comandos y funcionalidades principales |
| `database/` | Lógica de base de datos |
| `utils/` | Funciones auxiliares y configuración |

Si quieres añadir una nueva funcionalidad, intenta mantener esta organización para que el proyecto siga siendo fácil de entender y mantener.

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Puedes ayudar de diferentes maneras:

- 🐛 Reportando errores
- 💡 Proponiendo nuevas funciones
- 📝 Mejorando la documentación
- 🔧 Corrigiendo errores
- ⚡ Optimizando el código
- 🔀 Creando Pull Requests
- 💬 Ayudando a otros usuarios

Antes de realizar cambios importantes, revisa [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## 🛟 Soporte

Si tienes alguna duda, encontraste un fallo o quieres proponer una idea, puedes unirte al servidor oficial de soporte de KimiXP en Discord:

**🔗 https://discord.gg/sZyhRvzdx6**

En el servidor podrás:

- ❓ Hacer preguntas y resolver dudas
- 🐛 Reportar fallos y recibir ayuda
- 💡 Proponer nuevas ideas y funcionalidades
- 👥 Conocer a otras personas que utilizan el proyecto

---

## 🐛 Reportar errores

Si encuentras un problema con KimiXP, primero comprueba:

1. ✅ Que estás utilizando una versión actualizada
2. ✅ Que configuraste correctamente las variables de entorno
3. ✅ Que instalaste todas las dependencias
4. ✅ Que el problema no haya sido reportado anteriormente

Si el problema continúa, puedes abrir un **Issue** explicando qué ocurrió y, si es posible, incluyendo los errores que aparecen en la terminal.

> ⚠️ **No publiques tokens, contraseñas ni información privada en un Issue.**

---

## 📜 Licencia

KimiXP está disponible bajo la licencia **GNU General Public License v3.0 (GPL-3.0)**.

Puedes consultar los términos completos en el archivo [`LICENSE`](LICENSE).

---

## 👤 Desarrollador

**BrunoDevPe**

Desarrollador principal de KimiXP.

---

## 📌 Estado del proyecto

**🟢 En desarrollo activo.**

KimiXP continuará recibiendo mejoras, correcciones y nuevas funciones.

La estructura y algunas características pueden cambiar durante el desarrollo.

---

## 💙 Gracias

Gracias a todas las personas que utilizan, prueban, reportan errores o contribuyen a KimiXP.

El proyecto empezó como una idea y continúa creciendo gracias al desarrollo y a la comunidad.

---

<div align="center">

**KimiXP — Open Source Discord Bot**

Hecho con 💙 por [BrunoDevPe](https://github.com/WemphiraOrg)

</div>
