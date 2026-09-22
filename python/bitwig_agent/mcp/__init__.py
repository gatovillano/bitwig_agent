def __getattr__(name: str):
    if name in ("mcp_server", "main"):
        from bitwig_agent.mcp.server import mcp_server, main
        return {"mcp_server": mcp_server, "main": main}[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["mcp_server", "main"]
