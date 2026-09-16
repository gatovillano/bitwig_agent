# Especificación de Diseño: Menú de Autocompletado de Comandos

**Fecha**: 2026-09-15  
**Componente**: `bitwig_agent.completer` y `bitwig_agent.cli`

## 1. Resumen
Se implementa un sistema de autocompletado en tiempo real con menú emergente desplegable para la interfaz de línea de comandos (CLI) interactiva de Bitwig AI Agent, reemplazando la entrada estándar síncrona de Rich por una sesión enriquecida de `prompt_toolkit`.

## 2. Arquitectura y Componentes

### 2.1. Módulo `bitwig_agent/completer.py`
Clase `BitwigCliCompleter(Completer)` que implementa:
- Detección de comandos con prefijo `/`.
- Menú emergente de primer nivel:
  - `/session`: "Gestión interactiva y guardado de sesiones"
  - `/resume`: "Reanudar sesión previa por ID o búsqueda"
  - `/provider`: "Cambiar proveedor LLM (Google, Anthropic, etc.)"
  - `/model`: "Seleccionar modelo LLM activo"
  - `/keys`: "Configurar y gestionar API keys y entorno"
  - `/history`: "Ver historial formateado de la sesión"
  - `/status`: "Ver estado de Bitwig, transporte y LLM"
  - `/clear`: "Reiniciar memoria de conversación actual"
  - `/help`: "Mostrar ayuda de comandos y ejemplos"
  - `/exit` / `/quit`: "Guardar y salir de la aplicación"
- Subcomandos de segundo nivel:
  - Tras `/session `: sugiere `list`, `save`, `load`, `new`, `delete` con descripciones.
  - Tras `/provider `: sugiere los IDs de proveedores disponibles en `PROVIDERS`.
- Argumentos dinámicos de tercer nivel:
  - Tras `/session load ` o `/session delete ` o `/resume `: consulta en tiempo real a `SessionManager.list_sessions()` para ofrecer autocompletado de IDs y títulos de sesiones existentes, con metadatos mostrando número de mensajes y última fecha de edición.

### 2.2. Estilos Visuales (`PromptSession`)
- Estilo personalizado (`Style.from_dict`):
  - Menú desplegable flotante con contraste elegante (`completion-menu`, `completion-menu.completion`, `completion-menu.completion.current`, `completion-menu.meta`).
  - Scrollbar del menú estilizado.
- Historial persistente en disco en `~/.bitwig_agent/cli_history`.
- `complete_while_typing=True` para activar el menú emergente tan pronto el usuario escriba `/`.

### 2.3. Integración en `bitwig_agent/cli.py`
- Instanciar `PromptSession` con el completer y estilo configurados.
- Adaptar el prompt en el bucle interactivo usando `HTML(...)` de prompt_toolkit para mantener la estética idéntica (proveedor, modelo, sesión activa, prompt Bitwig).

## 3. Pruebas y Validación
- Pruebas unitarias en `tests/test_completer.py` verificando:
  - Completado de comandos raíz (`/`).
  - Completado de subcomandos (`/session `).
  - Completado dinámico de sesiones existentes.
  - Filtro por prefijo parcial (ej: `/se` sugiere `/session`).
