from __future__ import annotations
import os
import sys
import argparse
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from dotenv import load_dotenv

from bitwig_agent.client import BitwigClient
from bitwig_agent.llm import BitwigAgent
from bitwig_agent.config import (
    get_active_provider,
    set_active_provider,
    get_active_model,
    set_active_model,
    mask_secret,
)
from bitwig_agent.providers import (
    PROVIDERS,
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_KEYS,
    ALL_COMMON_KEYS,
)
from bitwig_agent.dialogs import (
    select_provider_dialog,
    select_model_dialog,
    manage_keys_dialog,
    select_session_dialog,
    session_menu_dialog,
    save_session_name_dialog,
    delete_session_dialog,
)
from bitwig_agent.antigravity import AntigravityClient
from bitwig_agent.session import SessionManager, Session
from bitwig_agent.completer import BitwigCliCompleter

import html
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.history import FileHistory

load_dotenv()

console = Console()
session_manager = SessionManager()

cli_style = Style.from_dict({
    "completion-menu.completion": "bg:#24283b #c0caf5",
    "completion-menu.completion.current": "bg:#3d59a1 #00ffff bold",
    "completion-menu.meta.completion": "bg:#1a1b26 #7aa2f7",
    "completion-menu.meta.completion.current": "bg:#283457 #ffffff bold",
    "scrollbar.background": "bg:#16161e",
    "scrollbar.button": "bg:#414868",
    "provider": "#00d7ff bold",
    "model": "#00ff87 bold",
    "session": "#888888 italic",
    "arrow": "#ff00af bold",
})

def print_banner(client: BitwigClient, provider: str, model: str, session: Session):
    connected = client.is_connected()
    conn_status = "[bold green]● Conectado (127.0.0.1:8989)[/bold green]" if connected else "[bold yellow]○ Bridge no detectado (:8989)[/bold yellow]"

    console.print(Panel.fit(
        f"[bold cyan]Bitwig AI Agent[/bold cyan] (Control Musical Inteligente)\n"
        f"Proveedor: [magenta]{provider.upper()}[/magenta]  │  Modelo: [green]{model}[/green]\n"
        f"Sesión: [cyan]'{session.title}'[/cyan] [dim]({session.id})[/dim]  │  Mensajes: [yellow]{session.message_count}[/yellow]\n"
        f"Bitwig Bridge: {conn_status}\n\n"
        f"[dim]Comandos: [bold]/provider[/bold] │ [bold]/model[/bold] │ [bold]/session[/bold] │ [bold]/resume[/bold] │ [bold]/history[/bold] │ [bold]/keys[/bold] │ [bold]/status[/bold] │ [bold]/help[/bold][/dim]",
        title="🎹 Bitwig AI Studio",
        border_style="cyan"
    ))

def show_status(client: BitwigClient, provider: str, model: str, session: Optional[Session] = None):
    table = Table(title="📊 Estado del Sistema", border_style="cyan")
    table.add_column("Componente", style="bold cyan")
    table.add_column("Estado / Valor", style="white")

    table.add_row("Proveedor Activo", f"[magenta]{provider.upper()}[/magenta]")
    table.add_row("Modelo Activo", f"[green]{model}[/green]")

    if session:
        table.add_row("Sesión Activa", f"[cyan]{session.title}[/cyan] [dim]({session.id})[/dim]")
        table.add_row("Historial", f"{session.message_count} mensajes en memoria")

    # Keys status
    if provider == "antigravity":
        if AntigravityClient.is_logged_in():
            k_status = "[green]✅ Sesión OAuth2 Activa (~/.gemini/antigravity-cli)[/green]"
        else:
            k_status = "[red]❌ No se detectó sesión OAuth2 en ~/.gemini/antigravity-cli[/red]"
    else:
        req_keys = PROVIDER_KEYS.get(provider, [])
        has_key = any(os.getenv(k) for k in req_keys)
        if not req_keys:
            k_status = "[dim]No requiere clave (local)[/dim]"
        elif has_key:
            active_k = next((k for k in req_keys if os.getenv(k)), req_keys[0])
            val = mask_secret(os.getenv(active_k))
            k_status = f"[green]✅ Configurada ({active_k}: {val})[/green]"
        else:
            k_status = f"[red]❌ No configurada (Requiere {', '.join(req_keys)})[/red]"
    table.add_row("Clave / Sesión", k_status)

    # Bitwig status
    connected = client.is_connected()
    if connected:
        table.add_row("Bitwig Extension", "[green]Conectado (Puerto 8989)[/green]")
        try:
            ctx = client.get_project()
            table.add_row("Tempo Bitwig", f"{ctx.tempo:.1f} BPM")
            table.add_row("Reproducción", "[green]Playing ▶[/green]" if ctx.isPlaying else "[yellow]Stopped ■[/yellow]")
            track_names = [t.name for t in ctx.tracks]
            summary = f"{len(track_names)} pistas: {', '.join(track_names[:6])}{'...' if len(track_names) > 6 else ''}"
            table.add_row("Pistas Detectadas", summary)
        except Exception as e:
            table.add_row("Bitwig Data", f"[yellow]Error leyendo datos: {e}[/yellow]")
    else:
        table.add_row("Bitwig Extension", "[yellow]Desconectado (Abre Bitwig Studio con la extensión BitwigAgentBridge)[/yellow]")

    console.print(table)
    console.print()

def show_history(messages: list):
    """
    Renders formatted conversation history of the current session.
    """
    user_or_asst = [m for m in messages if m.get("role") in ("user", "assistant")]
    if not user_or_asst:
        console.print("[dim]El historial de esta sesión está vacío aún.[/dim]\n")
        return

    console.print(Panel.fit("[bold cyan]📜 Historial de la Conversación Activa[/bold cyan]", border_style="cyan"))

    for m in messages:
        role = m.get("role")
        content = m.get("content") or ""
        tool_calls = m.get("tool_calls")

        if role == "user":
            console.print(Panel(content, title="👤 Usuario", border_style="blue", title_align="left"))
        elif role == "assistant":
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "tool")
                    args = fn.get("arguments", "")
                    console.print(f"  [yellow]⚙️ Acción en Bitwig:[/yellow] [bold]{fn_name}[/bold] [dim]{args}[/dim]")
            if content:
                console.print(Panel(Markdown(content), title="🤖 Asistente Bitwig", border_style="green", title_align="left"))
        elif role == "tool":
            pass # Keep output clean

    console.print()

def list_sessions_table():
    sessions = session_manager.list_sessions()
    if not sessions:
        console.print("[yellow]No hay sesiones guardadas aún.[/yellow]\n")
        return

    table = Table(title="🧵 Sesiones Guardadas", border_style="cyan")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Título", style="bold white")
    table.add_column("Proveedor", style="magenta")
    table.add_column("Modelo", style="green")
    table.add_column("Modificado", style="dim")
    table.add_column("Mensajes", justify="right", style="yellow")

    for s in sessions:
        table.add_row(
            s.get("id", ""),
            s.get("title", ""),
            s.get("provider", "").upper(),
            s.get("model", "").split("/")[-1],
            s.get("updated_at", "")[:16].replace("T", " "),
            str(s.get("message_count", 0)),
        )

    console.print(table)
    console.print()

def show_help():
    help_text = """
### 🪄 Comandos Mágicos Disponibles

- **/session** : Menú interactivo para gestionar sesiones (listar, guardar, nueva, historial, eliminar).
  - **/session list** : Lista las sesiones guardadas en tabla.
  - **/session save [nombre]** : Guarda la sesión actual con un título personalizado.
  - **/session load <id>** : Carga una sesión específica por su ID o parte de su nombre.
  - **/session new [título]** : Inicia una nueva sesión en blanco.
  - **/session delete <id>** : Elimina una sesión guardada.
- **/resume [query]** : Diálogo rápido para reanudar una conversación previa (o búsqueda por texto).
- **/history** : Muestra el historial completo de la conversación activa con las acciones musicales tomadas.
- **/provider** : Selecciona el proveedor de LLM (Google AI, Google Antigravity, KiloCode, Anthropic, OpenAI, OpenRouter, Groq, Ollama).
- **/model** : Abre el selector de modelos consultando en vivo la API del proveedor actual.
- **/keys** : Diálogo interactivo para ver, configurar y eliminar tus API Keys (`GEMINI_API_KEY`, `KILOCODE_API_KEY`, `ANTHROPIC_API_KEY`, etc.).
- **/status** : Muestra el estado del sistema, transporte y pistas de Bitwig Studio.
- **/clear** : Reinicia el historial en memoria de la sesión actual.
- **/exit** o **/quit** : Salir de la aplicación.

### 🎵 Ejemplos de Peticiones Musicales
- *"Crea una progresión Neo-Soul de 4 compases en D menor con acordes con novena en la pista Keys"*
- *"Pon el tempo a 85 bpm y genera una progresión lofi suave"*
- *"Crea una línea de bajo funky en la pista 2 que acompañe la progresión"*
- *"Borra el clip de la pista 1 y dale al play"*
"""
    console.print(Panel(Markdown(help_text.strip()), title="💡 Ayuda y Comandos", border_style="cyan"))

