"""
FastAPI Application - Fraud Detection API

Features:
- API Key Authentication
- Rate Limiting
- Request Logging
- Enhanced Error Handling (RFC 7807)
"""
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Request, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from app.auth import verify_api_key, verify_api_key_optional, get_client_info
from app.logging_config import prediction_logger
from app.rate_limit import prediction_rate_limit_checker
from app.exceptions import (
    APIException,
    api_exception_handler,
    http_exception_handler,
    ValidationError,
    ModelError
)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup/shutdown."""
    print("Starting Fraud Detection API...")
    print("Loading ML model...")

    if model_service.health_check():
        print("✓ Model loaded successfully")
        print(f"Model: {model_service.get_model_info()}")
    else:
        print("✗ Model loading failed!")

    yield

    print("Shutting down Fraud Detection API...")


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)


# Exception handlers
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate response time
    process_time = (time.time() - start_time) * 1000

    # Log to console
    print(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")

    return response


# ============================================================================
# PUBLIC ENDPOINTS (No Authentication Required)
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information."""
    return {
        "message": "Fraud Detection API",
        "version": API_VERSION,
        "status": "running",
        "authentication": "API Key required for protected endpoints",
        "endpoints": {
            "predict": "/api/v1/predict",
            "batch_predict": "/api/v1/predict/batch",
            "health": "/api/v1/health",
            "model_info": "/api/v1/model/info",
            "docs": "/docs"
        }
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint - no authentication required."""
    model_loaded = model_service.health_check()

    return HealthResponse(
        status="healthy" if model_loaded else "unhealthy",
        model_loaded=model_loaded,
        version=API_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.get("/api/v1/model/info", response_model=ModelInfoResponse, tags=["Model"])
async def get_model_info():
    """Get model information - no authentication required."""
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
        raise ModelError(f"Failed to retrieve model information: {str(e)}")


# ============================================================================
# PROTECTED ENDPOINTS (API Key Authentication Required)
# ============================================================================

@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(
    request: PredictionRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(prediction_rate_limit_checker)
):
    """
    Predict fraud for a single transaction.

    Authentication: Required (X-API-Key header)
    Rate Limit: 60 requests per minute
    """
    start_time = time.time()

    try:
        # Make prediction
        result = model_service.predict(features=request.features)

        # Build response
        response_data = {
            "transaction_id": request.transaction_id,
            "fraud_probability": result["fraud_probability"],
            "prediction": result["prediction"],
            "risk_level": result["risk_level"],
            "threshold_used": result["threshold_used"],
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

        # Log prediction
        response_time = (time.time() - start_time) * 1000
        prediction_logger.log_prediction(
            transaction_id=request.transaction_id,
            request=request.model_dump(),
            response=response_data,
            api_key=api_key,
            response_time_ms=response_time
        )

        return PredictionResponse(**response_data)

    except ValueError as e:
        # Log error
        prediction_logger.log_error(
            endpoint="/api/v1/predict",
            error=e,
            request_data=request.model_dump(),
            api_key=api_key
        )
        raise ValidationError(str(e))

    except Exception as e:
        prediction_logger.log_error(
            endpoint="/api/v1/predict",
            error=e,
            request_data=request.model_dump(),
            api_key=api_key
        )
        raise ModelError(f"Prediction failed: {str(e)}")


@app.post("/api/v1/predict/batch", response_model=BatchPredictionResponse, tags=["Prediction"])
async def predict_batch(
    request: BatchPredictionRequest,
    http_request: Request,
    api_key: str = Depends(verify_api_key),
    _rate_limit: None = Depends(prediction_rate_limit_checker)
):
    """
    Predict fraud for multiple transactions.

    Authentication: Required (X-API-Key header)
    Rate Limit: 60 requests per minute
    Max Batch Size: 100 transactions
    """
    start_time = time.time()

    try:
        # Extract features and IDs
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

        for txn_id, pred, txn in zip(transaction_ids, predictions, request.transactions):
            fraud_count += pred["prediction"]
            prediction_responses.append(
                PredictionResponse(
                    transaction_id=txn_id,
                    fraud_probability=pred["fraud_probability"],
                    prediction=pred["prediction"],
                    risk_level=pred["risk_level"],
                    threshold_used=pred["threshold_used"],
                    processed_at=datetime.now(timezone.utc).isoformat()
                )
            )

        response_data = {
            "predictions": prediction_responses,
            "total_processed": len(prediction_responses),
            "fraud_count": fraud_count,
            "fraud_rate": round(fraud_count / len(prediction_responses), 4),
            "processed_at": datetime.now(timezone.utc).isoformat()
        }

        # Log batch prediction
        response_time = (time.time() - start_time) * 1000
        prediction_logger.log_batch_prediction(
            transactions=[t.model_dump() for t in request.transactions],
            responses=[p.model_dump() for p in prediction_responses],
            api_key=api_key,
            response_time_ms=response_time
        )

        return BatchPredictionResponse(**response_data)

    except ValueError as e:
        prediction_logger.log_error(
            endpoint="/api/v1/predict/batch",
            error=e,
            api_key=api_key
        )
        raise ValidationError(str(e))

    except Exception as e:
        prediction_logger.log_error(
            endpoint="/api/v1/predict/batch",
            error=e,
            api_key=api_key
        )
        raise ModelError(f"Batch prediction failed: {str(e)}")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    prediction_logger.log_error(
        endpoint=str(request.url.path),
        error=exc
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "https://api.fraud-detection.com/errors/internal-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
            "instance": str(request.url.path)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
