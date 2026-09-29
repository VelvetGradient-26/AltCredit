from typing import Any, Dict

from services import score_config as c


class AltCreditRuleEngine:
    def __init__(self, config_module=c):
        self.cfg = config_module

    def evaluate_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        breakdown = {}

        # ------------------------------------------------------------------
        # 1. LIFESTYLE PILLAR
        # ------------------------------------------------------------------
        # 1.1 Employment Stability
        months_at_job = user_data["months_at_job"]
        p_1_1 = 0
        for tier in self.cfg.EMPLOYMENT_STABILITY_CONFIG["tiers"]:
            if months_at_job >= tier["min_months"]:
                p_1_1 = tier["points"]
                break
        breakdown["1.1_employment_stability"] = {
            "score": p_1_1,
            "max": 150,
            "val": f"{months_at_job} months",
        }

        # 1.2 Housing Status
        housing = str(user_data["housing"]).lower()
        rent_on_time = user_data["rent_on_time_months"]
        h_cfg = self.cfg.HOUSING_STATUS_CONFIG
        p_1_2 = h_cfg["none_points"]
        if housing == "owner":
            p_1_2 = h_cfg["owner_points"]
        elif housing == "rent":
            if rent_on_time >= h_cfg["rent_ontime_min_months"]:
                p_1_2 = h_cfg["rent_ontime_points"]
            else:
                p_1_2 = h_cfg["rent_short_points"]
        breakdown["1.2_housing_status"] = {
            "score": p_1_2,
            "max": 80,
            "val": f"housing={housing}, rent_on_time={rent_on_time}mo",
        }

        # 1.3 Digital Footprint
        digital_rate = user_data["digital_payment_rate"]
        p_1_3 = 0
        for tier in self.cfg.DIGITAL_FOOTPRINT_CONFIG["tiers"]:
            if digital_rate >= tier["min_rate"]:
                p_1_3 = tier["points"]
                break
        breakdown["1.3_digital_footprint"] = {
            "score": p_1_3,
            "max": 70,
            "val": f"{digital_rate * 100:.1f}%",
        }

        # 1.4 Education Level (Uses 'education_level' directly from merged_data.json)
        edu_str = str(user_data["education_level"]).lower()
        edu_map = self.cfg.EDUCATION_LEVEL_CONFIG["mapping"]

        p_1_4 = 0
        for k, pts in edu_map.items():
            if k in edu_str:
                p_1_4 = pts
                break

        breakdown["1.4_education_level"] = {"score": p_1_4, "max": 50, "val": edu_str}

        lifestyle_total = p_1_1 + p_1_2 + p_1_3 + p_1_4

        # ------------------------------------------------------------------
        # 2. SPENDING BEHAVIOR PILLAR
        # ------------------------------------------------------------------
        # 2.1 Spend-to-Income Ratio
        income = user_data["monthly_income"]
        spend = user_data["monthly_spend"]
        spend_ratio = (spend / income) if income > 0 else 1.0
        p_2_1 = 0
        for tier in self.cfg.SPEND_TO_INCOME_CONFIG["tiers"]:
            if spend_ratio <= tier["max_ratio"]:
                p_2_1 = tier["points"]
                break
        breakdown["2.1_spend_to_income_ratio"] = {
            "score": p_2_1,
            "max": 120,
            "val": f"{spend_ratio * 100:.1f}%",
        }

        # 2.2 Expense Diversity
        essential_pct = user_data["essential_pct"]
        p_2_2 = 0
        for tier in self.cfg.EXPENSE_DIVERSITY_CONFIG["tiers"]:
            if essential_pct >= tier["min_essential_pct"]:
                p_2_2 = tier["points"]
                break
        breakdown["2.2_expense_diversity"] = {
            "score": p_2_2,
            "max": 80,
            "val": f"{essential_pct * 100:.1f}%",
        }

        # 2.3 Cash-flow Volatility
        volatility = user_data["cashflow_volatility"]
        p_2_3 = 0
        for tier in self.cfg.CASHFLOW_VOLATILITY_CONFIG["tiers"]:
            if volatility <= tier["max_volatility"]:
                p_2_3 = tier["points"]
                break
        breakdown["2.3_cashflow_volatility"] = {
            "score": p_2_3,
            "max": 70,
            "val": f"{volatility * 100:.1f}%",
        }

        # 2.4 Savings / Emergency Fund
        savings_days = user_data["savings_days"]
        p_2_4 = 0
        for tier in self.cfg.SAVINGS_BUFFER_CONFIG["tiers"]:
            if savings_days >= tier["min_days"]:
                p_2_4 = tier["points"]
                break
        breakdown["2.4_savings_emergency_fund"] = {
            "score": p_2_4,
            "max": 80,
            "val": f"{savings_days} days",
        }

        spending_total = p_2_1 + p_2_2 + p_2_3 + p_2_4

        # ------------------------------------------------------------------
        # 3. REPAYMENT DISCIPLINE PILLAR
        # ------------------------------------------------------------------
        # 3.1 On-time Payment Rate
        on_time_rate = user_data["on_time_rate"]
        p_3_1 = 0
        for tier in self.cfg.ONTIME_PAYMENT_CONFIG["tiers"]:
            if on_time_rate >= tier["min_rate"]:
                p_3_1 = tier["points"]
                break
        breakdown["3.1_ontime_payment_rate"] = {
            "score": p_3_1,
            "max": 200,
            "val": f"{on_time_rate * 100:.1f}%",
        }

        # 3.2 Debt-to-Income Ratio
        dti = user_data["dti"]
        p_3_2 = 0
        for tier in self.cfg.DEBT_TO_INCOME_CONFIG["tiers"]:
            if dti <= tier["max_dti"]:
                p_3_2 = tier["points"]
                break
        breakdown["3.2_debt_to_income"] = {
            "score": p_3_2,
            "max": 120,
            "val": f"{dti * 100:.1f}%",
        }

        # 3.3 Credit Utilization
        credit_util = user_data["credit_util"]
        p_3_3 = 0
        for tier in self.cfg.CREDIT_UTILIZATION_CONFIG["tiers"]:
            if credit_util <= tier["max_util"]:
                p_3_3 = tier["points"]
                break
        breakdown["3.3_credit_utilization"] = {
            "score": p_3_3,
            "max": 100,
            "val": f"{credit_util * 100:.1f}%",
        }

        # 3.4 Recent Delinquency Severity
        d_cfg = self.cfg.DELINQUENCY_SEVERITY_CONFIG
        if user_data["delinq_90plus"] == 1:
            p_3_4 = d_cfg["miss_90_plus_points"]
            delinq_desc = "90+ Days Late"
        elif user_data["delinq_60plus"] == 1:
            p_3_4 = d_cfg["miss_60_points"]
            delinq_desc = "60-89 Days Late"
        elif user_data["delinq_30plus"] == 1:
            p_3_4 = d_cfg["miss_30_points"]
            delinq_desc = "30-59 Days Late"
        else:
            p_3_4 = d_cfg["clean_history_points"]
            delinq_desc = "No Delinquency"

        breakdown["3.4_delinquency_severity"] = {
            "score": p_3_4,
            "max": 150,
            "val": delinq_desc,
        }

        repayment_total = p_3_1 + p_3_2 + p_3_3 + p_3_4

        # ------------------------------------------------------------------
        # 4. BONUS & PENALTY ADJUSTMENTS
        # ------------------------------------------------------------------
        bp_cfg = self.cfg.BONUS_PENALTY_CONFIG

        pos_habits = user_data["positive_habits"]
        bonus_pts = min(
            pos_habits * bp_cfg["points_per_positive_habit"],
            bp_cfg["max_positive_bonus"],
        )

        risk_flags = user_data["risk_flags"]
        penalty_pts = min(
            risk_flags * bp_cfg["penalty_per_risk_flag"], bp_cfg["max_risk_penalty"]
        )

        net_adjustments = bonus_pts - penalty_pts
        breakdown["4.1_positive_habits"] = {
            "score": bonus_pts,
            "max": bp_cfg["max_positive_bonus"],
            "val": f"{pos_habits} habits",
        }
        breakdown["4.2_risk_flags"] = {
            "score": -penalty_pts,
            "max": -bp_cfg["max_risk_penalty"],
            "val": f"{risk_flags} flags",
        }

        # Raw Score Capping
        raw_score = lifestyle_total + spending_total + repayment_total + net_adjustments
        final_score = max(
            self.cfg.MIN_CREDIT_SCORE, min(self.cfg.MAX_CREDIT_SCORE, raw_score)
        )

        # Risk Tier Categorization
        risk_tier = "High Risk / Poor"
        for t in self.cfg.RISK_TIERS:
            if final_score >= t["min_score"]:
                risk_tier = t["label"]
                break

        return {
            "user_id": user_data["user_id"],
            "applicant_id": user_data["applicant_id"],
            "final_credit_score": final_score,
            "risk_tier": risk_tier,
            "pillar_breakdown": {
                "lifestyle_score": lifestyle_total,
                "spending_behavior_score": spending_total,
                "repayment_discipline_score": repayment_total,
                "net_adjustments": net_adjustments,
            },
            "subfactor_breakdown": breakdown,
        }


engine = AltCreditRuleEngine()
