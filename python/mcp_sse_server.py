from starlette.routing import Route
from bitwig_agent.mcp.server import mcp_server

# Streamable HTTP en /sse (el cliente remoto hace POST /sse) y alias en /mcp
app = mcp_server.streamable_http_app(streamable_http_path="/sse", host="0.0.0.0")
_r = [r for r in app.router.routes if getattr(r, "path", None) == "/sse"][0]
app.router.routes.append(Route("/mcp", endpoint=_r.endpoint, methods=list(_r.methods or [])))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, proxy_headers=True, forwarded_allow_ips="*")
