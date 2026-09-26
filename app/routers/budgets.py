from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _get_or_404(db: Session, user: models.User, budget_id: int) -> models.Budget:
    budget = crud.get_budget(db, user.id, budget_id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


@router.post("", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    data: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = crud.create_budget(db, user.id, data)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A budget for this category and month already exists",
        )
    return budget


@router.get("", response_model=list[schemas.BudgetStatus])
def list_budgets(
    month: schemas.Month | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budgets = crud.list_budgets(db, user.id, month)
    return [crud.get_budget_status(db, budget) for budget in budgets]


@router.get("/{budget_id}", response_model=schemas.BudgetStatus)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = _get_or_404(db, user, budget_id)
    return crud.get_budget_status(db, budget)


@router.patch("/{budget_id}", response_model=schemas.BudgetOut)
def update_budget(
    budget_id: int,
    data: schemas.BudgetUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = _get_or_404(db, user, budget_id)
    return crud.update_budget(db, budget, data)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    budget = _get_or_404(db, user, budget_id)
    crud.delete_budget(db, budget)
    return Response(status_code=status.HTTP_204_NO_CONTENT)