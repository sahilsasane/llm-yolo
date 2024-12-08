from fastapi import (
    APIRouter,
    File,
    UploadFile,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
)
from uuid import uuid4
import os
from config.settings import settings
from utils.file_handler import FileHandler
from services.llm_service import LLMService
from core.data_processor import DataProcessor
from core.meta_data import MetadataExtractor
from typing import List

# from api.websocket import ConnectionManager
from schema.requests import QueryRequest

router = APIRouter()
file_handler = FileHandler()
meta_data = MetadataExtractor()
llm_service = LLMService(settings.MODEL_NAME)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = str(uuid4())
        file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}_{file.filename}")
        output_path = os.path.join(settings.OUTPUT_DIR, f"{file_id}.csv")

        # Create directories if they don't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

        # Save and process file
        file_handler.save_upload_file(file, file_path)
        file_type = file.filename.split(".")[-1].lower()

        if file_type not in ["csv", "xlsx"]:
            raise ValueError("Unsupported file type")

        data_processor = DataProcessor()
        data_processor.clean_and_process_file(
            file_path=file_path, output_path=output_path
        )

        return {"file_id": file_id, "filename": file.filename}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload file: {str(e)}")


async def query(query_request: QueryRequest):
    try:
        output_path = os.path.join(settings.OUTPUT_DIR, f"{query_request.file_id}.csv")
        df = file_handler.read_dataframe(output_path, "csv")
        metadata = meta_data.extract_metadata(df)

        agent_executor = llm_service.setup_agent(df, metadata)
        query_input = f"""
        query: {query_request.query}
        You're task is to write code to satisfy the query and also execute.
        Use the tools provided to execute the code.
        Output the stdout of the code exectution.
        The output should be formatted so that each row appears on a new line, enclosed in a Python code block.
        
        Here is the dataset schema:
        {metadata['Schema']}
        """

        result = agent_executor.invoke({"input": query_input, "chat_history": ""})
        return {"response": result["output"]}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")


@router.websocket("/ws/query")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if (
                websocket.application_state == "CLOSING"
                or websocket.application_state == "CLOSED"
            ):
                break
            query_request = QueryRequest(**data)
            try:
                response = await query(query_request)
                await manager.broadcast(response["response"])

            except Exception as e:
                error_message = f"Query failed: {str(e)}"
                await manager.broadcast(f"{error_message}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A client disconnected.")
