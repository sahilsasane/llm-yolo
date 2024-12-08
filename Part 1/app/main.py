from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import endpoints
import logging

logging.basicConfig(level=logging.DEBUG)


def create_app() -> FastAPI:
    app = FastAPI(
        title="CSV Query Chatbot",
        description="A FastAPI app with CSV query and real-time chat",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Update to your frontend URL
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(endpoints.router, prefix="/api", tags=["File", "Query"])

    app.add_websocket_route("/ws/query", endpoints.websocket_endpoint)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:create_app", host="127.0.0.1", port=8800, reload=True)
