from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    file_id: str = Field(
        ..., title="File ID", description="The ID of the uploaded file"
    )
    query: str = Field(..., title="Query", description="The query to be executed")
