from __future__ import annotations
import os
from typing import Optional, List, Tuple
from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog, message_dialog
from prompt_toolkit.formatted_text import HTML

from bitwig_agent.config import (
    load_config,
    save_config,
    get_active_provider,
    set_active_provider,
    get_active_model,
    set_active_model,
    save_env_var,
    remove_env_var,
    mask_secret,
    get_env_file_path,
)
from bitwig_agent.providers import (
    PROVIDERS,
    PROVIDER_DEFAULT_MODELS,
    ALL_COMMON_KEYS,
    fetch_models_for_provider,
)

def select_provider_dialog() -> Optional[str]:
    """
    Shows interactive dialog to choose LLM provider.
    Returns the provider key (e.g. 'google', 'anthropic') or None if cancelled.
    """
    current = get_active_provider()
    values = [(p[0], f"{p[1]}") for p in PROVIDERS]
    
    res = radiolist_dialog(
        title="🌐 Seleccionar Proveedor LLM",
        text="Elige el proveedor que deseas utilizar con Bitwig Agent:\n(Se consultará su catálogo de modelos dinámicamente)",
        values=values,
        default=current,
    ).run()

    return res

def select_model_dialog(provider: Optional[str] = None, current_model: Optional[str] = None) -> Optional[str]:
    """
    Fetches models for the given provider and displays selection dialog.
    Allows choosing a model or typing a custom one.
    """
    prov = provider or get_active_provider()
    curr = current_model or get_active_model()
    
    models = fetch_models_for_provider(prov)
    
    values: List[Tuple[str, str]] = []
    # Add fetched / fallback models
    for m_id, label in models:
        values.append((m_id, label))
        
    # Add custom model option
    values.append(("__custom__", "✏️  Introducir otro modelo manualmente..."))

    # Determine default selection
    default_val = curr if any(v[0] == curr for v in values) else (values[0][0] if values else None)

    res = radiolist_dialog(
        title=f"🤖 Modelos disponibles ({prov.upper()})",
        text=f"Selecciona el modelo a utilizar:\n(Modelo activo actual: {curr})",
        values=values,
        default=default_val,
    ).run()

    if res == "__custom__":
        custom = input_dialog(
            title="Modelo Personalizado",
            text=f"Introduce el identificador del modelo para LiteLLM\n(Ej: {prov}/mi-modelo o claude-3-7-sonnet):",
            default=curr or "",
        ).run()
        if custom and custom.strip():
            return custom.strip()
        return None

    return res

def manage_keys_dialog() -> None:
    """
    Interactive management dialog for API keys and environment variables.
    Saves directly to .env and active runtime environment.
    """
    dotenv_path = get_env_file_path()

    while True:
        # Read keys from .env
        env_keys: List[str] = []
        if os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k = line.split("=")[0].strip()
                            if k:
                                env_keys.append(k)
            except Exception:
                pass

        all_keys = sorted(list(set(ALL_COMMON_KEYS + env_keys)))

        options = []
        for k in all_keys:
            val = os.getenv(k, "")
            if val:
                masked = mask_secret(val)
                status = f'<style fg="ansigreen">✅ {masked}</style>'
            else:
                status = '<style fg="ansibrightblack">❌ No configurada</style>'

            options.append((k, HTML(f"<b>{k:<22}</b> │ {status}")))

        options.append(("__custom__", HTML("<b>➕ Añadir otra variable...</b>")))
        options.append(("__back__", HTML("<b>⬅️  Volver al chat</b>")))

        selected_key = radiolist_dialog(
            title="🔑 Gestión de API Keys y Variables",
            text=f"Archivo: {os.path.basename(dotenv_path)}\nSelecciona una variable para configurar, ver o eliminar:",
            values=options,
        ).run()

        if not selected_key or selected_key == "__back__":
            break

        if selected_key == "__custom__":
            custom_name = input_dialog(
                title="Nueva Variable de Entorno",
                text="Introduce el nombre de la variable (ej: GROQ_API_KEY, OLLAMA_API_BASE):",
            ).run()
            if custom_name and custom_name.strip():
                selected_key = custom_name.strip().upper()
            else:
                continue

        # Show actions for the selected key
        curr_val = os.getenv(selected_key, "")
        curr_masked = mask_secret(curr_val) if curr_val else "No configurada"

        action = radiolist_dialog(
            title=f"Acción para {selected_key}",
            text=f"Variable: {selected_key}\nEstado actual: {curr_masked}",
            values=[
                ("SET", "✏️  Configurar / Cambiar valor"),
                ("DELETE", "🗑️  Eliminar variable"),
                ("CANCEL", "🚫 Cancelar"),
            ],
            default="SET",
        ).run()

        if action == "SET":
            is_password = not ("URL" in selected_key or "BASE" in selected_key or "MODEL" in selected_key)
            new_val = input_dialog(
                title=f"Configurar {selected_key}",
                text=f"Introduce el valor para {selected_key}:",
                password=is_password,
            ).run()

            if new_val is not None:
                new_val = new_val.strip()
                save_env_var(selected_key, new_val)
                message_dialog(
                    title="✅ Guardado",
                    text=f"La variable {selected_key} ha sido actualizada exitosamente.",
                ).run()

        elif action == "DELETE":
            remove_env_var(selected_key)
            message_dialog(
                title="🗑️ Eliminado",
                text=f"La variable {selected_key} ha sido eliminada.",
            ).run()

