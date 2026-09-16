from __future__ import annotations
from typing import Iterable, Optional
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

from bitwig_agent.providers import PROVIDERS
from bitwig_agent.session import SessionManager

ROOT_COMMANDS = [
    ("/session", "Gestión de sesiones (list, save, load, new, delete)"),
    ("/resume", "Reanudar sesión previa por ID o búsqueda"),
    ("/provider", "Cambiar proveedor LLM (Google, Anthropic, etc.)"),
    ("/model", "Seleccionar modelo LLM activo"),
    ("/keys", "Configurar API Keys y variables de entorno"),
    ("/history", "Ver historial y acciones de la conversación"),
    ("/status", "Ver estado de Bitwig, transporte y LLM"),
    ("/clear", "Reiniciar historial de la sesión activa"),
    ("/help", "Mostrar ayuda de comandos y ejemplos"),
    ("/exit", "Guardar sesión y salir"),
    ("/quit", "Guardar sesión y salir"),
]

SESSION_SUBCOMMANDS = [
    ("list", "Listar sesiones guardadas en tabla"),
    ("save", "Guardar sesión actual con un título opcional"),
    ("load", "Cargar una sesión guardada por ID o nombre"),
    ("new", "Iniciar una nueva sesión en blanco"),
    ("delete", "Eliminar una sesión guardada"),
]

class BitwigCliCompleter(Completer):
    """
    Intelligent autocomplete completer for the Bitwig AI Agent CLI.
    Provides rich popup menu completions for root commands, subcommands,
    providers, and saved session IDs with descriptive metadata.
    """

    def __init__(self, session_manager: Optional[SessionManager] = None):
        self.session_manager = session_manager or SessionManager()

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor

        # Only trigger completion if line starts with slash (or leading whitespace then slash)
        stripped = text_before_cursor.lstrip()
        if not stripped.startswith("/"):
            return

        parts = stripped.split()
        is_trailing_space = text_before_cursor.endswith(" ")

        # 1. Completing the root command (e.g. "/" or "/ses" or "/pro")
        if len(parts) == 1 and not is_trailing_space:
            prefix = parts[0].lower()
            for cmd, desc in ROOT_COMMANDS:
                if cmd.lower().startswith(prefix):
                    yield Completion(
                        text=cmd,
                        start_position=-len(parts[0]),
                        display=cmd,
                        display_meta=desc,
                    )
            return

        root_cmd = parts[0].lower() if parts else ""

        # 2. Completing subcommands for /session
        if root_cmd == "/session":
            # Just typed "/session " or completing subcommand like "/session l"
            if len(parts) == 1 and is_trailing_space:
                for sub, desc in SESSION_SUBCOMMANDS:
                    yield Completion(
                        text=sub,
                        start_position=0,
                        display=sub,
                        display_meta=desc,
                    )
                return

            if len(parts) == 2 and not is_trailing_space:
                sub_prefix = parts[1].lower()
                for sub, desc in SESSION_SUBCOMMANDS:
                    if sub.lower().startswith(sub_prefix):
                        yield Completion(
                            text=sub,
                            start_position=-len(parts[1]),
                            display=sub,
                            display_meta=desc,
                        )
                return

            subcommand = parts[1].lower() if len(parts) > 1 else ""

            # 3. Dynamic session arguments for /session load and /session delete
            if subcommand in ("load", "delete"):
                arg_prefix = ""
                start_pos = 0
                if len(parts) == 2 and is_trailing_space:
                    arg_prefix = ""
                    start_pos = 0
                elif len(parts) == 3 and not is_trailing_space:
                    arg_prefix = parts[2].lower()
                    start_pos = -len(parts[2])
                else:
                    return

                sessions = self.session_manager.list_sessions()
                for s in sessions:
                    s_id = s.get("id", "")
                    s_title = s.get("title", "")
                    meta = f"{s.get('message_count', 0)} msgs • {s.get('updated_at', '')[:10]}"
                    # Match if prefix is in id or in title
                    if not arg_prefix or arg_prefix in s_id.lower() or arg_prefix in s_title.lower():
                        yield Completion(
                            text=s_id,
                            start_position=start_pos,
                            display=f"{s_id} ({s_title[:20]})",
                            display_meta=meta,
                        )
                return

        # 4. Dynamic session arguments for /resume
        if root_cmd == "/resume":
            arg_prefix = ""
            start_pos = 0
            if len(parts) == 1 and is_trailing_space:
                arg_prefix = ""
                start_pos = 0
            elif len(parts) == 2 and not is_trailing_space:
                arg_prefix = parts[1].lower()
                start_pos = -len(parts[1])
            else:
                return

            sessions = self.session_manager.list_sessions()
            for s in sessions:
                s_id = s.get("id", "")
                s_title = s.get("title", "")
                meta = f"{s.get('message_count', 0)} msgs • {s.get('updated_at', '')[:10]}"
                if not arg_prefix or arg_prefix in s_id.lower() or arg_prefix in s_title.lower():
                    yield Completion(
                        text=s_id,
                        start_position=start_pos,
                        display=f"{s_id} ({s_title[:20]})",
                        display_meta=meta,
                    )
            return

        # 5. Dynamic arguments for /provider
        if root_cmd == "/provider":
            prov_prefix = ""
            start_pos = 0
            if len(parts) == 1 and is_trailing_space:
                prov_prefix = ""
                start_pos = 0
            elif len(parts) == 2 and not is_trailing_space:
                prov_prefix = parts[1].lower()
                start_pos = -len(parts[1])
            else:
                return

            for p_tuple in PROVIDERS:
                p_id, p_name = p_tuple[0], p_tuple[1]
                if not prov_prefix or p_id.lower().startswith(prov_prefix):
                    yield Completion(
                        text=p_id,
                        start_position=start_pos,
                        display=p_id,
                        display_meta=p_name,
                    )
            return
