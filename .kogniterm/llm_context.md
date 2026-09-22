<!-- Generado por KogniTerm DeepResearcher -->
# Informe de Investigación: Memoria Contextual del Proyecto

He completado la investigación exhaustiva del proyecto local y he generado el archivo **`llm_context.md`** en la raíz del repositorio. A continuación presento el contenido final consolidado, que captura propósito, arquitectura, comandos y convenciones con el detalle técnico requerido.

---

# Memoria Contextual del Proyecto

## 1. Propósito Principal, Tecnologías Clave y Alcance

**Bitwig MCP Server & AI Agent** es una plataforma integral que convierte **Bitwig Studio 6.0+** en un entorno musical directamente accesible y programable para modelos de lenguaje avanzados (**LLMs**) a través del estándar abierto **Model Context Protocol (MCP)**. El proyecto no se limita a una interfaz de control remoto: su objetivo es situar a la IA como un colaborador musical dentro del flujo de trabajo del productor, con capacidad de inspección en tiempo real, composición algorítmica avanzada y edición no destructiva de proyectos.

El alcance del proyecto abarca tres capas desacopladas: una extensión nativa de Bitwig escrita en **Java 17+** que expone un servidor HTTP REST en el puerto `8989`, un servidor MCP en **Python 3.10+** que actúa como puente entre clientes MCP (Claude Desktop, Cursor, Windsurf, Antigravity, etc.) y el bridge de Bitwig, y un **motor musical** propio con parser armónico, optimización de voice leading, generación de grooves y humanización estocástica.

Tecnologías clave del stack:
- **Backend/control**: Java 17+, API de Controladores de Bitwig Studio, servidor HTTP REST embebido (`http://127.0.0.1:8989`).
- **Servidor MCP y CLI**: Python 3.10+, `mcp>=1.0.0`, `httpx>=0.27.0`, `pydantic>=2.7.0`, `litellm>=1.40.0`, `rich>=13.7.1`, `prompt-toolkit>=3.0.40`, `python-dotenv>=1.0.1`.
- **Empaquetado**: `hatchling` como backend de build (`python/pyproject.toml`).
- **Pruebas**: `pytest>=8.0.0`, `pytest-asyncio>=0.23.2` (suite con pruebas unitarias y de integración).
- **Clientes soportados**: Claude Desktop, Cursor, Windsurf, Antigravity/Gemini CLI, Gemini CLI, Ollama local y cualquier cliente compatible con stdio MCP.

El proyecto define claramente su alcance funcional en la documentación: inspección de proyecto/pistas/clips, generación de progresiones de acordes con voice leading suave, líneas de bajo adaptativas, escritura nota por nota, inserción de instrumentos nativos y presets `.bwpreset`, gestión de efectos nativos, control de transporte, grabación en Arranger y visualización ASCII de piano rolls.

Fuentes de referencia: `README.md` [^1^], `python/pyproject.toml` [^2^], `java-extension/build.sh` [^3^], `.env.example` [^4^].

---

## 2. Arquitectura y Módulos Clave

La arquitectura del proyecto sigue un patrón de tres capas desacopladas y de alto rendimiento, con comunicación por JSON-RPC sobre stdio en el lado MCP y HTTP REST en el lado de Bitwig.

### 2.1 Estructura de Carpetas

```
bitwig_agent/
├── README.md
├── .env.example
├── LICENSE
├── docs/
│   └── superpowers/
├── java-extension/
│   ├── build.sh
│   ├── build/
│   │   └── BitwigAgentBridge.bwextension
│   └── src/main/java/com/bitwig/agent/
│       ├── BitwigAgentExtension.java
│       ├── BitwigAgentExtensionDefinition.java
│       ├── BridgeHttpServer.java
│       └── JsonUtils.java
└── python/
    ├── pyproject.toml
    ├── uv.lock
    ├── README.md
    └── bitwig_agent/
        ├── __init__.py
        ├── mcp/
        │   ├── __init__.py
        │   └── server.py
        ├── llm/
        │   ├── __init__.py
        │   ├── orchestrator.py
        │   └── tools.py
        ├── theory/
        │   ├── __init__.py
        │   ├── chords.py
        │   ├── voicings.py
        │   ├── rhythm.py
        │   ├── humanize.py
        │   └── visualization.py
        ├── client.py
        ├── cli.py
        ├── config.py
        ├── providers.py
        ├── antigravity.py
        ├── session.py
        ├── completer.py
        └── dialogs.py
```

