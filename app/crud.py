from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.security import hash_password, verify_password


# ---------- Helpers ----------

def month_range(month: str) -> tuple[date, date]:
    """Return (first day of month, first day of next month) for 'YYYY-MM'."""
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


def _apply_filters(
    stmt,
    user_id: int,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    stmt = stmt.where(models.Expense.user_id == user_id)
    if category:
        stmt = stmt.where(models.Expense.category == category)
    if start_date:
        stmt = stmt.where(models.Expense.spent_on >= start_date)
    if end_date:
        stmt = stmt.where(models.Expense.spent_on <= end_date)
    return stmt


# ---------- Users ----------

def get_user(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)


def get_user_by_email(db: Session, email: str) -> models.User | None:
    stmt = select(models.User).where(models.User.email == email.strip().lower())
    return db.scalars(stmt).first()


def create_user(db: Session, data: schemas.UserCreate) -> models.User:
    user = models.User(email=data.email, hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


# ---------- Expenses ----------

def create_expense(db: Session, user_id: int, data: schemas.ExpenseCreate) -> models.Expense:
    expense = models.Expense(user_id=user_id, **data.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def get_expense(db: Session, user_id: int, expense_id: int) -> models.Expense | None:
    stmt = select(models.Expense).where(
        models.Expense.id == expense_id,
        models.Expense.user_id == user_id,
    )
    return db.scalars(stmt).first()


def list_expenses(
    db: Session,
    user_id: int,
    category: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[models.Expense]:
    stmt = _apply_filters(select(models.Expense), user_id, category, start_date, end_date)
    stmt = stmt.order_by(models.Expense.spent_on.desc(), models.Expense.id.desc())
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def update_expense(
    db: Session, expense: models.Expense, data: schemas.ExpenseUpdate
) -> models.Expense:
    for field, value in data.model_dump(exclude_unset=True).items():
        # Only "note" is allowed to be cleared to null
        if value is None and field != "note":
            continue
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, expense: models.Expense) -> None:
    db.delete(expense)
    db.commit()


# ---------- Reports ----------

def get_summary(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> schemas.Summary:
    stmt = select(
        models.Expense.category,
        func.sum(models.Expense.amount),
        func.count(models.Expense.id),
    )
    stmt = _apply_filters(stmt, user_id, None, start_date, end_date)
    stmt = stmt.group_by(models.Expense.category)
    stmt = stmt.order_by(func.sum(models.Expense.amount).desc())

    by_category = [
        schemas.CategorySummary(category=cat, total=round(total, 2), count=count)
        for cat, total, count in db.execute(stmt).all()
    ]
    return schemas.Summary(
        total=round(sum(item.total for item in by_category), 2),
        count=sum(item.count for item in by_category),
        by_category=by_category,
    )


def get_monthly_totals(
    db: Session, user_id: int, year: int | None = None
) -> list[schemas.MonthlyTotal]:
    stmt = select(models.Expense.spent_on, models.Expense.amount).where(
        models.Expense.user_id == user_id
    )
    if year is not None:
        stmt = stmt.where(
            models.Expense.spent_on >= date(year, 1, 1),
            models.Expense.spent_on <= date(year, 12, 31),
        )

    totals: dict[str, list] = defaultdict(lambda: [0.0, 0])
    for spent_on, amount in db.execute(stmt).all():
        key = spent_on.strftime("%Y-%m")
        totals[key][0] += amount
        totals[key][1] += 1

    return [
        schemas.MonthlyTotal(month=month, total=round(total, 2), count=count)
        for month, (total, count) in sorted(totals.items())
    ]


# ---------- Budgets ----------

def create_budget(
    db: Session, user_id: int, data: schemas.BudgetCreate
) -> models.Budget | None:
    """Return the new budget, or None if one already exists for that category and month."""
    budget = models.Budget(user_id=user_id, **data.model_dump())
    db.add(budget)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return None
    db.refresh(budget)
    return budget


def get_budget(db: Session, user_id: int, budget_id: int) -> models.Budget | None:
    stmt = select(models.Budget).where(
        models.Budget.id == budget_id,
        models.Budget.user_id == user_id,
    )
    return db.scalars(stmt).first()


def list_budgets(db: Session, user_id: int, month: str | None = None) -> list[models.Budget]:
    stmt = select(models.Budget).where(models.Budget.user_id == user_id)
    if month:
        stmt = stmt.where(models.Budget.month == month)
    stmt = stmt.order_by(models.Budget.month.desc(), models.Budget.category)
    return list(db.scalars(stmt).all())


def update_budget(
    db: Session, budget: models.Budget, data: schemas.BudgetUpdate
) -> models.Budget:
    budget.limit_amount = data.limit_amount
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget: models.Budget) -> None:
    db.delete(budget)
    db.commit()


def get_budget_status(db: Session, budget: models.Budget) -> schemas.BudgetStatus:
    start, end = month_range(budget.month)
    stmt = select(func.coalesce(func.sum(models.Expense.amount), 0.0)).where(
        models.Expense.user_id == budget.user_id,
        models.Expense.category == budget.category,
        models.Expense.spent_on >= start,
        models.Expense.spent_on < end,
    )
    spent = round(float(db.scalar(stmt)), 2)
    remaining = round(budget.limit_amount - spent, 2)
    percent_used = round(spent / budget.limit_amount * 100, 1)

    return schemas.BudgetStatus(
        id=budget.id,
        category=budget.category,
        month=budget.month,
        limit_amount=budget.limit_amount,
        spent=spent,
        remaining=remaining,
        percent_used=percent_used,
        over_budget=spent > budget.limit_amount,
    )