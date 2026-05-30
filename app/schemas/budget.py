
from pydantic import BaseModel, Field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

class BudgetBase(BaseModel):
    category: str
    budget_amount: Decimal
    start_date: date = Field(default_factory=date.today)
    end_date: date = Field(default_factory=lambda: date.today() + timedelta(days=30))
    past_spending: Optional[Decimal] = None
    reduction_percent: Optional[Decimal] = None

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    budget_amount: Decimal

class Budget(BudgetBase):
    id: str
    user_id: str
    start_date: date
    end_date: date
    remaining_budget: Optional[Decimal] = None
    past_spending: Optional[Decimal] = None
    reduction_percent: Optional[Decimal] = None
    is_successful: Optional[bool] = None

    class Config:
        from_attributes = True


class PastSpendingOption(BaseModel):
    reduction_percent: int
    estimated_savings: float
    new_budget_amount: float
    label: str


class PastSpendingOptionsResponse(BaseModel):
    category: str
    past_spending: float
    options: list[PastSpendingOption]


class BudgetGoalMicroAlert(BaseModel):
    level: str
    title: str
    message: str


class BudgetGoalStatus(BaseModel):
    budget_id: str
    category: str
    budget_amount: float
    current_spend: float
    remaining_budget: float
    progress_percent: float
    days_left: int
    burn_rate_per_day: float
    projected_period_spend: float
    predicted_to_exceed: bool
    alerts: list[BudgetGoalMicroAlert]


class BudgetPredictionDriver(BaseModel):
    factor: str
    impact: str
    detail: str


class BudgetGoalPredictionExplanation(BaseModel):
    budget_id: str
    category: str
    risk_level: str
    risk_probability: float
    short_explanation: str
    drivers: list[BudgetPredictionDriver]


class BudgetGoalSimulationRequest(BaseModel):
    reduction_percent: float = Field(default=0, ge=0, le=100)
    absolute_cut: float = Field(default=0, ge=0)


class BudgetGoalSimulationResult(BaseModel):
    budget_id: str
    category: str
    baseline_projected_spend: float
    simulated_projected_spend: float
    projected_savings: float
    baseline_predicted_to_exceed: bool
    simulated_predicted_to_exceed: bool
    simulated_remaining_budget: float


class BudgetGoalSuggestion(BaseModel):
    suggestion_type: str
    title: str
    message: str
    estimated_savings: float
    priority: str


class BudgetGoalSuggestionsResponse(BaseModel):
    budget_id: str
    category: str
    suggestions: list[BudgetGoalSuggestion]


class BudgetGoalAdaptiveAdjustment(BaseModel):
    budget_id: str
    category: str
    recommended_budget_amount: float
    adjustment_percent: float
    reason: str


class BudgetGoalPeriodReview(BaseModel):
    budget_id: str
    category: str
    period_start: date
    period_end: date
    is_period_closed: bool
    achieved: bool
    budget_amount: float
    total_spent: float
    savings_or_overrun: float
    summary: str
    next_recommended_budget: float