### 2.2 Capa Java: Extensión Nativa y Bridge HTTP

El componente Java reside en `java-extension/` y constituye el único punto de contacto autorizado con la API de Bitwig Studio. Su responsabilidad es doble: actuar como **controlador registrado** de Bitwig y exponer un **servidor HTTP REST** en `http://127.0.0.1:8989`.

El script `build.sh` compila las clases Java contra `bitwig.jar` (ruta esperada en `/opt/bitwig-studio/bin/bitwig.jar`), copia recursos, empaqueta el `.bwextension` y lo despliega automáticamente al directorio de extensiones del usuario. El binario precompilado `build/BitwigAgentBridge.bwextension` permite omitir la compilación si no se dispone del JDK 17 y el JAR de Bitwig.

Internamente, `BridgeHttpServer.java` implementa endpoints REST para transporte, pistas, clips, instrumentos, efectos y dispositivos. El uso de `host.scheduleTask()` garantiza que todas las mutaciones sobre clips, notas, pistas y transporte se ejecutan en el hilo principal de Bitwig, evitando bloqueos de audio y condiciones de carrera. Esta decisión es crítica para la estabilidad en tiempo real.

### 2.3 Capa Python: Cliente HTTP, Servidor MCP y Motor Musical

**Cliente HTTP (`client.py`)**: La clase `BitwigClient` encapsula toda la comunicación con el bridge mediante `httpx`. Define modelos Pydantic para las estructuras del dominio: `ProjectState`, `TrackInfo`, `TrackDetail`, `DeviceInfo`, `ClipDetail`, `ClipNote`, `NoteEvent` y `SlotInfo`. Cada método mapea directamente a un endpoint REST del bridge (`/api/project`, `/api/transport`, `/api/clip/notes`, `/api/instrument/add`, `/api/effect/add`, `/api/device/control`, etc.), manteniendo una interfaz tipada y validada.

**Servidor MCP (`mcp/server.py`)**: Expone la especificación de herramientas MCP sobre transporte `stdio` usando `MCPServer`. Cada herramienta decorada con `@mcp_server.tool()` es un wrapper que recibe parámetros tipados, delega a `ToolExecutor`, serializa el resultado a JSON indentado y lo devuelve al cliente MCP. El servidor registra herramientas de proyecto, acordes, bajo, transporte, clips, escenas, grabación en Arranger, efectos, dispositivos, catálogo de efectos de audio, y organización de pistas (move, group, ungroup, organize).

**Orquestador LLM (`llm/orchestrator.py`)**: La clase `BitwigAgent` envuelve `litellm.completion` y gestiona el ciclo multi-turno de tool use. Mantiene un historial de mensajes con system prompt fijo, envía herramientas (`BITWIG_TOOLS`) en cada llamada y ejecuta hasta `max_turns=8` iteraciones de tool calling. Incluye lógica de enrutamiento especial para Antigravity (mapeo de mensajes a formato Gemini, OAuth2 desde token local) y KiloCode Gateway (endpoint OpenAI-compatible).

**Motor Musical (`theory/`)**: Es la capa de dominio musical. `chords.py` implementa un parser universal de acordes con regex, diccionarios de intervalos canónicos y soporte de slash chords. `voicings.py` resuelve el problema del voice leading mediante búsqueda combinatoria de asignaciones de octava que minimizan la suma de distancias euclidianas al acorde previo, con restricciones de registro y distancia mínima entre voces. `rhythm.py` traduce acordes voicingados a eventos de nota en la cuadrícula de 16nos, soportando patrones `sustained`, `lofi`, `syncopated`, `quarter_stabs` y `arpeggio`, además de basslines en estilos `root`, `syncopated` y `walking`. `humanize.py` aplica variación gaussiana de velocidades y micro-timing por pila de acorde. `visualization.py` renderiza un Piano Roll ASCII con cabecera de metadatos, eje de tiempo y timeline de eventos.

