"""Safe customer DTOs and ownership checks before every remote operation."""

import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from parking.api.gateway import Gateway
from parking.api.sessions import Conflict, NotFound, Registry
from parking.api.submissions import Submissions
from parking.graph.schemas import GraphInput, GraphOutput
from parking.settings import Settings


Handle = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")]
WEB = Path(__file__).resolve().parents[1] / "web"


class ChatRequest(GraphInput):
    thread_id: Handle


class ChatReply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: str
    request_id: str
    status: Literal["pending", "completed", "failed"]
    reply: GraphOutput | None
    error_code: str | None
    retryable: bool


def create_app(settings=None, client=None):
    settings = settings or Settings.from_env()
    registry = Registry(settings.application_path)
    ledger = Submissions(registry)
    gateway = Gateway(settings, ledger, client=client)
    app = FastAPI(title="Parking reservation assistant", docs_url=None, redoc_url=None)
    app.state.gateway = gateway
    app.state.registry = registry
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=True,
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def browser_boundary(request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins:
            return JSONResponse({"error_code": "origin_denied"}, status_code=403)
        if request.method == "POST" and request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error_code": "origin_denied"}, status_code=403)
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 32000:
            return JSONResponse({"error_code": "invalid_request"}, status_code=413)
        owner = registry.owner(request.cookies.get("parking_owner"))
        request.state.owner = owner
        response = await call_next(request)
        response.set_cookie("parking_owner", owner, httponly=True, samesite="strict", path="/")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request, error):
        return JSONResponse({"error_code": "invalid_request"}, status_code=422)

    @app.exception_handler(NotFound)
    async def missing(request, error):
        return JSONResponse({"error_code": "not_found"}, status_code=404)

    @app.exception_handler(Conflict)
    async def conflict(request, error):
        return JSONResponse({"error_code": "request_conflict"}, status_code=409)

    @app.exception_handler(Exception)
    async def unavailable(request, error):
        return JSONResponse({"error_code": "service_unavailable"}, status_code=503)

    @app.get("/")
    async def index():
        return FileResponse(WEB / "index.html")

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/app.mjs")
    async def script():
        return FileResponse(WEB / "app.mjs", media_type="text/javascript")

    @app.get("/styles.css")
    async def styles():
        return FileResponse(WEB / "styles.css", media_type="text/css")

    @app.post("/api/threads")
    async def new_thread(request: Request):
        thread_id = await gateway.create_thread()
        registry.bind_thread(request.state.owner, thread_id)
        return {"thread_id": thread_id}

    @app.post("/api/chat", response_model=ChatReply)
    async def chat(body: ChatRequest, request: Request):
        registry.require_thread(request.state.owner, body.thread_id)
        try:
            result = await gateway.submit(request.state.owner, body.thread_id, body.request_id, body.message)
        except (Conflict, NotFound):
            raise
        except Exception:
            # A reserved request exists even after a lost remote acknowledgement.
            row = ledger.get(request.state.owner, body.thread_id, body.request_id)
            result = gateway.project(row)
            if result["status"] == "pending":
                return JSONResponse(ChatReply.model_validate(result).model_dump(), status_code=202)
            raise
        return JSONResponse(ChatReply.model_validate(result).model_dump(), status_code=200 if result["status"] == "completed" else 202)

    @app.get("/api/threads/{thread_id}/requests/{request_id}", response_model=ChatReply)
    async def status(thread_id: Handle, request_id: Handle, request: Request):
        registry.require_thread(request.state.owner, thread_id)
        result = await gateway.status(request.state.owner, thread_id, request_id)
        return JSONResponse(ChatReply.model_validate(result).model_dump(), status_code=202 if result["status"] == "pending" else 200)

    @app.get("/api/threads/{thread_id}/conversation")
    async def conversation(thread_id: Handle, request: Request):
        rows = registry.conversation(request.state.owner, thread_id)
        messages = []
        for row in rows:
            messages.append({"role": "user", "text": row["message"], "request_id": row["request_id"]})
            if row["status"] == "completed":
                output = GraphOutput.model_validate(json.loads(row["result"]))
                messages.append({"role": "assistant", "text": output.final_reply, "request_id": row["request_id"]})
        return {"thread_id": thread_id, "messages": messages}

    @app.get("/api/admin/reservations")
    async def pending_reservations():
        return {"reservations": gateway.admin.store.pending()}

    @app.post("/api/admin/reservations/{reservation_id}/resume", status_code=202)
    async def resume_reservation(reservation_id: Handle):
        return await gateway.admin.resume(reservation_id)

    return app
