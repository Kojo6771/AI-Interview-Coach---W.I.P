# CVResponse is a Pydantic model that represents the response schema for a CV document.
from datetime import datetime
from pydantic import BaseModel, ConfigDict

#cv response model
class CVResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_type: str
    uploaded_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

class CVDetailResponse(CVResponse):
    extracted_text:str