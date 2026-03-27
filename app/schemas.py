"""
Pydantic Schemas for Request/Response Validation

FastAPI uses these to automatically:
1. Validate incoming data types
2. Convert JSON to Python objects
3. Generate API documentation
4. Return helpful error messages
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from datetime import datetime


class PredictionRequest(BaseModel):
    """
    Request schema for single transaction prediction.

    FastAPI will automatically:
    - Check that transaction_id is a string
    - Check that amount is a positive number
    - Check that features has exactly 31 values
    - Return 422 error if validation fails
    """
    transaction_id: str = Field(
        ...,
        description="Unique transaction identifier",
        min_length=1,
        max_length=100
    )
    amount: float = Field(
        ...,
        description="Transaction amount in USD (must be greater than 0)",
        gt=0
    )
    features: List[float] = Field(
        ...,
        description="31 features: V1-V28, amount_scaled, hour_sin, hour_cos",
        min_length=31,
        max_length=31
    )

    @field_validator('transaction_id')
    @classmethod
    def transaction_id_must_not_be_empty(cls, v: str) -> str:
        """Custom validator: ensure transaction_id is not just whitespace."""
        if not v.strip():
            raise ValueError('transaction_id cannot be empty or whitespace')
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_id": "txn_123456",
                "amount": 150.50,
                "features": [
                    -1.36, 0.21, 1.48, -0.52, 1.23, -0.36, 0.45, -0.12,
                    0.89, -0.78, 1.12, -0.34, 0.67, -1.45, 0.23, -0.89,
                    1.34, -0.56, 0.78, -1.23, 0.45, -0.67, 1.89, -0.34,
                    0.56, -0.78, 1.23, -0.45, 0.12, 0.89, -0.23
                ]
            }
        }
    )


class PredictionResponse(BaseModel):
    """Response schema for prediction result."""
    transaction_id: str = Field(..., description="Transaction ID from request")
    fraud_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probability of fraud (0-1)"
    )
    prediction: int = Field(
        ...,
        ge=0,
        le=1,
        description="Binary prediction (0=legitimate, 1=fraud)"
    )
    risk_level: str = Field(
        ...,
        description="Risk category: HIGH, MEDIUM, or LOW"
    )
    threshold_used: float = Field(
        ...,
        description="Decision threshold used for binary prediction"
    )
    processed_at: str = Field(
        ...,
        description="ISO timestamp of prediction"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_id": "txn_123456",
                "fraud_probability": 0.234,
                "prediction": 0,
                "risk_level": "LOW",
                "threshold_used": 0.5,
                "processed_at": "2026-03-19T10:30:00Z"
            }
        }
    )


class BatchPredictionRequest(BaseModel):
    """Request schema for batch predictions."""
    threshold: Optional[float] = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Decision threshold (default: 0.5)"
    )
    transactions: List[PredictionRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of transactions (max 100 per batch)"
    )


class BatchPredictionResponse(BaseModel):
    """Response schema for batch predictions."""
    predictions: List[PredictionResponse]
    total_processed: int
    fraud_count: int
    fraud_rate: float
    processed_at: str


class HealthResponse(BaseModel):
    """Response schema for health check."""
    model_config = ConfigDict(protected_namespaces=())
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether model is loaded")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="ISO timestamp")


class ModelInfoResponse(BaseModel):
    """Response schema for model information."""
    model_config = ConfigDict(protected_namespaces=())
    model_name: str
    model_version: str
    algorithm: str
    training_date: str
    feature_count: int
    threshold: float
    performance: dict
    api_version: str
