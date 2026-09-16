# Especificación de Diseño: Herramienta `write_notes`

**Fecha**: 2026-09-16  
**Componentes**: `bitwig_agent.llm.tools`, `bitwig_agent.mcp.server`, `bitwig_agent.llm.orchestrator`

## 1. Resumen
Se añade una nueva herramienta (`write_notes`) al agente y servidor MCP de Bitwig Studio, permitiendo componer y diseñar clips musicales nota por nota con control total sobre tono (número MIDI o nombre de nota tipo "C4"), posición temporal (por pasos de semicorchea o por beats decimales), duración, velocidad MIDI, canal y opciones de humanización y previsualización gráfica en piano roll ASCII.

## 2. Arquitectura y Componentes

### 2.1. Definición del Esquema (`BITWIG_TOOLS` en `bitwig_agent/llm/tools.py`)
Nombre: `write_notes`
Descripción: "Writes custom note sequences note-by-note into a clip slot in Bitwig Studio with precise control over pitch, timing, duration, and velocity."

**Parámetros principales**:
- `track` (`string` | `integer`, requerido): Índice o nombre de pista (ej. `'0'`, `'Lead'`, `'Synth'`, `'Drums'`).
- `slot` (`integer`, opcional, default: `0`): Índice del slot del clip launcher (0-indexed).
- `notes` (`array` de objetos, requerido): Lista de eventos de nota a escribir.
  - Cada objeto de nota contiene:
    - `pitch` (`integer` o `string`, requerido): Altura en número MIDI (`0-127`, ej: `60`) o nombre de nota con octava (ej: `"C4"`, `"F#3"`, `"Bb2"`, `"Db5"`).
    - `step` (`integer`, opcional): Paso en resolución de semicorcheas (`0` = compás 1.1, `4` = compás 1.2, `16` = compás 2.1).
    - `beat` (`number`, opcional): Posición temporal en beats decimales (`0.0`, `0.5`, `1.25`, etc.). Si no se provee `step`, se calcula automáticamente como `int(round(beat * 4.0))`.
    - `duration` (`number`, opcional, default: `1.0`): Duración en beats (ej. `0.25` = semicorchea, `0.5` = corchea, `1.0` = negra, `4.0` = redonda).
    - `velocity` (`integer`, opcional, default: `100`): Velocidad MIDI (`1-127`).
    - `channel` (`integer`, opcional, default: `0`): Canal MIDI (`0-15`).
- `beats` (`number`, opcional, default: `16`): Duración total del clip en beats. Si las notas exceden el valor indicado, el tamaño del clip se expande automáticamente al múltiplo de 4 beats más próximo.
- `clear` (`boolean`, opcional, default: `true`): Si es `true`, borra las notas preexistentes en el clip antes de escribir las nuevas.
- `launch` (`boolean`, opcional, default: `false`): Si es `true`, dispara la reproducción del clip inmediatamente tras escribirlo.
- `humanize` (`boolean`, opcional, default: `false`): Si es `true`, aplica micro-variaciones de velocidad y sutiles ajustes dinámicos usando `humanize_events`.

### 2.2. Ejecución (`ToolExecutor.execute` en `bitwig_agent/llm/tools.py`)
- Resolución del índice de pista mediante `self._resolve_track_index(...)`.
- Conversión y validación robusta de cada elemento de `notes`:
  - `pitch`: Soporta tanto enteros `0-127` como strings normalizados mediante `note_name_to_pitch(...)`.
  - `timing`: Resuelve `step` directamente o a partir de `beat` (`beat * 4`).
  - `duration`: Resuelve duración mínima y escala.
  - `velocity` y `channel` con validaciones de límites estándar MIDI.
- Instanciación de `NoteEvent`s.
- Aplicación opcional de `humanize_events(note_events)`.
- Envío al cliente Bitwig (`self.client.write_notes(...)`).
- Disparo opcional de reproducción (`self.client.launch_clip(...)`).
- Renderizado de Piano Roll ASCII enriquecido con `render_ascii_piano_roll(...)`.
- Retorno de respuesta estructurada con estado, metadatos y visualización ASCII.

### 2.3. Exposición en Servidor MCP (`bitwig_agent/mcp/server.py`)
- Función decorada con `@mcp_server.tool()`:
  ```python
  @mcp_server.tool()
  def write_notes(
      track: str,
      notes: List[Dict[str, Any]],
      slot: int = 0,
      beats: float = 16.0,
      clear: bool = True,
      launch: bool = False,
      humanize: bool = False
  ) -> str
  ```
- Esquema estático MCP registrado en `~/.gemini/antigravity/mcp/bitwig/write_notes.json`.

### 2.4. Actualización de System Prompt (`bitwig_agent/llm/orchestrator.py`)
- Inclusión de `write_notes` en la lista de herramientas disponibles y directrices musicales para creación de melodías, líneas de bajo custom, arpegios, y ritmos nota por nota.

## 3. Pruebas y Validación
- Pruebas unitarias en `python/tests/test_llm_tools.py`:
  - Verificación de presencia de `write_notes` en `BITWIG_TOOLS`.
  - Prueba de ejecución con pitches como strings (`"C4"`, `"E4"`, `"G4"`) y números (`60`, `64`, `67`).
  - Prueba de cálculo de posición a partir de `beat` vs `step`.
  - Prueba de opción `launch` y `humanize`.
  - Verificación de la inclusión del piano roll ASCII en la respuesta.
