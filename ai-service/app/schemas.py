from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    customer_id: int = Field(..., ge=1)
    book_id: int = Field(..., ge=1)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = ""


class ReviewOut(BaseModel):
    id: int
    customer_id: int
    book_id: int
    rating: int
    comment: str
    sentiment_label: str
    sentiment_score: float
    aspect_tags: List[Any]
    advice: str
    ai_metadata: Dict[str, Any]
    created_at: datetime


class RecommendationSnapshotOut(BaseModel):
    id: int
    customer_id: int
    recommendations: List[Dict[str, Any]]
    created_at: datetime
    warnings: List[str] = []


class ModelDriftSnapshotOut(BaseModel):
    id: int
    source: str
    review_count: int
    average_rating: float
    average_sentiment: float
    divergence: float
    negative_ratio: float
    needs_retrain: bool
    note: str
    created_at: datetime


class RetrainRequest(BaseModel):
    source: Optional[str] = "manual-retrain"
    note: Optional[str] = ""


class GraphRagRequest(BaseModel):
    query: str
    customer_id: Optional[int] = 0
    top_k: Optional[int] = 5


class ChatAdviceRequest(BaseModel):
    query: str
    customer_id: Optional[int] = 0
