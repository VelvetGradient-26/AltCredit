import pandas as pd
import numpy as np

from pathlib import Path

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "ml_training_dataset_model_A_realistic_balanced_5500.csv"
)


# ============================================================
# LOAD
# ============================================================

df = pd.read_csv(DATA_PATH)

TARGET = "borrower_outcome"


# ============================================================
# FEATURES
# ============================================================

FEATURES = [
    # Lifestyle
    "age",
    "education_level",
    "employment_status",
    "monthly_income",
    "city_tier",
    "months_at_job",
    "housing",
    "rent_on_time_months",
    "digital_payment_rate",
    "education",

    # Spending
    "monthly_spend",
    "essential_pct",
    "cashflow_volatility",
    "savings_days",

    # Repayment
    "on_time_rate",
    "dti",
    "credit_util",

    # Delinquency
    "delinq_90plus",
    "delinq_60plus",
    "delinq_30plus",

    # Behaviour
    "positive_habits",
    "risk_flags"
]


X = df[FEATURES]

y = df[TARGET]


# ============================================================
# PREPROCESSING
# ============================================================

categorical_features = [
    "education_level",
    "employment_status",
    "housing",
    "education"
]

numeric_features = [
    f for f in FEATURES
    if f not in categorical_features
]


numeric_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="median")
    ),
    (
        "scaler",
        StandardScaler()
    )
])


categorical_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(strategy="most_frequent")
    ),
    (
        "onehot",
        OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=False
        )
    )
])


preprocessor = ColumnTransformer([
    (
        "numeric",
        numeric_pipeline,
        numeric_features
    ),
    (
        "categorical",
        categorical_pipeline,
        categorical_features
    )
])


# ============================================================
# MODELS
# ============================================================

logistic = Pipeline([
    (
        "preprocessor",
        preprocessor
    ),
    (
        "model",
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42
        )
    )
])


xgb_pipeline = Pipeline([
    (
        "preprocessor",
        preprocessor
    ),
    (
        "model",
        XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.035,
            min_child_weight=5,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.10,
            reg_lambda=2.0,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1
        )
    )
])


# ============================================================
# 5-FOLD CROSS VALIDATION
# ============================================================

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)


scoring = [
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc"
]


def run_cv(name, model):

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    results = cross_validate(
        model,
        X,
        y,
        cv=cv,
        scoring=scoring,
        n_jobs=-1
    )

    for metric in scoring:

        values = results[
            f"test_{metric}"
        ]

        print(
            f"{metric.upper():10s}: "
            f"{values.mean():.4f} "
            f"+/- {values.std():.4f}"
        )

    return results


logistic_results = run_cv(
    "LOGISTIC REGRESSION",
    logistic
)


xgb_results = run_cv(
    "XGBOOST",
    xgb_pipeline
)