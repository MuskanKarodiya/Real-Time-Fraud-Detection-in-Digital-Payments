"""
Model Training Module

This module provides functions for training and evaluating machine learning models
for fraud detection. Includes baseline models (Logistic Regression, Random Forest)
and XGBoost with Optuna hyperparameter tuning.

Reference: project_guide.md Week 2 - Feature Engineering & Model Training
"""

import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, Any

# Scikit-learn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_curve,
    roc_auc_score,
    precision_recall_curve,
    auc
)

# XGBoost and Optuna
try:
    from xgboost import XGBClassifier
    import optuna
except ImportError:
    raise ImportError(
        "XGBoost and Optuna are required. "
        "Install with: pip install xgboost optuna"
    )


class ModelTrainer:
    """
    A class for training and evaluating fraud detection models.

    This class handles:
    - Baseline model training (Logistic Regression, Random Forest)
    - XGBoost with Optuna hyperparameter tuning
    - Model evaluation and comparison
    - Model artifact management
    """

    def __init__(self, models_dir: Optional[Path] = None, data_dir: Optional[Path] = None):
        """
        Initialize the ModelTrainer.

        Args:
            models_dir: Directory to save model artifacts
            data_dir: Directory containing processed data
        """
        self.models_dir = models_dir or Path("models")
        self.data_dir = data_dir or Path("data/processed")
        self.models_dir.mkdir(exist_ok=True)

        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None

    def load_data(self) -> None:
        """Load processed training and test data."""
        self.X_train = joblib.load(self.data_dir / "X_train.pkl")
        self.X_test = joblib.load(self.data_dir / "X_test.pkl")
        self.y_train = joblib.load(self.data_dir / "y_train.pkl")
        self.y_test = joblib.load(self.data_dir / "y_test.pkl")

        print(f"Data loaded: Train={self.X_train.shape[0]:,}, Test={self.X_test.shape[0]:,}")
        print(f"Fraud rate: Train={self.y_train.mean():.4%}, Test={self.y_test.mean():.4%}")

    def calculate_scale_pos_weight(self) -> float:
        """
        Calculate scale_pos_weight for XGBoost.

        For imbalanced datasets:
        scale_pos_weight = negative_cases / positive_cases

        Returns:
            Calculated scale_pos_weight value
        """
        neg_cases = (self.y_train == 0).sum()
        pos_cases = (self.y_train == 1).sum()
        return neg_cases / pos_cases

    def train_logistic_regression(
        self,
        max_iter: int = 1000,
        class_weight: str = "balanced",
        random_state: int = 42
    ) -> LogisticRegression:
        """
        Train Logistic Regression baseline model.

        Args:
            max_iter: Maximum iterations for convergence
            class_weight: Weighting strategy for imbalanced classes
            random_state: Random seed for reproducibility

        Returns:
            Trained LogisticRegression model
        """
        print("Training Logistic Regression...")

        model = LogisticRegression(
            class_weight=class_weight,
            max_iter=max_iter,
            random_state=random_state,
            n_jobs=-1
        )

        model.fit(self.X_train, self.y_train)
        print("Logistic Regression training completed.")

        return model

    def train_random_forest(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        class_weight: str = "balanced",
        random_state: int = 42
    ) -> RandomForestClassifier:
        """
        Train Random Forest baseline model.

        Args:
            n_estimators: Number of trees in the forest
            max_depth: Maximum depth of trees
            class_weight: Weighting strategy for imbalanced classes
            random_state: Random seed for reproducibility

        Returns:
            Trained RandomForestClassifier model
        """
        print("Training Random Forest...")

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            class_weight=class_weight,
            n_jobs=-1,
            random_state=random_state,
            verbose=0
        )

        model.fit(self.X_train, self.y_train)
        print("Random Forest training completed.")

        return model

    def create_optuna_objective(
        self,
        n_folds: int = 5,
        scale_pos_weight: Optional[float] = None
    ):
        """
        Create Optuna objective function for XGBoost tuning.

        Args:
            n_folds: Number of cross-validation folds
            scale_pos_weight: Weight for positive class (calculated if None)

        Returns:
            Objective function for Optuna optimization
        """
        if scale_pos_weight is None:
            scale_pos_weight = self.calculate_scale_pos_weight()

        def objective(trial):
            """Optuna objective function."""
            params = {
                # Tree structure
                'max_depth': trial.suggest_int('max_depth', 3, 10),

                # Learning
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 500),

                # Regularization
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),

                # Class imbalance
                'scale_pos_weight': trial.suggest_float(
                    'scale_pos_weight',
                    scale_pos_weight * 0.5,
                    scale_pos_weight * 1.5
                ),

                # Other
                'random_state': 42,
                'n_jobs': -1,
                'eval_metric': 'logloss',
                'use_label_encoder': False,
            }

            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
            xgb = XGBClassifier(**params)

            scores = cross_val_score(
                xgb, self.X_train, self.y_train,
                cv=cv, scoring='roc_auc', n_jobs=-1
            )

            return scores.mean()

        return objective

    def train_xgboost_with_optuna(
        self,
        n_trials: int = 50,
        n_folds: int = 5,
        show_progress: bool = True
    ) -> Tuple[XGBClassifier, optuna.Study]:
        """
        Train XGBoost with Optuna hyperparameter optimization.

        Args:
            n_trials: Number of Optuna trials (use 100 for production)
            n_folds: Number of cross-validation folds
            show_progress: Whether to show progress bar

        Returns:
            Tuple of (trained XGBoost model, Optuna study object)
        """
        print(f"Starting Optuna optimization ({n_trials} trials)...")

        # Create study
        study = optuna.create_study(
            direction='maximize',
            study_name='xgboost_fraud_detection'
        )

        # Run optimization
        study.optimize(
            self.create_optuna_objective(n_folds=n_folds),
            n_trials=n_trials,
            show_progress_bar=show_progress,
            n_jobs=-1
        )

        print(f"\nBest ROC-AUC: {study.best_value:.4f}")
        print("Best parameters:")
        for param, value in study.best_params.items():
            if isinstance(value, float):
                print(f"  {param}: {value:.4f}")
            else:
                print(f"  {param}: {value}")

        # Train final model with best parameters
        print("\nTraining final XGBoost model...")
        best_params = study.best_params.copy()
        best_params.update({
            'random_state': 42,
            'n_jobs': -1,
            'eval_metric': 'logloss',
            'use_label_encoder': False,
        })

        xgb_model = XGBClassifier(**best_params)
        xgb_model.fit(self.X_train, self.y_train)
        print("XGBoost training completed.")

        return xgb_model, study

    @staticmethod
    def evaluate_model(
        model,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_name: str = "Model"
    ) -> Dict[str, Any]:
        """
        Evaluate a trained model.

        Args:
            model: Trained model with predict and predict_proba methods
            X_test: Test features
            y_test: Test labels
            model_name: Name of the model for reporting

        Returns:
            Dictionary containing evaluation metrics and predictions
        """
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()

        # Calculate metrics
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        roc_auc = roc_auc_score(y_test, y_proba)

        # Print results
        print(f"\n{'='*60}")
        print(f"  {model_name} - Test Results")
        print(f"{'='*60}")
        print(f"\nConfusion Matrix:")
        print(f"                Predicted")
        print(f"               Legit  Fraud")
        print(f"Actual Legit   {tn:5d}  {fp:5d}")
        print(f"       Fraud   {fn:5d}  {tp:5d}")

        print(f"\nMetrics:")
        print(f"  Fraud Recall:     {recall:.4%}")
        print(f"  Fraud Precision:  {precision:.4%}")
        print(f"  F1-Score:         {f1:.4f}")
        print(f"  ROC-AUC:          {roc_auc:.4f}")

        return {
            'y_pred': y_pred,
            'y_proba': y_proba,
            'confusion_matrix': cm,
            'recall': recall,
            'precision': precision,
            'f1': f1,
            'roc_auc': roc_auc
        }

    def compare_models(
        self,
        models: Dict[str, Any],
        save_path: Optional[Path] = None
    ) -> pd.DataFrame:
        """
        Compare multiple models.

        Args:
            models: Dictionary of model_name -> model_object
            save_path: Optional path to save comparison table

        Returns:
            DataFrame with comparison metrics
        """
        results = []

        for name, model in models.items():
            metrics = self.evaluate_model(model, self.X_test, self.y_test, name)
            results.append({
                'Model': name,
                'ROC-AUC': metrics['roc_auc'],
                'Fraud Recall': metrics['recall'],
                'Fraud Precision': metrics['precision'],
                'F1-Score': metrics['f1']
            })

        comparison_df = pd.DataFrame(results)

        print(f"\n{'='*70}")
        print("              MODEL COMPARISON")
        print(f"{'='*70}")
        print(comparison_df.to_string(index=False))
        print(f"{'='*70}")

        # Check KPIs
        print(f"\nKPI Check (project_guide targets):")
        for _, row in comparison_df.iterrows():
            print(f"\n{row['Model']}:")
            print(f"  ROC-AUC >= 0.95:    {row['ROC-AUC']:.4f}  {'PASS' if row['ROC-AUC'] >= 0.95 else 'FAIL'}")
            print(f"  Recall >= 0.90:     {row['Fraud Recall']:.4f}  {'PASS' if row['Fraud Recall'] >= 0.90 else 'FAIL'}")
            print(f"  Precision >= 0.85:  {row['Fraud Precision']:.4f}  {'PASS' if row['Fraud Precision'] >= 0.85 else 'FAIL'}")

        if save_path:
            comparison_df.to_csv(save_path, index=False)
            print(f"\nComparison saved to: {save_path}")

        return comparison_df

    def save_model(
        self,
        model: Any,
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save a trained model artifact.

        Args:
            model: Trained model object
            model_name: Name for the model file
            metadata: Optional metadata dictionary

        Returns:
            Path to saved model file
        """
        timestamp = datetime.now().isoformat()

        # Save model
        model_path = self.models_dir / f"{model_name}.pkl"
        joblib.dump(model, model_path)

        # Save metadata
        if metadata is not None:
            metadata['saved_at'] = timestamp
            metadata_path = self.models_dir / f"{model_name}_metadata.json"

            import json
            # Convert non-serializable items
            serializable_metadata = {}
            for k, v in metadata.items():
                try:
                    json.dumps({k: v})
                    serializable_metadata[k] = v
                except TypeError:
                    serializable_metadata[k] = str(v)

            with open(metadata_path, 'w') as f:
                json.dump(serializable_metadata, f, indent=2)

        print(f"Model saved: {model_path}")
        return model_path

    def plot_roc_curves(
        self,
        models: Dict[str, Any],
        save_path: Optional[Path] = None
    ) -> None:
        """
        Plot ROC curves for multiple models.

        Args:
            models: Dictionary of model_name -> model_object
            save_path: Optional path to save the plot
        """
        plt.figure(figsize=(10, 8))

        for name, model in models.items():
            y_proba = model.predict_proba(self.X_test)[:, 1]
            fpr, tpr, _ = roc_curve(self.y_test, y_proba)
            roc_auc = auc(fpr, tpr)
            plt.plot(fpr, tpr, label=f'{name} (AUC = {roc_auc:.4f})', linewidth=2)

        plt.plot([0, 1], [0, 1], 'k--', label='Random (AUC = 0.5000)')
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate (Recall)', fontsize=12)
        plt.title('ROC Curves - Model Comparison', fontsize=14)
        plt.legend(loc='lower right', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xlim([0, 1])
        plt.ylim([0, 1.05])
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"ROC curves saved to: {save_path}")

        plt.show()


def main():
    """
    Main training pipeline.

    Follows project_guide.md Week 2 workflow:
    - Day 4: Train baseline models
    - Day 5: Train XGBoost with Optuna
    - Day 6: Full evaluation and comparison
    - Day 7: Save final model
    """
    print("="*70)
    print("     FRAUD DETECTION - MODEL TRAINING PIPELINE")
    print("     Following: project_guide.md Week 2")
    print("="*70)

    # Initialize trainer
    trainer = ModelTrainer()

    # Load data
    print("\n[1/6] Loading processed data...")
    trainer.load_data()

    # Train baseline models
    print("\n[2/6] Training baseline models...")
    logreg_model = trainer.train_logistic_regression()
    rf_model = trainer.train_random_forest()

    # Train XGBoost with Optuna
    print("\n[3/6] Training XGBoost with Optuna (50 trials)...")
    xgb_model, study = trainer.train_xgboost_with_optuna(n_trials=50)

    # Compare all models
    print("\n[4/6] Comparing models...")
    models = {
        'Logistic Regression': logreg_model,
        'Random Forest': rf_model,
        'XGBoost (Optuna)': xgb_model
    }
    comparison = trainer.compare_models(models)

    # Plot ROC curves
    print("\n[5/6] Plotting ROC curves...")
    images_dir = Path("docs/images")
    images_dir.mkdir(parents=True, exist_ok=True)
    trainer.plot_roc_curves(models, save_path=images_dir / "all_models_roc_curves.png")

    # Save models
    print("\n[6/6] Saving models...")
    trainer.save_model(logreg_model, "logreg_baseline", {
        "type": "LogisticRegression",
        "week": "2",
        "day": "4"
    })
    trainer.save_model(rf_model, "rf_baseline", {
        "type": "RandomForest",
        "week": "2",
        "day": "4"
    })
    trainer.save_model(xgb_model, "xgboost_optuna", {
        "type": "XGBoost",
        "week": "2",
        "day": "5",
        "optuna_trials": len(study.trials),
        "best_cv_score": study.best_value
    })

    # Save Optuna study
    joblib.dump(study, trainer.models_dir / "optuna_study.pkl")

    print("\n" + "="*70)
    print("     TRAINING PIPELINE COMPLETED")
    print("="*70)
    print("\nNext steps (project_guide Week 2):")
    print("  Day 6: Address class imbalance, compute full evaluation")
    print("  Day 7: Select final model and create model card")
    print("="*70)


if __name__ == "__main__":
    main()