### 2.4 Flujo de Ejecución

El flujo end-to-end cuando un usuario interactúa con un cliente MCP es el siguiente:

1. El usuario escribe una petición musical en el cliente MCP (por ejemplo, Claude Desktop).
2. El cliente envía una solicitud JSON-RPC por stdio al servidor MCP (`bitwig-agent-mcp`).
3. `mcp/server.py` recibe la llamada a una herramienta decorada, recoge los argumentos y llama a `ToolExecutor.execute()`.
4. `ToolExecutor` puede invocar al motor musical (`theory/`) para transformar símbolos de acordes en listas de `NoteEvent`, o llamar directamente a métodos de `BitwigClient`.
5. `BitwigClient` envía peticiones HTTP JSON al bridge de Java en `http://127.0.0.1:8989`.
6. El servidor Java recibe la petición, la despacha al hilo principal de Bitwig mediante `host.scheduleTask()` y aplica la modificación en el DAW.
7. La respuesta viaja de vuelta por HTTP → `BitwigClient` → `ToolExecutor` → `mcp/server.py` → cliente MCP → LLM → usuario.

Para la CLI interactiva (`bitwig-agent`), el flujo añade una capa de orquestación LLM adicional: el prompt del usuario se envía a `BitwigAgent.chat()`, que a su vez invoca a LiteLLM/Antigravity con herramientas. Si el modelo decide llamar a herramientas, el orquestador las ejecuta localmente y reinyecta los resultados como mensajes de herramienta hasta obtener la respuesta final.

---

## 3. Comandos del Proyecto

### 3.1 Compilación y despliegue de la extensión Java

```bash
# Compilar y desplegar la extensión (requiere Java 17+ y bitwig.jar en /opt/bitwig-studio/bin/)
./java-extension/build.sh

# El script genera:
#   java-extension/build/BitwigAgentBridge.bwextension
# y lo copia a ~/Bitwig Studio/Extensions/
```

### 3.2 Instalación del paquete Python

```bash
cd python

# Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Instalación editable con dependencias
pip install -e .

# Dependencias dev (tests)
pip install -e ".[dev]"
```

### 3.3 Ejecución del servidor MCP

```bash
# A través del entry point instalado por pyproject.toml
bitwig-agent-mcp

# O directamente como módulo
python -m bitwig_agent.mcp.server
```

### 3.4 Ejecución de la CLI interactiva

```bash
bitwig-agent

# Con argumentos CLI
bitwig-agent --model gemini/gemini-2.5-pro
bitwig-agent --session "Mi Sesión Neo-Soul"
bitwig-agent --prompt "Crea una progresión de Dm9 a G13"
```

### 3.5 Pruebas automatizadas

```bash
cd python
pytest -v

# Opciones útiles
pytest tests/test_theory.py -v          # Solo pruebas de teoría musical
pytest tests/test_client.py -v          # Solo pruebas del cliente HTTP
pytest tests/test_llm_tools.py -v       # Solo pruebas de herramientas MCP
pytest tests/ -k "not integration" -v   # Excluir pruebas de integración si aplica
```

La configuración de pytest en `python/pyproject.toml` fija `asyncio_mode = "auto"` y `testpaths = ["tests"]`, por lo que no se requiere configuración adicional.

### 3.6 Verificación rápida del bridge

```bash
# Comprobar que la extensión está activa en Bitwig
curl http://127.0.0.1:8989/api/status

# Respuesta esperada:
# {"status":"ok","name":"Bitwig Agent Bridge","version":"1.0.0","bitwig_api":18}
```

