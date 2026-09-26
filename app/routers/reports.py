import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.deps import check_date_range, get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=schemas.Summary)
def get_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_date_range(start_date, end_date)
    return crud.get_summary(db, user.id, start_date, end_date)


@router.get("/monthly", response_model=list[schemas.MonthlyTotal])
def get_monthly_totals(
    year: int | None = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return crud.get_monthly_totals(db, user.id, year)


@router.get("/export.csv")
def export_csv(
    category: schemas.Category | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    check_date_range(start_date, end_date)
    expenses = crud.list_expenses(
        db, user.id, category, start_date, end_date, skip=0, limit=100_000
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "title", "amount", "category", "spent_on", "note"])
    for e in expenses:
        writer.writerow(
            [e.id, e.title, e.amount, e.category, e.spent_on.isoformat(), e.note or ""]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="expenses.csv"'},
    )
    