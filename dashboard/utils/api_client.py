"""
API Client Module

Communicates with the FastAPI backend on EC2.
"""
from typing import Dict, Any, Optional

import requests
import streamlit as st

from dashboard.config import API_BASE_URL, API_TIMEOUT


@st.cache_data(ttl=10)  # Cache health checks for 10 seconds
def check_health() -> Dict[str, Any]:
    """
    Check API health status.

    Returns:
        Dict with health status info
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/health",
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "model_loaded": False,
        }


@st.cache_data(ttl=60)  # Cache model info for 1 minute
def get_model_info() -> Dict[str, Any]:
    """
    Get model information from API.

    Returns:
        Dict with model metadata
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/model/info",
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}


def make_prediction(transaction_id: str, amount: float, features: list, api_key: str) -> Dict[str, Any]:
    """
    Make a prediction request to the API.

    Args:
        transaction_id: Unique transaction identifier
        amount: Transaction amount
        features: List of 31 feature values
        api_key: API key for authentication

    Returns:
        Dict with prediction result or error info
    """
    try:
        payload = {
            "transaction_id": transaction_id,
            "amount": amount,
            "features": features
        }

        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

        # Use valid dev key if demo-key is passed
        if api_key == "demo-key":
            headers["X-API-Key"] = "dev-key-12345"

        response = requests.post(
            f"{API_BASE_URL}/api/v1/predict",
            json=payload,
            headers=headers,
            timeout=API_TIMEOUT
        )

        if response.status_code == 200:
            return response.json()
        else:
            # Try to get error detail from response
            try:
                error_detail = response.json().get("detail", "Unknown error")
            except:
                error_detail = response.text[:200] if response.text else f"HTTP {response.status_code}"

            return {
                "error": True,
                "status_code": response.status_code,
                "message": error_detail
            }

    except requests.Timeout:
        return {
            "error": True,
            "message": "Request timed out - API took too long to respond"
        }
    except requests.ConnectionError:
        return {
            "error": True,
            "message": f"Cannot connect to API at {API_BASE_URL} - check if the server is running"
        }
    except requests.RequestException as e:
        return {
            "error": True,
            "message": f"Request failed: {str(e)}"
        }


@st.cache_data(ttl=5)
def get_api_metrics() -> Dict[str, Any]:
    """
    Get API metrics if available.

    Returns:
        Dict with metrics info
    """
    health = check_health()
    model_info = get_model_info()

    return {
        "api_status": health.get("status", "unknown"),
        "model_loaded": health.get("model_loaded", False),
        "latency_ms": health.get("latency_ms"),
        "model_name": model_info.get("model_name"),
        "model_version": model_info.get("version"),
    }


def format_api_status(status: str) -> tuple:
    """
    Format API status for display.

    Returns:
        Tuple of (label, color_class, icon)
    """
    status_lower = status.lower()

    if status_lower == "healthy" or status_lower == "ok":
        return "Healthy", "dot-green", "✓"
    elif status_lower == "unhealthy" or status_lower == "error":
        return "Unhealthy", "dot-red", "✗"
    else:
        return "Unknown", "dot-gray", "?"
