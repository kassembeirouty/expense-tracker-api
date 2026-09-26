from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal[
    "food",
    "transport",
    "housing",
    "utilities",
    "health",
    "entertainment",
    "education",
    "shopping",
    "other",
]

# Month in the format "YYYY-MM", for example "2026-09"
Month = Annotated[str, Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ---------- Users and auth ----------

class UserCreate(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Expenses ----------

class ExpenseBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    category: Category
    spent_on: date
    note: str | None = Field(default=None, max_length=255)


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0)
    category: Category | None = None
    spent_on: date | None = None
    note: str | None = Field(default=None, max_length=255)


class ExpenseOut(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ---------- Budgets ----------

class BudgetCreate(BaseModel):
    category: Category
    month: Month
    limit_amount: float = Field(gt=0)


class BudgetUpdate(BaseModel):
    limit_amount: float = Field(gt=0)


class BudgetOut(BudgetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class BudgetStatus(BaseModel):
    id: int
    category: str
    month: str
    limit_amount: float
    spent: float
    remaining: float
    percent_used: float
    over_budget: bool


# ---------- Reports ----------

class CategorySummary(BaseModel):
    category: str
    total: float
    count: int


class Summary(BaseModel):
    total: float
    count: int
    by_category: list[CategorySummary]


class MonthlyTotal(BaseModel):
    month: str
    total: float
    count: int