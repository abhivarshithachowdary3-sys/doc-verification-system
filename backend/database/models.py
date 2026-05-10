"""SQLModel database models."""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column

class VerificationRecord(SQLModel, table=True):
    __tablename__ = "verification_records"
    request_id:         str            = Field(primary_key=True)
    status:             str
    document_type:      Optional[str]  = None
    fraud_score:        Optional[float]= None
    verification_score: Optional[float]= None
    blockchain_tx:      Optional[str]  = None
    report_json:        Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    created_at:         datetime       = Field(default_factory=datetime.utcnow)
