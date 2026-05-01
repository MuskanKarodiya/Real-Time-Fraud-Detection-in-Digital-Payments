"""
Feature Preprocessing for Dashboard

Computes the 3 additional features (amount_scaled, hour_sin, hour_cos)
required by the API from raw transaction data.

The API expects 31 features: V1-V28 + amount_scaled + hour_sin + hour_cos
But the raw dataset has: V1-V28 + Amount + Time

This module bridges that gap.
"""
import numpy as np
from typing import List, Tuple
import joblib
from pathlib import Path


# Feature names order expected by the model
FEATURE_NAMES = [
    'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
    'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
    'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28',
    'amount_scaled', 'hour_sin', 'hour_cos'
]


def compute_amount_scaled(amount: float, scaler_path: Path = None) -> float:
    """
    Compute log-transformed amount feature.

    Uses log1p transform: log(1 + amount)

    Args:
        amount: Raw transaction amount
        scaler_path: Optional path to fitted StandardScaler (not used currently)

    Returns:
        Scaled amount value
    """
    # log1p is log(1 + x) - handles zero values gracefully
    return float(np.log1p(amount))


def compute_hour_features(time_elapsed: float) -> Tuple[float, float]:
    """
    Compute cyclic encoding for hour of day.

    Args:
        time_elapsed: Time in seconds since first transaction

    Returns:
        Tuple of (hour_sin, hour_cos)
    """
    # Convert seconds to hour (0-23)
    hour = (time_elapsed / 3600) % 24

    # Cyclic encoding preserves that hour 23 and hour 0 are adjacent
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)

    return float(hour_sin), float(hour_cos)


def preprocess_features(
    v_features: List[float],
    amount: float,
    time_elapsed: float = 0.0
) -> List[float]:
    """
    Convert raw transaction data to 31 features expected by the API.

    Args:
        v_features: List of 28 PCA features (V1-V28)
        amount: Transaction amount
        time_elapsed: Time elapsed in seconds (default: 0 = current time)

    Returns:
        List of 31 features: V1-V28 + amount_scaled + hour_sin + hour_cos
    """
    if len(v_features) != 28:
        raise ValueError(f"Expected 28 V features, got {len(v_features)}")

    # Compute the 3 additional features
    amount_scaled = compute_amount_scaled(amount)
    hour_sin, hour_cos = compute_hour_features(time_elapsed)

    # Combine all features
    return v_features + [amount_scaled, hour_sin, hour_cos]


def prepare_api_payload(
    transaction_id: str,
    v_features: List[float],
    amount: float,
    time_elapsed: float = 0.0
) -> dict:
    """
    Prepare complete API request payload.

    Args:
        transaction_id: Unique transaction identifier
        v_features: List of 28 PCA features (V1-V28)
        amount: Transaction amount
        time_elapsed: Time elapsed in seconds (default: 0)

    Returns:
        Dict with transaction_id, amount, and 31 features
    """
    features = preprocess_features(v_features, amount, time_elapsed)

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "features": features
    }


# Example fraud/legitimate transactions from the actual dataset
# These are real rows from creditcard.csv with computed features

EXAMPLE_FRAUD = {
    "transaction_id": "fraud_example_1",
    "amount": 1.00,
    "time_elapsed": 406.0,
    "v_features": [
        -2.3122265423263, 1.95199201064158, -1.60985073229769, 3.9979055875468,
        -0.522187864667764, -1.42654531920595, -2.53738730624579, 1.39165724829804,
        -2.77008927719433, -2.77227214465915, 3.20203320709635, -2.89990738849473,
        -0.595221881324605, -4.28925378244217, 0.389724120274487, -1.14074717980657,
        -2.83005567450437, -0.0168224681808257, 0.416955705037907, 0.126910559061474,
        0.517232370861764, -0.0350493686052974, -0.465211076182388, 0.320198198514526,
        0.0445191674731724, 0.177839798284401, 0.261145002567677, -0.143275874698919
    ]
}

EXAMPLE_LEGITIMATE = {
    "transaction_id": "legit_example_1",
    "amount": 1.00,
    "time_elapsed": 0.0,
    "v_features": [
        -1.3598071336738, -0.0727811733098497, 2.53634673796914, 1.37815522427443,
        -0.338320769942518, 0.462387777762292, 0.239598554061257, 0.0986979012610507,
        0.363786969611213, 0.0907941719789316, -0.551599533260813, -0.617800855762348,
        -0.991389847235408, -0.311169353699879, 1.46817697209427, -0.470400525259478,
        0.207971241929242, 0.0257905801985591, 0.403992960255733, 0.251412098239705,
        -0.018306777944153, 0.277837575558899, -0.110473910188767, 0.0669280749146731,
        0.128539358273528, -0.189114843888824, 0.133558376740387, -0.0210530534538215
    ]
}

# Borderline case - features that could be either fraud or legitimate
# This is a transaction with mixed signals
EXAMPLE_BORDERLINE = {
    "transaction_id": "borderline_example_1",
    "amount": 150.00,
    "time_elapsed": 14400.0,  # 4 hours
    "v_features": [
        0.00, 0.00, 0.00, 2.00, 0.00, 0.00, 0.00, 0.00,
        0.00, -2.00, 1.50, -1.00, 0.00, -3.50, 0.00, 0.00,
        -2.50, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
        0.00, 0.00, 0.00, 0.00
    ]
}


def get_example_payload(example_type: str = "legitimate") -> dict:
    """
    Get example transaction payload for testing.

    Args:
        example_type: "fraud", "legitimate", or "borderline"

    Returns:
        Dict with transaction_id, amount, and 31 features ready for API
    """
    examples = {
        "fraud": EXAMPLE_FRAUD,
        "legitimate": EXAMPLE_LEGITIMATE,
        "borderline": EXAMPLE_BORDERLINE
    }

    ex = examples.get(example_type, EXAMPLE_LEGITIMATE)
    return prepare_api_payload(
        transaction_id=ex["transaction_id"],
        v_features=ex["v_features"],
        amount=ex["amount"],
        time_elapsed=ex["time_elapsed"]
    )