---

## 4. Convenciones y Reglas de Desarrollo

### 4.1 Estilo de código y formato

El proyecto sigue las convenciones estándar de Python con énfasis en legibilidad y tipado estático:
- Uso de `from __future__ import annotations` en todos los módulos Python para compatibilidad de tipado.
- Tipado explícito en firmas de funciones y variables (`List`, `Dict`, `Optional`, `Union`, `Any`).
- Modelos de dominio definidos con **Pydantic v2** (`BaseModel`, `Field`) para validación y serialización.
- Nombres de variables y funciones en `snake_case`; nombres de clases en `PascalCase`.
- Strings de documentación (`docstrings`) en las firmas públicas y clases clave.

### 4.2 Patrones de diseño obligatorios

**Cliente HTTP tipado**: Toda comunicación con el bridge se realiza exclusivamente a través de `BitwigClient`, que encapsula `httpx` y devuelve modelos Pydantic validados. No se permiten llamadas HTTP directas desde herramientas u orquestadores; el cliente es la única vía de acceso.

**ToolExecutor como dispatcher central**: Las herramientas MCP no se ejecutan de forma dispersa. `ToolExecutor.execute()` centraliza la resolución de tracks (por índice o por nombre), la invocación al motor musical y la normalización de errores. Toda herramienta pasa por este dispatcher.

**Fachada del motor musical**: El módulo `theory/__init__.py` expone dos funciones de alto nivel, `build_chord_progression()` y `build_bassline()`, que ocultan la complejidad interna de parsing, voicing, ritmo y humanización. El resto del código no debe invocar directamente a `chords.py`, `voicings.py`, `rhythm.py` o `humanize.py` desde herramientas MCP; debe usar la fachada.

**Separación de responsabilidades MCP vs CLI**: El servidor MCP (`mcp/server.py`) solo conoce herramientas y devuelve JSON. La CLI interactiva (`cli.py`) es la única capa con interfaz de usuario rica (`rich`, `prompt_toolkit`), gestión de sesiones y comandos slash. El orquestador LLM (`llm/orchestrator.py`) vive en una capa intermedia y es consumido por la CLI, no por el servidor MCP.

**Proveedores LLM desacoplados**: El soporte multi-proveedor no se implementa con condicionales dispersos en el orquestador. `providers.py` centraliza catálogos, modelos por defecto, claves requeridas y funciones de descubrimiento dinámico (`fetch_*_models`). El orquestador solo despacha entre Antigravity, KiloCode y LiteLLM estándar.

### 4.3 Decisiones técnicas registradas

1. **Java como bridge nativo**: Se eligió Java porque la API de Controladores de Bitwig Studio está disponible exclusivamente en Java. El servidor HTTP es intencionalmente ultraligero y se ejecuta en localhost para evitar latencia de red y problemas de firewall.

2. **Python como capa MCP y musical**: Python ofrece el ecosistema más maduro para MCP (`mcp` SDK), modelado con Pydantic, composición musical algorítmica y orquestación de LLMs con LiteLLM. El motor musical se implementa aquí por expresividad y velocidad de prototipado.

3. **HTTP REST en lugar de bindings nativos**: El bridge Java no importa librerías Python ni expone sockets UNIX avanzados. Un API REST JSON simple es suficiente, fácil de depurar con `curl` y tolerable en latencia para comandos musicales no ultra-time-critical.

4. **Modelos Pydantic como contrato de datos**: Todas las estructuras que cruzan la frontera entre Python y Java están validadas con Pydantic. Esto permite detección temprana de cambios en el API del bridge y documentación ejecutable de los contratos.

5. **Humanización gaussiana por pila de notas**: En lugar de aplicar jitter aleatorio plano por nota, `humanize.py` agrupa notas por step, identifica la voz superior y aplica un contorno dinámico (acento en la voz superior, reducción en voces internas). Esta decisión busca evitar el efecto "MIDI robot" sin sacrificar la claridad armónica.