def select_session_dialog(title: str = "📂 Reanudar Sesión", text: str = "Selecciona una sesión guardada:") -> Optional[str]:
    """
    Shows radiolist dialog with all saved sessions.
    Returns the selected session_id or None.
    """
    from bitwig_agent.session import SessionManager
    sm = SessionManager()
    sessions = sm.list_sessions()
    if not sessions:
        message_dialog(
            title="📂 Sin Sesiones Guardadas",
            text="No hay sesiones guardadas todavía.\nPuedes guardar la sesión actual con /session save [nombre].",
        ).run()
        return None

    values = []
    for s in sessions:
        date_str = s.get("updated_at", "")[:16].replace("T", " ")
        prov = s.get("provider", "").upper()
        msgs = s.get("message_count", 0)
        label = f"{s.get('title', s['id'])} [{prov}] — {date_str} ({msgs} msgs)"
        values.append((s["id"], label))

    selected = radiolist_dialog(
        title=title,
        text=text,
        values=values,
        default=values[0][0] if values else None,
    ).run()

    return selected

def session_menu_dialog() -> Optional[str]:
    """
    Interactive menu for session management.
    """
    options = [
        ("RESUME", "📂 Reanudar / Cargar sesión guardada"),
        ("SAVE", "💾 Guardar sesión actual con nombre"),
        ("NEW", "✨ Iniciar nueva sesión en blanco"),
        ("HISTORY", "📜 Ver historial de la sesión actual"),
        ("DELETE", "🗑️  Eliminar una sesión guardada"),
        ("BACK", "⬅️  Volver al chat"),
    ]
    return radiolist_dialog(
        title="🧵 Gestión de Sesiones e Historia",
        text="Selecciona una acción para administrar tus sesiones de Bitwig AI:",
        values=options,
        default="RESUME",
    ).run()

def save_session_name_dialog(default_name: str = "") -> Optional[str]:
    """
    Prompt to enter a title / name for the session.
    """
    return input_dialog(
        title="💾 Guardar Sesión",
        text="Introduce un título o nombre para identificar esta sesión:",
        default=default_name,
    ).run()

def delete_session_dialog() -> Optional[str]:
    """
    Selector to choose a session to delete.
    """
    from bitwig_agent.session import SessionManager
    sm = SessionManager()
    sessions = sm.list_sessions()
    if not sessions:
        message_dialog(
            title="🗑️ Sin Sesiones",
            text="No hay sesiones guardadas para eliminar.",
        ).run()
        return None

    values = []
    for s in sessions:
        date_str = s.get("updated_at", "")[:16].replace("T", " ")
        label = f"{s.get('title', s['id'])} — {date_str}"
        values.append((s["id"], label))

    return radiolist_dialog(
        title="🗑️ Eliminar Sesión",
        text="Selecciona la sesión que deseas eliminar permanentemente:",
        values=values,
    ).run()
