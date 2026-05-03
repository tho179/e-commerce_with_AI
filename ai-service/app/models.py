from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.sqlite import JSON

from .db import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    book_id = Column(Integer, nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    comment = Column(String, default="")
    sentiment_label = Column(String(16), default="neutral")
    sentiment_score = Column(Float, default=0.5)
    aspect_tags = Column(JSON, default=list)
    advice = Column(String, default="")
    ai_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class RecommendationSnapshot(Base):
    __tablename__ = "recommendation_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    recommendations = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class ModelDriftSnapshot(Base):
    __tablename__ = "model_drift_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(40), default="system")
    review_count = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    average_sentiment = Column(Float, default=0.0)
    divergence = Column(Float, default=0.0)
    negative_ratio = Column(Float, default=0.0)
    needs_retrain = Column(Boolean, default=False)
    note = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
