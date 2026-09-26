from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (must be imported so tables are registered)
from app.database import Base, engine
from app.routers import auth, budgets, expenses, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Expense Tracker API",
    version="2.0.0",
    description=(
        "A REST API to track personal expenses with user accounts (JWT), "
        "monthly budgets, spending reports, and CSV export."
    ),
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(budgets.router)
app.include_router(reports.router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok"}