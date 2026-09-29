from engines.prediction_engine import (
    predict_credit_score
)


user = {

    "user_id": "USR_015",
    "age": 22,
    "education_level": "Master's",
    "employment_status": "Employed",
    "monthly_income": 1582,
    "city_tier": 1,
    "applicant_id": "f0bb65ec-a06b-4016-987d-468bd24b862e",
    "months_at_job": 35,
    "housing": "none",
    "rent_on_time_months": 0,
    "digital_payment_rate": 0.4,
    "education": "master",
    "monthly_spend": 949,
    "essential_pct": 0.52,
    "cashflow_volatility": 0.17,
    "savings_days": 15,
    "on_time_rate": 0.69,
    "dti": 0.57,
    "credit_util": 0.72,
    "delinq_90plus": 0,
    "delinq_60plus": 0,
    "delinq_30plus": 0,
    "positive_habits": 1,
    "risk_flags": 1

}


result = predict_credit_score(
    user
)


print(result)