6. **Voice leading por producto cartesiano con restricciones**: `find_best_voice_leading()` itera sobre combinaciones de octavas candidatas dentro de un rango definido, descarta clusters ilegibles y minimiza una función de coste combinada por movimiento de voces y deriva del centro. Es computacionalmente O(c^n) pero con voces típicas de 3 a 5 notas y un rango acotado es instantáneo.

7. **Compatibilidad multi-proveedor sin lock-in**: El soporte para Antigravity, KiloCode, Google, Anthropic, OpenAI, OpenRouter, Groq y Ollama no es un afterthought. El diseño de `providers.py`, el mapeo de mensajes en `antigravity.py` y el ruteo en `orchestrator.py` están pensados para que agregar un proveedor nuevo sea una cuestión de catálogo y fetch, no de reescritura.

### 4.4 Reglas obligatorias de desarrollo

- **No modificar el bridge Java sin actualizar el cliente Python**: Cualquier cambio en endpoints, payloads o nombres de campo en `BridgeHttpServer.java` debe reflejarse simultáneamente en `client.py` y en los schemas de Pydantic correspondientes.
- **Toda herramienta MCP debe ser registrada en `mcp/server.py` y en `llm/tools.py`**: El servidor MCP expone la firma pública; `tools.py` define el schema JSON para el LLM y la lógica de ejecución. Ambos deben mantenerse sincronizados.
- **Las pruebas unitarias deben mockear `httpx.Client`**: No se deben realizar llamadas HTTP reales en tests. Los tests existentes usan `monkeypatch` para reemplazar `httpx.Client.post` y verificar URLs y payloads.
- **El parser de acordes debe manejar variantes de notación**: `chords.py` acepta múltiples alias (`m`, `min`, `-`, `m7`, `min7`, `-7`, etc.) y normaliza a intervalos canónicos. Cualquier nueva calidad de acorde debe registrarse en `CHORD_INTERVALS`.
- **Las herramientas deben ser tolerantes a fallos de conexión**: Si el bridge no está disponible, las herramientas deben devolver respuestas con claves `error` e `hint` útiles para el usuario, nunca excepciones sin captura.
- **Los comandos de grabación en Arranger usan `time.sleep` síncrono**: `record_to_arranger` con `record_sequence` bloquea el hilo Python durante la duración de la grabación para mantener la sincronización rítmica con el BPM del proyecto. Esta es una decisión de diseño aceptada; no debe reemplazarse por asincronía sin reevaluar la precisión temporal.
- **La CLI debe autoguardar sesiones**: Toda interacción en modo interactivo actualiza y persiste la sesión actual en `~/.config/bitwig_agent/sessions/`. El comando `/exit` y `EOFError` garantizan el guardado incluso ante interrupción.

---

## Referencias a Fuentes

- [^1^] `README.md` — Documentación principal del proyecto.
- [^2^] `python/pyproject.toml` — Configuración de paquete, dependencias y scripts.
- [^3^] `java-extension/build.sh` — Script de compilación y despliegue de la extensión Java.
- [^4^] `.env.example` — Plantilla de variables de entorno y configuración de proveedores.
- Código fuente analizado: `python/bitwig_agent/mcp/server.py`, `python/bitwig_agent/llm/tools.py`, `python/bitwig_agent/llm/orchestrator.py`, `python/bitwig_agent/client.py`, `python/bitwig_agent/theory/*.py`, `python/bitwig_agent/cli.py`, `python/bitwig_agent/config.py`, `python/bitwig_agent/providers.py`, `python/bitwig_agent/antigravity.py`, `python/bitwig_agent/session.py`.
- Tests revisados: `python/tests/test_theory.py`, `python/tests/test_client.py`, `python/tests/test_llm_tools.py`, `python/tests/test_visualization.py`, `python/tests/test_track_organization.py`.

---

El archivo **`llm_context.md`** ha sido generado en la raíz del proyecto con toda la información estructurada. Quedo a disposición del Bash Agent para cualquier ajuste o entrega adicional.