def main():
    parser = argparse.ArgumentParser(description="Bitwig AI Agent - Control Bitwig Studio con cualquier LLM")
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Especificar modelo temporalmente"
    )
    parser.add_argument(
        "--session",
        "-s",
        type=str,
        default=None,
        help="ID de sesión para reanudar al inicio"
    )
    parser.add_argument(
        "--prompt",
        "-p",
        type=str,
        default=None,
        help="Petición directa de una sola vez sin modo interactivo"
    )
    args = parser.parse_args()

    active_provider = get_active_provider()
    active_model = args.model or get_active_model()

    client = BitwigClient()

    # Load or create active session
    if args.session:
        active_session = session_manager.get_session(args.session)
        if not active_session:
            active_session = session_manager.create_session(title=args.session, provider=active_provider, model=active_model)
    else:
        # Create a fresh session for this run
        active_session = session_manager.create_session(title="Nueva Sesión", provider=active_provider, model=active_model)

    agent = BitwigAgent(
        model=active_model,
        client=client,
        session_id=active_session.id,
        session_title=active_session.title
    )
    if active_session.messages:
        agent.load_history(active_session.messages, session_id=active_session.id, title=active_session.title)

    if args.prompt:
        with console.status(f"[cyan]Procesando petición musical con {active_model}...[/cyan]"):
            response = agent.chat(args.prompt)
        active_session.messages = list(agent.messages)
        session_manager.save_session(active_session)
        console.print(Markdown(response))
        return

    print_banner(client, active_provider, active_model, active_session)

    completer = BitwigCliCompleter(session_manager=session_manager)
    history_dir = os.path.expanduser("~/.bitwig_agent")
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, "cli_history")

    prompt_session = PromptSession(
        completer=completer,
        complete_while_typing=True,
        history=FileHistory(history_file),
        style=cli_style,
    )

    while True:
        try:
            safe_prov = html.escape(active_provider)
            safe_mod = html.escape(active_model.split("/")[-1])
            safe_title = html.escape(active_session.title[:15])

            prompt_text = HTML(
                f"<provider>{safe_prov}</provider>:"
                f"<model>{safe_mod}</model> "
                f"<session>({safe_title})</session> "
                f"<arrow>Bitwig &gt; </arrow>"
            )

            prompt = prompt_session.prompt(prompt_text).strip()
            if not prompt:
                continue

            cmd = prompt.lower()

            if cmd in ("/exit", "/quit", "exit", "quit", "q"):
                console.print("[dim]Guardando sesión y saliendo de Bitwig Agent. ¡Hasta la próxima sesión de música![/dim]")
                active_session.messages = list(agent.messages)
                session_manager.save_session(active_session)
                break

            # ───────────────────── SESSION COMMANDS ─────────────────────
            if cmd.startswith("/session"):
                parts = prompt.strip().split(maxsplit=2)
                subcommand = parts[1].lower() if len(parts) > 1 else None
                subarg = parts[2].strip() if len(parts) > 2 else ""

                if not subcommand:
                    # Show interactive session menu
                    choice = session_menu_dialog()
                    if choice == "RESUME":
                        target_id = select_session_dialog()
                        if target_id:
                            loaded = session_manager.get_session(target_id)
                            if loaded:
                                active_session = loaded
                                agent.load_history(loaded.messages, session_id=loaded.id, title=loaded.title)
                                if loaded.provider:
                                    active_provider = loaded.provider
                                    set_active_provider(loaded.provider)
                                if loaded.model:
                                    active_model = loaded.model
                                    set_active_model(loaded.model)
                                    agent.model = loaded.model
                                console.print(f"[bold green]✓ Sesión '{loaded.title}' cargada exitosamente ({loaded.message_count} mensajes).[/bold green]\n")
                    elif choice == "SAVE":
                        new_name = save_session_name_dialog(active_session.title)
                        if new_name and new_name.strip():
                            active_session.title = new_name.strip()
                            active_session.messages = list(agent.messages)
                            active_session.provider = active_provider
                            active_session.model = active_model
                            session_manager.save_session(active_session)
                            agent.session_title = active_session.title
                            console.print(f"[bold green]✓ Sesión guardada como: '{active_session.title}'[/bold green]\n")
                    elif choice == "NEW":
                        new_title = save_session_name_dialog("Nueva Sesión") or "Nueva Sesión"
                        active_session = session_manager.create_session(title=new_title, provider=active_provider, model=active_model)
                        agent.reset_history()
                        agent.session_id = active_session.id
                        agent.session_title = active_session.title
                        console.print(f"[bold green]✓ Nueva sesión iniciada: '{active_session.title}'[/bold green]\n")
                    elif choice == "HISTORY":
                        show_history(agent.messages)
                    elif choice == "DELETE":
                        del_id = delete_session_dialog()
                        if del_id:
                            session_manager.delete_session(del_id)
                            console.print(f"[bold yellow]✓ Sesión '{del_id}' eliminada.[/bold yellow]\n")
                    continue

                if subcommand == "list":
                    list_sessions_table()
                    continue

                if subcommand == "save":
                    name = subarg or active_session.title
                    active_session.title = name
                    active_session.messages = list(agent.messages)
                    active_session.provider = active_provider
                    active_session.model = active_model
                    session_manager.save_session(active_session)
                    console.print(f"[bold green]✓ Sesión '{active_session.title}' guardada ({active_session.id}).[/bold green]\n")
                    continue

                if subcommand == "load":
                    if not subarg:
                        console.print("[red]Uso: /session load <id_o_nombre>[/red]\n")
                        continue
                    found = session_manager.get_session(subarg)
                    if not found:
                        matches = session_manager.find_sessions(subarg)
                        if matches:
                            found = session_manager.get_session(matches[0]["id"])
                    if found:
                        active_session = found
                        agent.load_history(found.messages, session_id=found.id, title=found.title)
                        if found.provider:
                            active_provider = found.provider
                            set_active_provider(found.provider)
                        if found.model:
                            active_model = found.model
                            set_active_model(found.model)
                            agent.model = found.model
                        console.print(f"[bold green]✓ Sesión '{found.title}' cargada ({found.message_count} mensajes).[/bold green]\n")
                    else:
                        console.print(f"[red]No se encontró la sesión '{subarg}'. Usa /session list para ver las disponibles.[/red]\n")
                    continue

                if subcommand == "new":
                    title = subarg or "Nueva Sesión"
                    active_session = session_manager.create_session(title=title, provider=active_provider, model=active_model)
                    agent.reset_history()
                    agent.session_id = active_session.id
                    agent.session_title = active_session.title
                    console.print(f"[bold green]✓ Nueva sesión iniciada: '{active_session.title}'[/bold green]\n")
                    continue

                if subcommand == "delete":
                    if not subarg:
                        console.print("[red]Uso: /session delete <id>[/red]\n")
                        continue
                    if session_manager.delete_session(subarg):
                        console.print(f"[bold yellow]✓ Sesión '{subarg}' eliminada.[/bold yellow]\n")
                    else:
                        console.print(f"[red]No se pudo eliminar la sesión '{subarg}'.[/red]\n")
                    continue

                console.print("[yellow]Subcomandos disponibles: list, save, load, new, delete (o /session para abrir el menú interactivo).[/yellow]\n")
                continue

            # ───────────────────── RESUME COMMAND ─────────────────────
            if cmd.startswith("/resume"):
                parts = prompt.strip().split(maxsplit=1)
                query = parts[1].strip() if len(parts) > 1 else None

                target_id = None
                if query:
                    matches = session_manager.find_sessions(query)
                    if len(matches) == 1:
                        target_id = matches[0]["id"]
                    elif len(matches) > 1:
                        console.print(f"[yellow]Múltiples coincidencias para '{query}'. Abriendo selector...[/yellow]")
                        target_id = select_session_dialog(title=f"Coincidencias para '{query}'")
                    else:
                        console.print(f"[yellow]No se encontró sesión con '{query}'. Abriendo todas...[/yellow]")
                        target_id = select_session_dialog()
                else:
                    target_id = select_session_dialog()

                if target_id:
                    loaded = session_manager.get_session(target_id)
                    if loaded:
                        active_session = loaded
                        agent.load_history(loaded.messages, session_id=loaded.id, title=loaded.title)
                        if loaded.provider:
                            active_provider = loaded.provider
                            set_active_provider(loaded.provider)
                        if loaded.model:
                            active_model = loaded.model
                            set_active_model(loaded.model)
                            agent.model = loaded.model
                        console.print(f"[bold green]✓ Sesión '{loaded.title}' reanudada con éxito ({loaded.message_count} mensajes).[/bold green]\n")
                continue

            # ───────────────────── HISTORY COMMAND ─────────────────────
            if cmd in ("/history", "/historial"):
                show_history(agent.messages)
                continue

            # ───────────────────── PROVIDER & MODEL COMMANDS ─────────────────────
            if cmd in ("/provider", "/providers"):
                new_provider = select_provider_dialog()
                if new_provider:
                    active_provider = new_provider
                    set_active_provider(new_provider)
                    active_session.provider = new_provider
                    console.print(f"[bold green]✓ Proveedor establecido a:[/bold green] [magenta]{active_provider.upper()}[/magenta]")

                    if active_provider == "antigravity" and not AntigravityClient.is_logged_in():
                        console.print("[yellow]⚠️ Advertencia: No se encontró sesión activa de Antigravity en ~/.gemini/antigravity-cli[/yellow]")

                    console.print(f"[dim]Consultando catálogo de modelos para {active_provider.upper()}...[/dim]")
                    new_model = select_model_dialog(provider=active_provider)
                    if new_model:
                        active_model = new_model
                        set_active_model(new_model)
                        agent.model = active_model
                        active_session.model = active_model
                        console.print(f"[bold green]✓ Modelo activo configurado:[/bold green] [green]{active_model}[/green]\n")
                    else:
                        default_m = PROVIDER_DEFAULT_MODELS.get(active_provider, active_model)
                        active_model = default_m
                        set_active_model(default_m)
                        agent.model = active_model
                        active_session.model = active_model
                        console.print(f"[dim]Usando modelo por defecto:[/dim] [green]{active_model}[/green]\n")
                continue

            if cmd in ("/model", "/models"):
                console.print(f"[dim]Consultando modelos de {active_provider.upper()}...[/dim]")
                new_model = select_model_dialog(provider=active_provider, current_model=active_model)
                if new_model:
                    active_model = new_model
                    set_active_model(new_model)
                    agent.model = active_model
                    active_session.model = active_model
                    console.print(f"[bold green]✓ Modelo cambiado exitosamente a:[/bold green] [green]{active_model}[/green]\n")
                continue

            if cmd in ("/keys", "/key"):
                manage_keys_dialog()
                load_dotenv(override=True)
                console.print("[bold green]✓ Configuración de claves actualizada.[/bold green]\n")
                continue

            if cmd == "/status":
                show_status(client, active_provider, active_model, active_session)
                continue

            if cmd in ("/help", "/?"):
                show_help()
                continue

            if cmd == "/clear":
                agent.reset_history()
                active_session.messages = []
                session_manager.save_session(active_session)
                console.print("[dim]Historial de conversación reiniciado.[/dim]\n")
                continue

            # ───────────────────── NORMAL CHAT TURN ─────────────────────
            # Auto-update title on first user message if it's default
            if active_session.title in ("Nueva Sesión", "Sesión sin título") and active_session.message_count == 0:
                active_session.title = session_manager.auto_title_from_prompt(prompt)

            with console.status(f"[cyan]Pensando y componiendo en Bitwig ({active_model})...[/cyan]"):
                response = agent.chat(prompt)

            # Auto-save session
            active_session.messages = list(agent.messages)
            active_session.provider = active_provider
            active_session.model = active_model
            session_manager.save_session(active_session)

            console.print("\n", Markdown(response), "\n")

        except KeyboardInterrupt:
            console.print("\n[dim]Interrumpido. Escribe /exit para salir.[/dim]")
        except EOFError:
            console.print("\n[dim]Guardando sesión y saliendo de Bitwig Agent. ¡Hasta la próxima sesión de música![/dim]")
            active_session.messages = list(agent.messages)
            session_manager.save_session(active_session)
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}\n")

if __name__ == "__main__":
    main()
