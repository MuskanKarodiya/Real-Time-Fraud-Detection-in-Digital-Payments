"""
FastAPI Application - Fraud Detection API

Key Concepts:
1. @app.post() - Define POST endpoint
2. async def - Asynchronous for concurrent requests
3. Dependency Injection - Clean way to share resources
4. Middleware - CORS, logging, etc.
"""
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import List

from app.config import API_TITLE, API_VERSION, API_DESCRIPTION, ALLOWED_ORIGINS
from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthResponse,
    ModelInfoResponse
)
from app.model import model_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager - runs on startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan.

    Startup: Load model, verify health
    Shutdown: Clean up resources
    """
    # Startup
    logger.info("Starting Fraud Detection API...")
    logger.info("Loading ML model...")

    if model_service.health_check():
        logger.info("✓ Model loaded successfully")
        logger.info(f"Model info: {model_service.get_model_info()}")
    else:
        logger.error("✗ Model loading failed!")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down Fraud Detection API...")


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)


# CORS Middleware
# Allows frontend apps to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information.

    Returns basic API info and available endpoints.
    """
    return {
        "message": "Fraud Detection API",
        "version": API_VERSION,
        "status": "running",
        "endpoints": {
            "predict": "/api/v1/predict",
            "batch_predict": "/api/v1/predict/batch",
            "health": "/api/v1/health",
            "model_info": "/api/v1/model/info",
            "docs": "/docs"
        }
    }


# Health Check Endpoint
@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Used by:
    - Load balancers to check service health
    - Monitoring systems
    - Kubernetes probes

    Returns service status and model loading state.
    """
    model_loaded = model_service.health_check()

    return HealthResponse(
        status="healthy" if model_loaded else "unhealthy",
        model_loaded=model_loaded,
        version=API_VERSION,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


# Model Info Endpoint
@app.get("/api/v1/model/info", response_model=ModelInfoResponse, tags=["Model"])
async def get_model_info():
    """
    Get model information.

    Returns:
    - Model name and version
    - Training date
    - Feature count
    - Performance metrics
    - API version
    """
    try:
        info = model_service.get_model_info()
        return ModelInfoResponse(
            model_name=info.get("model_name", "Unknown"),
            model_version=info.get("model_version", "Unknown"),
            algorithm=info.get("algorithm", "Unknown"),
            training_date=info.get("training_date", "Unknown"),
            feature_count=info.get("feature_count", 31),
            threshold=info.get("threshold", 0.5),
            performance=info.get("performance", {}),
            api_version=API_VERSION
        )
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model information"
        )


# Single Prediction Endpoint
@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(request: PredictionRequest):
    """
    Predict fraud for a single transaction.

    Request Body:
    {
        "transaction_id": "txn_123",
        "amount": 150.50,
        "features": [31 float values]
    }

    Response:
    {
        "transaction_id": "txn_123",
        "fraud_probability": 0.234,
        "prediction": 0,
        "risk_level": "LOW",
        "threshold_used": 0.5,
        "processed_at": "2026-03-19T10:30:00Z"
    }

    HTTP Status Codes:
    - 200: Successful prediction
    - 422: Invalid request data
    - 500: Prediction service error
    """
    try:
        # Make prediction
        result = model_service.predict(
            features=request.features,
            threshold=request.threshold if hasattr(request, 'threshold') else None
        )

        # Build response
        return PredictionResponse(
            transaction_id=request.transaction_id,
            fraud_probability=result["fraud_probability"],
            prediction=result["prediction"],
            risk_level=result["risk_level"],
            threshold_used=result["threshold_used"],
            processed_at=datetime.utcnow().isoformat() + "Z"
        )

    except ValueError as e:
        # Validation error
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected error
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


# Batch Prediction Endpoint
@app.post("/api/v1/predict/batch", response_model=BatchPredictionResponse, tags=["Prediction"])
async def predict_batch(request: BatchPredictionRequest):
    """
    Predict fraud for multiple transactions.

    More efficient than multiple single predictions.

    Request Body:
    {
        "threshold": 0.5,
        "transactions": [
            {"transaction_id": "txn1", "amount": 100, "features": [...]},
            {"transaction_id": "txn2", "amount": 200, "features": [...]}
        ]
    }

    Response:
    {
        "predictions": [...],
        "total_processed": 2,
        "fraud_count": 0,
        "fraud_rate": 0.0,
        "processed_at": "2026-03-19T10:30:00Z"
    }
    """
    try:
        # Extract features from all transactions
        features_list = [txn.features for txn in request.transactions]
        transaction_ids = [txn.transaction_id for txn in request.transactions]

        # Make batch prediction
        predictions = model_service.predict_batch(
            features_list=features_list,
            threshold=request.threshold
        )

        # Build response
        prediction_responses = []
        fraud_count = 0

        for txn_id, pred in zip(transaction_ids, predictions):
            fraud_count += pred["prediction"]
            prediction_responses.append(
                PredictionResponse(
                    transaction_id=txn_id,
                    fraud_probability=pred["fraud_probability"],
                    prediction=pred["prediction"],
                    risk_level=pred["risk_level"],
                    threshold_used=pred["threshold_used"],
                    processed_at=datetime.utcnow().isoformat() + "Z"
                )
            )

        return BatchPredictionResponse(
            predictions=prediction_responses,
            total_processed=len(prediction_responses),
            fraud_count=fraud_count,
            fraud_rate=round(fraud_count / len(prediction_responses), 4),
            processed_at=datetime.utcnow().isoformat() + "Z"
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )
