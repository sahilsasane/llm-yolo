from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    file_id: str = Field(
        ..., title="File ID", description="The ID of the uploaded file"
    )
    threshold: int = Field(
        10,
        title="Threshold",
        description="The minimum number of potholes to consider a zone critical",
    )
