# Bitwig MCP Server & AI Agent 🎹🤖⚡

[![Bitwig Studio 6.0+](https://img.shields.io/badge/Bitwig_Studio-6.0%2B-orange?style=flat-square&logo=bitwig)](https://www.bitwig.com/)
[![MCP Server](https://img.shields.io/badge/MCP-Model_Context_Protocol-purple?style=flat-square)](https://modelcontextprotocol.io/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org/)
[![Java 17+](https://img.shields.io/badge/Java-17%2B-red?style=flat-square&logo=openjdk)](https://openjdk.org/)
[![Tests Passing](https://img.shields.io/badge/Tests-36%20Passing-brightgreen?style=flat-square)](https://github.com/gatovillano/bitwig_agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**Bitwig MCP Server & AI Agent** es una plataforma integral que convierte a **Bitwig Studio 6.0+** en un entorno musical directamente accesible y programable para modelos de lenguaje avanzados (**LLMs**) a través del estándar abierto **Model Context Protocol (MCP)**.

Permite a asistentes como **Claude Desktop**, **Cursor**, **Antigravity**, **Windsurf** o cualquier agente autónomo:
* Inspeccionar en tiempo real la sesión, pistas, instrumentos y plugins activos.
* Componer progresiones de acordes complejas con algoritmos de **Voice Leading suave**, voicings de teclado avanzados y grooves humanizados.
* Generar líneas de bajo adaptativas sincronizadas armónicamente.
* Escribir secuencias melódicas o rítmicas personalizadas nota por nota con control quirúrgico.
* Inspeccionar clips y visualizarlos mediante un **Piano Roll ASCII** en la respuesta de la IA.
* Insertar pistas de instrumentos nativos de Bitwig (*Polymer*, *Polysynth*, *FM-4*, *Sampler*, *Drum Machine*, etc.) o presets `.bwpreset`.
* Controlar el transporte de reproducción (play, stop, set tempo).

---

## 📑 Tabla de Contenidos

1. [¿Por qué un Servidor MCP para Bitwig?](#-por-qué-un-servidor-mcp-para-bitwig)
2. [Arquitectura del Sistema](#-arquitectura-del-sistema)
3. [Herramientas MCP Expuestas (Tools Reference)](#-herramientas-mcp-expuestas-tools-reference)
   - [1. `get_project_context`](#1-get_project_context)
   - [2. `create_chord_progression`](#2-create_chord_progression)
   - [3. `create_bassline`](#3-create_bassline)
   - [4. `write_notes`](#4-write_notes)
   - [5. `inspect_track`](#5-inspect_track)
   - [6. `inspect_clip`](#6-inspect_clip)
   - [7. `add_instrument_track`](#7-add_instrument_track)
   - [8. `control_transport`](#8-control_transport)
   - [9. `clear_clip`](#9-clear_clip)
4. [Configuración en Clientes MCP](#-configuración-en-clientes-mcp)
   - [Claude Desktop](#claude-desktop)
   - [Antigravity / Gemini CLI](#antigravity--gemini-cli)
   - [Cursor & Windsurf](#cursor--windsurf)
5. [Instalación y Puesta en Marcha](#-instalación-y-puesta-en-marcha)
   - [Paso 1: Instalar la Extensión en Bitwig Studio](#paso-1-instalar-la-extensión-en-bitwig-studio)
   - [Paso 2: Activar el Controlador en Bitwig](#paso-2-activar-el-controlador-en-bitwig)
   - [Paso 3: Instalar el Paquete Python](#paso-3-instalar-el-paquete-python)
6. [Motor de Teoría Musical](#-motor-de-teoría-musical)
7. [Modo Alternativo: CLI Interactivo (`bitwig-agent`)](#-modo-alternativo-cli-interactivo-bitwig-agent)
8. [Suite de Pruebas](#-suite-de-pruebas)
9. [Estructura del Proyecto](#-estructura-del-proyecto)
10. [Licencia](#-licencia)

---

## ⚡ ¿Por qué un Servidor MCP para Bitwig?

Hasta ahora, usar modelos de lenguaje para producir música requería copiar y pegar archivos MIDI o lidiar con fragmentos de código desconectados del DAW. 

Gracias a **MCP (Model Context Protocol)**, el modelo tiene acceso directo a Bitwig como una extensión de su pensamiento:

```
                          ┌─────────────────────────────┐
                          │   Cliente MCP (Claude,      │
                          │ Cursor, Antigravity, etc.)  │
                          └──────────────┬──────────────┘
                                         │ JSON-RPC (stdio)
                                         ▼
                          ┌─────────────────────────────┐
                          │    Servidor MCP en Python   │
                          │     (bitwig-agent-mcp)      │
                          └──────────────┬──────────────┘
                                         │ Motor Musical / HTTP
                                         ▼
                          ┌─────────────────────────────┐
                          │ Java Controller Extension   │
                          │   (BitwigAgentBridge :8989) │
                          └──────────────┬──────────────┘
                                         │ Bitwig API Thread-Safe
                                         ▼
                          ┌─────────────────────────────┐
                          │      BITWIG STUDIO 6.0+     │
                          │ Clips, Pistas, Piano Roll   │
                          └─────────────────────────────┘
```

* **Cero latencia de contexto**: La IA puede consultar qué pistas existen, si están sonando, qué instrumentos tienen cargados y qué notas hay escritas en cualquier clip slot.
* **Creatividad musical algorítmica**: En lugar de notas aleatorias, cuenta con un motor que comprende tensiones de acordes (9as, 11as, 13as, dominantes alterados), resuelve el movimiento de las voces mediante saltos mínimos (*Voice Leading*) y aplica dinámicas humanas.
* **Edición no destructiva**: Puede crear nuevos clips, sobreescribir, borrar o inspeccionar sin alterar el flujo de trabajo del productor.

---

## 🏗 Arquitectura del Sistema

El ecosistema se compone de tres capas desacopladas y de alto rendimiento:

1. **Extensión Java (`BitwigAgentBridge.bwextension`)**:
   - Implementa la API de Controladores de Bitwig Studio 6.0 (`com.bitwig.extension.controller.ControllerExtension`).
   - Aloja un servidor HTTP REST ultraligero y seguro en `http://127.0.0.1:8989`.
   - Utiliza `host.scheduleTask()` para garantizar que todas las modificaciones sobre clips, notas, pistas y transporte ocurran en el hilo de ejecución principal de Bitwig sin bloqueos de audio.

2. **Servidor MCP Python (`bitwig-agent-mcp`)**:
   - Expone la especificación de herramientas MCP sobre transporte estándar `stdio`.
   - Conecta el protocolo MCP con el motor de teoría musical y el cliente HTTP de Bitwig.

3. **Motor Musical (`bitwig_agent.theory`)**:
   - Parser armónico universal (soporta nomenclatura estándar de jazz y música moderna).
   - Optimizador de Voice Leading basado en distancia euclidiana de semitonos entre acordes sucesivos.
   - Generador de groove rítmico (estilos `sustained`, `lofi`, `syncopated`, `quarter_stabs`, `arpeggio`).
   - Humanizador con fluctuación estocástica de micro-timing y velocidades de pulsación realistas.

---

## 🛠 Herramientas MCP Expuestas (Tools Reference)

A continuación se detallan todas las herramientas disponibles a través del servidor MCP:

### 1. `get_project_context`
Inspecciona el estado global del proyecto en Bitwig Studio.
* **Argumentos**: Ninguno.
* **Retorna**: JSON con tempo en BPM, estado de reproducción (`isPlaying`) y lista completa de pistas (índice, nombre, mute, solo, arm y slots con clips existentes).
* **Ejemplo de respuesta**:
  ```json
  {
    "tempo": 120.0,
    "isPlaying": false,
    "tracks": [
      {
        "index": 0,
        "name": "Rhodes Piano",
        "arm": false,
        "mute": false,
        "solo": false,
        "occupied_slots": [0, 1]
      },
      {
        "index": 1,
        "name": "Sub Bass",
        "arm": false,
        "mute": false,
        "solo": false,
        "occupied_slots": [0]
      }
    ]
  }
  ```

---

### 2. `create_chord_progression`
Genera y escribe una progresión de acordes armónicamente optimizada en un clip de la pista indicada.
* **Argumentos**:
  | Parámetro | Tipo | Por Defecto | Descripción |
  |-----------|------|-------------|-------------|
  | `track` | `string` | *(Requerido)* | Índice (ej. `"0"`) o nombre de la pista (ej. `"Keys"`, `"Rhodes"`). |
  | `chords` | `List[string]` | *(Requerido)* | Lista de acordes, ej: `["Dm9", "G13", "Cmaj9", "A7alt"]`. |
  | `slot` | `integer` | `0` | Índice del slot en el Clip Launcher. |
  | `beats_per_chord` | `number` | `4.0` | Duración en pulsos (4.0 = 1 compás en 4/4). |
  | `voicing_style` | `string` | `"keyboard"` | Estilo de distribución de voces: `"keyboard"`, `"rootless"` (voicings jazz sin tónica) o `"drop2"`. |
  | `rhythm_pattern` | `string` | `"sustained"` | Patrón rítmico: `"sustained"`, `"lofi"`, `"syncopated"`, `"quarter_stabs"`, `"arpeggio"`. |
  | `include_bass` | `boolean` | `true` | Si se debe incluir la nota tónica grave en el acorde. |
  | `humanize` | `boolean` | `true` | Aplica variaciones orgánicas de velocidad y micro-timing. |
  | `launch` | `boolean` | `false` | Inicia la reproducción del clip inmediatamente tras crearlo. |

* **Ejemplo de prompt para el LLM**:
  > *"Crea una progresión Neo-Soul en la pista 'Rhodes': Dm9 -> G13 -> Cmaj9 -> A7b9#11 con patrón rítmico lofi y voicings rootless, y ponla en reproducción."*

---

### 3. `create_bassline`
Crea una línea de bajo dedicada que sigue armónicamente una progresión de acordes.
* **Argumentos**:
  | Parámetro | Tipo | Por Defecto | Descripción |
  |-----------|------|-------------|-------------|
  | `track` | `string` | *(Requerido)* | Índice o nombre de la pista de bajo (ej. `"Bass"`, `"1"`). |
  | `chords` | `List[string]` | *(Requerido)* | Símbolos de acordes que el bajo debe acompañar. |
  | `slot` | `integer` | `0` | Índice del slot del clip. |
  | `beats_per_chord` | `number` | `4.0` | Duración por acorde. |
  | `style` | `string` | `"syncopated"` | Estilo rítmico: `"root"` (tónica simple), `"syncopated"` (síncopa groove), `"walking"` (walking bass). |
  | `launch` | `boolean` | `false` | Dispara el clip al terminar de escribirlo. |

---

### 4. `write_notes`
Permite escribir secuencias de notas arbitrarias nota por nota con control absoluto de tono, posición temporal, duración y velocidad.
* **Argumentos**:
  | Parámetro | Tipo | Por Defecto | Descripción |
  |-----------|------|-------------|-------------|
  | `track` | `string` | *(Requerido)* | Índice o nombre de la pista. |
  | `notes` | `List[object]` | *(Requerido)* | Lista de eventos de nota a escribir. |
  | `slot` | `integer` | `0` | Índice del slot del clip. |
  | `beats` | `number` | `16.0` | Longitud total del clip en pulsos (auto-extensible si las notas lo superan). |
  | `clear` | `boolean` | `true` | Si limpia el clip antes de insertar las notas. |
  | `launch` | `boolean` | `false` | Inicia la reproducción inmediata. |
  | `humanize` | `boolean` | `false` | Aplica humanización sutil a las notas escritas. |

* **Estructura de cada nota en `notes`**:
  - `pitch`: Número MIDI (`0-127`) o nombre con octava (`"C4"`, `"F#3"`, `"Bb2"`, `"Db5"`).
  - `step`: Posición en semicorcheas (0 = pulso 1, 4 = pulso 2, etc.) **o** `beat` (número flotante: `0.0`, `1.5`, `2.25`).
  - `duration`: Duración en pulsos (`1.0` = negra, `0.25` = semicorchea, `0.5` = corchea).
  - `velocity`: Velocidad MIDI de `1` a `127` (por defecto `100`).
  - `channel`: Canal MIDI de `0` a `15` (por defecto `0`).

---

### 5. `inspect_track`
Permite al modelo "ver" la configuración completa de una pista.
* **Argumentos**: `track` (`string`, requerido): Índice o nombre de la pista.
* **Información que devuelve**:
  - Parámetros de mezcla: Volumen, panorama, mute, solo, arm.
  - Cadena completa de dispositivos: Sintetizadores (*Polymer*, *Polysynth*), instrumentos externos, plugins VST/CLAP, efectos de audio y presets activos.
  - Lista de clips presentes en la pista.

---

### 6. `inspect_clip`
Inspecciona el contenido interno de un clip y genera una representación visual gráfica en ASCII del Piano Roll.
* **Argumentos**: `track` (`string`), `slot` (`integer`, default `0`).
* **Visualización en Piano Roll ASCII**:
  ```text
    G4  | · · · · · · · · [═══════] · · · · · · · · |
    E4  | · · · · · · · · [═══════] · · · · · · · · |
    C4  | [═══════] · · · · · · · · · · · · · · · · |
    A3  | [═══════] · · · · · · · · · · · · · · · · |
        +---+---+---+---+---+---+---+---+---+---+---+
  Beat:   1       2       3       4       5       6
  ```

---

### 7. `add_instrument_track`
Inserta una nueva pista de instrumento o añade un instrumento a una pista existente.
* **Argumentos**:
  | Parámetro | Tipo | Por Defecto | Descripción |
  |-----------|------|-------------|-------------|
  | `name` | `string` | *(Requerido)* | Nombre de la pista (ej. `"Lead Synth"`, `"Drum Rack"`). |
  | `instrument` | `string` | `"polymer"` | Instrumento: `"polymer"`, `"polysynth"`, `"fm-4"`, `"phase-4"`, `"sampler"`, `"drum_machine"`, `"organ"`, `"poly_grid"`, `"instrument_layer"` o ruta a un archivo `.bwpreset`. |
  | `position` | `integer` | `-1` | Posición de inserción (`-1` para el final). |
  | `track` | `string` | `null` | Si se especifica, carga el instrumento en una pista existente en lugar de crear una nueva. |

---

### 8. `control_transport`
Controla el motor de reproducción y el tempo de Bitwig Studio.
* **Argumentos**:
  - `action`: `"play"`, `"stop"`, `"restart"` o `"set_tempo"`.
  - `tempo`: Valor en BPM (ej. `85.0`, `124.0`).

---

### 9. `clear_clip`
Limpia el contenido de un clip slot.
* **Argumentos**:
  - `track`: Índice o nombre de la pista.
  - `slot`: Índice del clip slot (default `0`).
  - `action`: `"notes"` (vacía las notas manteniendo el clip) o `"delete"` (elimina el clip por completo).

---

## 🔌 Configuración en Clientes MCP

### Claude Desktop

Edita tu archivo de configuración de Claude Desktop:
* **Linux**: `~/.config/Claude/claude_desktop_config.json`
* **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Añade el servidor `bitwig`:

```json
{
  "mcpServers": {
    "bitwig": {
      "command": "/ruta/al/proyecto/bitwig_agent/python/.venv/bin/bitwig-agent-mcp"
    }
  }
}
```

> 💡 **Nota**: Sustituye `/ruta/al/proyecto` por la ruta absoluta a tu clon del repositorio.

---

### Antigravity / Gemini CLI

Si utilizas Antigravity, el servidor se puede configurar mediante la carpeta de schemas MCP en `~/.gemini/antigravity/mcp/bitwig/` o agregando la definición en tus variables de configuración:

```json
{
  "mcpServers": {
    "bitwig": {
      "command": "python",
      "args": ["-m", "bitwig_agent.mcp.server"],
      "cwd": "/ruta/al/proyecto/bitwig_agent/python"
    }
  }
}
```

---

### Cursor & Windsurf

En Cursor (en `.cursor/mcp.json` o en `Settings -> Features -> MCP`):

```json
{
  "mcpServers": {
    "bitwig": {
      "command": "/ruta/al/proyecto/bitwig_agent/python/.venv/bin/bitwig-agent-mcp"
    }
  }
}
```

Una vez guardado, reinicia el cliente o recarga los servidores MCP. Verás disponibles las 8 herramientas nativas de Bitwig con el prefijo o símbolo correspondiente.

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
* **Bitwig Studio 6.0 o superior** (Linux, macOS o Windows).
* **Java 17 o superior** (OpenJDK 17 recomendada para compilar la extensión).
* **Python 3.10 o superior**.

---

### Paso 1: Instalar la Extensión en Bitwig Studio

El repositorio incluye el binario precompilado listo para usar en:
`java-extension/build/BitwigAgentBridge.bwextension`

Copia el archivo a tu carpeta de extensiones de Bitwig:
* **Linux**: `~/Bitwig Studio/Extensions/`
* **macOS**: `~/Documents/Bitwig Studio/Extensions/`
* **Windows**: `%USERPROFILE%\Documents\Bitwig Studio\Extensions\`

En Linux puedes copiarlo directamente ejecutando:
```bash
mkdir -p "$HOME/Bitwig Studio/Extensions"
cp java-extension/build/BitwigAgentBridge.bwextension "$HOME/Bitwig Studio/Extensions/"
```

*(Opcional) Si deseas recompilar la extensión Java desde el código fuente:*
```bash
./java-extension/build.sh
```

---

### Paso 2: Activar el Controlador en Bitwig

1. Abre **Bitwig Studio**.
2. Abre la configuración con `Ctrl + ,` (o `Cmd + ,` en macOS).
3. Selecciona la pestaña **Controllers**.
4. Haz clic en **Add controller**.
5. En la lista de fabricantes busca **BitwigAgent** y selecciona **Bitwig Agent Bridge**.
6. Verás aparecer una notificación en Bitwig:
   > *"Bitwig Agent Bridge Active (port 8989)"*

Verifica la conexión ejecutando en tu terminal:
```bash
curl http://127.0.0.1:8989/api/status
```
Debe devolver:
```json
{"status":"ok","name":"Bitwig Agent Bridge","version":"1.0.0","bitwig_api":18}
```

---

### Paso 3: Instalar el Paquete Python

1. Clona el repositorio e ingresa al subdirectorio `python`:
   ```bash
   git clone https://github.com/gatovillano/bitwig_agent.git
   cd bitwig_agent/python
   ```

2. Crea y activa un entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instala el proyecto en modo editable con dependencias:
   ```bash
   pip install -e .
   ```

¡Listo! Los comandos `bitwig-agent` y `bitwig-agent-mcp` quedarán instalados en tu entorno virtual.

---

## 🎼 Motor de Teoría Musical

El núcleo de teoría musical en `bitwig_agent.theory` resuelve uno de los problemas más difíciles en la composición asistida por IA: **que los acordes suenen musicales y naturales**.

### Características Destacadas:
1. **Sintaxis Armónica Flexible**:
   - Acordes mayores, menores, aumentados, disminuidos (`C`, `Am`, `Caug`, `Bdim`).
   - Extensiones y tensiones: 7mas, 9nas, 11nas, 13vas (`Dm9`, `F#m11`, `G13`, `Cmaj9`).
   - Acordes suspendidos (`Dsus4`, `Gsus2`).
   - Dominantes alterados: `G7alt`, `A7b9#11`, `E7#9`, `C7b13`.
   - Slash Chords: `F/G`, `Db/C`, `Ebmaj7/Bb`.

2. **Voice Leading Suave**:
   - Algoritmo que calcula la distancia de semitonos entre todas las inversiones posibles del siguiente acorde y elige aquella que minimiza el salto interválico de las voces intermedias.

3. **Estilos de Voicing**:
   - `keyboard`: Distribución abierta balanceada a 4-5 voces para teclado.
   - `rootless`: Voicings de jazz moderno (Bill Evans / Wynton Kelly) donde la tónica se omite para ser interpretada por el bajo, liberando espacio armónico para 3ra, 7ma, 9na y 11na/13va.
   - `drop2`: Voicings Drop-2 donde la segunda voz más aguda desciende una octava, ideal para secciones de viento o pads amplios.

4. **Grooves y Humanización**:
   - Estilos rítmicos integrados: acordes sostenidos (`sustained`), groove sincopado (`syncopated`), síncopa relajada (`lofi`), golpes a negras (`quarter_stabs`) y arpegios fluidos (`arpeggio`).
   - Humanización con variación gaussiana de velocidades y micro-timing de pulsación para evitar la sensación robótica o mecánica.

---

## 💻 Modo Alternativo: CLI Interactivo (`bitwig-agent`)

Además del servidor MCP, el paquete incluye una potente interfaz de línea de comandos (**CLI**) con autocompletado y menús interactivos impulsada por **LiteLLM**:

```bash
./python/.venv/bin/bitwig-agent
```

### Características de la CLI:
* **Compatibilidad Multi-Proveedor**:
  - **Google Gemini** (`gemini-2.5-flash`, `gemini-2.5-pro`).
  - **Anthropic Claude** (`claude-3-7-sonnet`, `claude-3-5-haiku`).
  - **OpenAI** (`gpt-4o`, `gpt-4o-mini`, `o3-mini`).
  - **Groq** (`llama-3.3-70b-versatile`, `mixtral-8x7b-32768`).
  - **Ollama local** (modelos locales sin coste de API).
  - **Antigravity OAuth2** (integración nativa con cuentas de Google Antigravity).
* **Menús interactivos**:
  - `/provider`: Cambia de proveedor de IA al vuelo.
  - `/model`: Selector de modelos compatibles.
  - `/keys`: Gestión segura de claves API almacenadas localmente.
  - `/session` & `/resume`: Historial de conversaciones y sesiones persistentes.
  - `/status`: Diagnóstico del estado del bridge de Bitwig y del modelo activo.

---

## 🧪 Suite de Pruebas

El proyecto cuenta con una batería de **36 pruebas unitarias y de integración** que validan la robustez del sistema:

```bash
cd python
pytest -v
```

### Qué se evalúa:
* **`test_theory.py`**: Parsing de acordes complejos, inversiones, Voice Leading y cálculo de notas.
* **`test_client.py`**: Modelos Pydantic, serialización de `NoteEvent` y conector HTTP REST.
* **`test_llm_tools.py`**: Ejecución de las herramientas MCP y validación de parámetros de entrada.
* **`test_visualization.py`**: Generador de Piano Roll ASCII y representación de clips.
* **`test_completer.py` & `test_session.py`**: Menús interactivos y persistencia de sesiones.

---

## 📁 Estructura del Proyecto

```
bitwig_agent/
├── README.md                      # Documentación principal con énfasis en MCP
├── .gitignore                     # Configuración de exclusiones de git
├── .env.example                   # Plantilla de variables de entorno y API keys
├── java-extension/                # Extensión nativa de Bitwig Studio
│   ├── build.sh                   # Script de compilación bash
│   ├── build/
│   │   └── BitwigAgentBridge.bwextension  # Binario precompilado de la extensión
│   └── src/main/java/com/bitwig/agent/
│       ├── BitwigAgentExtension.java      # Controlador de Bitwig
│       ├── BridgeHttpServer.java          # Servidor REST HTTP embebido (:8989)
│       └── JsonUtils.java                 # Serializador JSON ligero
└── python/                        # Servidor MCP, CLI y Motor Musical
    ├── pyproject.toml             # Configuración del paquete y dependencias
    ├── bitwig_agent/
    │   ├── mcp/
    │   │   └── server.py          # Servidor MCP stdio (bitwig-agent-mcp)
    │   ├── llm/
    │   │   ├── agent.py           # Orquestador con LiteLLM
    │   │   └── tools.py           # Definición y ejecución de herramientas
    │   ├── theory/                # Motor de teoría musical y voice leading
    │   ├── client.py              # Cliente HTTP REST tipado con Pydantic
    │   ├── cli.py                 # Interfaz interactiva de terminal
    │   └── config.py              # Configuración y gestión de credenciales
    └── tests/                     # Suite completa de tests automatizados (pytest)
```

---

## 📄 Licencia

Distribuido bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.

---

<div align="center">
  Hecho con ❤️ para la comunidad de productores y músicos de Bitwig Studio.
</div>
