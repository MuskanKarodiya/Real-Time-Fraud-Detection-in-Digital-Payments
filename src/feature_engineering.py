"""
Feature Engineering Module

This module provides functions for feature transformation and engineering
for fraud detection models.

Reference: project_guide.md Week 2 - Feature Engineering & Model Development

Feature Engineering Strategy:
- Amount: StandardScaler normalization (zero mean, unit variance)
- Time: Convert to hour_of_day (cyclic encoding) and is_night_transaction flag
- V1-V28: Already PCA-transformed; apply correlation analysis
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from pathlib import Path
from typing import Tuple, Optional
import joblib


def extract_time_features(df: pd.DataFrame, time_col: str = 'time_elapsed') -> pd.DataFrame:
    """
    Extract time-based features from elapsed time.

    Per project_guide.md: Convert to hour_of_day (cyclic encoding) and is_night_transaction flag.

    Args:
        df: Input dataframe
        time_col: Name of the time elapsed column (default: 'time_elapsed')

    Returns:
        Dataframe with added time features (hour, day, is_night)
    """
    df = df.copy()

    # Extract hour (0-23) from elapsed time
    df['hour'] = ((df[time_col] / 3600) % 24).astype(int)

    # Extract day (dataset covers 2 days)
    df['day'] = (df[time_col] // 86400).astype(int)

    # Night risk flag: Transactions between 00:00-05:00 local time
    # Per project_guide: "Night risk flag: Transactions between 00:00-05:00 local time"
    df['is_night'] = ((df['hour'] >= 0) & (df['hour'] < 5)).astype(int)

    return df


def add_cyclic_encoding(df: pd.DataFrame, col: str = 'hour') -> pd.DataFrame:
    """
    Add cyclic encoding for circular features like hour of day.

    Per project_guide.md: Use cyclic encoding for time features.
    This preserves the fact that hour 23 and hour 0 are adjacent (midnight).

    Args:
        df: Input dataframe
        col: Column name to encode (default: 'hour')

    Returns:
        Dataframe with cyclic encoded columns (col_sin, col_cos)
    """
    df = df.copy()

    df[f'{col}_sin'] = np.sin(2 * np.pi * df[col] / 24)
    df[f'{col}_cos'] = np.cos(2 * np.pi * df[col] / 24)

    return df


def scale_amount(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    col: str = 'amount',
    scaler_path: Optional[Path] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, StandardScaler]:
    """
    Scale the amount feature using StandardScaler.

    Per project_guide.md: "Amount: StandardScaler normalization (zero mean, unit variance)"

    IMPORTANT: Fit on training data only to prevent data leakage.

    Args:
        df_train: Training dataframe
        df_test: Test dataframe
        col: Column name to scale
        scaler_path: Optional path to save fitted scaler

    Returns:
        Tuple of (train_df, test_df, fitted_scaler)
    """
    df_train = df_train.copy()
    df_test = df_test.copy()

    scaler = StandardScaler()

    # Fit on training data only
    df_train[f'{col}_scaled'] = scaler.fit_transform(df_train[[col]])

    # Transform both train and test
    df_test[f'{col}_scaled'] = scaler.transform(df_test[[col]])

    # Save scaler if path provided
    if scaler_path:
        scaler_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, scaler_path)

    return df_train, df_test, scaler


def remove_correlated_features(
    df: pd.DataFrame,
    features: list,
    threshold: float = 0.95
) -> list:
    """
    Apply correlation analysis to remove redundant features.

    Per project_guide.md: "V1-V28: Already PCA-transformed; apply correlation analysis
    to remove redundant features (|r| > 0.95)"

    Args:
        df: Input dataframe
        features: List of feature columns to check
        threshold: Correlation threshold for removal (default: 0.95)

    Returns:
        List of features to keep (removes highly correlated ones)
    """
    # Compute correlation matrix
    corr_matrix = df[features].corr().abs()

    # Find highly correlated pairs
    upper_triangle = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    )

    # Identify features to drop
    to_drop = [column for column in upper_triangle.columns
                if any(upper_triangle[column] > threshold)]

    features_to_keep = [f for f in features if f not in to_drop]

    print(f"Correlation analysis: Removed {len(to_drop)} highly correlated features")
    print(f"Features kept: {len(features_to_keep)}")

    return features_to_keep


def engineer_features(
    df: pd.DataFrame,
    fit_scaler: bool = True,
    scaler: Optional[StandardScaler] = None
) -> Tuple[pd.DataFrame, Optional[StandardScaler]]:
    """
    Apply complete feature engineering pipeline.

    Pipeline per project_guide.md Week 2:
    1. Extract time features (hour, is_night flag)
    2. Apply cyclic encoding for hour
    3. Scale amount feature

    Args:
        df: Input dataframe with raw features (V1-V28, amount, time_elapsed)
        fit_scaler: Whether to fit a new scaler (True for train data)
        scaler: Pre-fitted scaler (for test data)

    Returns:
        Tuple of (engineered_df, scaler)
    """
    df = df.copy()

    # Step 1: Extract time features
    df = extract_time_features(df)

    # Step 2: Add cyclic encoding for hour
    df = add_cyclic_encoding(df, 'hour')

    # Step 3: Scale amount (if amount column exists)
    if 'amount' in df.columns:
        if fit_scaler:
            scaler = StandardScaler()
            df['amount_scaled'] = scaler.fit_transform(df[['amount']])
        elif scaler is not None:
            df['amount_scaled'] = scaler.transform(df[['amount']])

    return df, scaler
