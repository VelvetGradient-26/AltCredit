import joblib
import pandas as pd

from pathlib import Path


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "xgboost_credit_model.joblib"
)


# ============================================================
# LOAD MODEL
# ============================================================

model_bundle = joblib.load(
    MODEL_PATH
)

model = model_bundle["model"]
preprocessor = model_bundle["preprocessor"]
features = model_bundle["features"]


# ============================================================
# RISK TIER
# ============================================================

def get_risk_tier(score):

    if score >= 750:
        return "Prime / Low Risk"

    elif score >= 650:
        return "Near-Prime / Medium Risk"

    elif score >= 550:
        return "Sub-Prime / Fair"

    return "High Risk / Poor"


# ============================================================
# PREDICTION
# ============================================================

def predict_credit_score(user_data):

    """
    user_data:
        Dictionary containing applicant features.
    """

    # Convert dictionary → DataFrame

    input_df = pd.DataFrame(
        [user_data]
    )

    # Ensure exact feature order

    input_df = input_df[
        features
    ]

    # Preprocess

    X = preprocessor.transform(
        input_df
    )

    # Predict PD

    probability_of_default = (

        model
        .predict_proba(X)[0][1]

    )

    # Convert PD → 0-1000 score

    credit_score = round(
        1000 * (
            1 - probability_of_default
        )
    )

    # Keep score inside range

    credit_score = max(
        0,
        min(1000, credit_score)
    )

    # Risk tier

    risk_tier = get_risk_tier(
        credit_score
    )

    return {

        "probability_of_default":
            round(
                float(probability_of_default),
                4
            ),

        "credit_score":
            credit_score,

        "risk_tier":
            risk_tier

    }