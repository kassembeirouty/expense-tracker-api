# Expense Tracker API

![Tests](https://github.com/<Kassem Beyrouty>/expense-tracker-api/actions/workflows/tests.yml/badge.svg)

A secure, multi-user REST API for tracking personal expenses, built with **FastAPI**, **SQLAlchemy 2**, and **SQLite**. Users register and log in with **JWT authentication**, record expenses, set **monthly budgets per category**, and get **spending reports**. Each user's data is fully isolated from other users.

The project includes **51 automated tests**, a **Docker** setup, and a **GitHub Actions** pipeline that runs the tests on every push.

## Features

**Authentication**
- User registration and login with JWT access tokens
- Passwords hashed with PBKDF2-SHA256 and a random salt (never stored in plain text)
- Emails normalized (case-insensitive), duplicate accounts rejected
- Login errors don't reveal whether an email is registered

**Expenses**
- Create, read, update (partial), and delete expenses
- Validation: positive amounts, fixed categories, length limits
- Filter by category and date range, with pagination
- Users can only access their own expenses

**Budgets**
- Set a spending limit per category per month
- Live budget status: amount spent, remaining, percent used, over-budget flag
- Correct month boundaries, including December → January

**Reports**
- Spending summary by category (optionally within a date range)
- Monthly spending trends (optionally for one year)
- CSV export (opens in Excel)

**Engineering**
- Modular structure with separate routers, schemas, CRUD layer, and security module
- 51 tests covering auth, validation, business logic, and data isolation between users
- Dockerfile running as a non-root user
- Continuous integration with GitHub Actions

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.14 | Language |
| FastAPI | Web framework |
| SQLAlchemy 2 | ORM / database access |
| SQLite | Database |
| Pydantic 2 | Data validation |
| PyJWT | JWT tokens |
| Pytest | Testing |
| Docker | Containerization |
| GitHub Actions | CI pipeline |

## Project Structure

```
expense-tracker-api/
├── app/
│   ├── routers/
│   │   ├── auth.py        # Register, login, current user
│   │   ├── expenses.py    # Expense CRUD
│   │   ├── budgets.py     # Budgets and budget status
│   │   └── reports.py     # Summary, monthly trends, CSV export
│   ├── crud.py            # Database operations
│   ├── database.py        # Database connection and session
│   ├── deps.py            # Shared dependencies (current user, validation)
│   ├── main.py            # App setup
│   ├── models.py          # Database tables (User, Expense, Budget)
│   ├── schemas.py         # Request/response validation
│   └── security.py        # Password hashing and JWT
├── tests/
│   ├── conftest.py        # Shared fixtures (test DB, login helper)
│   ├── test_auth.py
│   ├── test_budgets.py
│   ├── test_expenses.py
│   └── test_reports.py
├── .github/workflows/tests.yml
├── Dockerfile
└── requirements.txt
```

## Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/<Kassem Beyrouty>/expense-tracker-api.git
cd expense-tracker-api

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive documentation. Register a user, click **Authorize**, and log in with your email and password to try the protected endpoints.

### Run with Docker

```bash
docker build -t expense-tracker-api .
docker run -p 8000:8000 -e SECRET_KEY=your-long-random-secret expense-tracker-api
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | development key | Secret used to sign JWT tokens. **Set this in production.** |
| `DATABASE_URL` | `sqlite:///./expenses.db` | Database connection string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Health check |
| POST | `/auth/register` | No | Create an account |
| POST | `/auth/login` | No | Log in, returns a JWT token |
| GET | `/auth/me` | Yes | Current user |
| POST | `/expenses` | Yes | Create an expense |
| GET | `/expenses` | Yes | List expenses (`category`, `start_date`, `end_date`, `skip`, `limit`) |
| GET | `/expenses/{id}` | Yes | Get one expense |
| PATCH | `/expenses/{id}` | Yes | Update part of an expense |
| DELETE | `/expenses/{id}` | Yes | Delete an expense |
| POST | `/budgets` | Yes | Create a monthly budget |
| GET | `/budgets` | Yes | List budgets with status (`month`) |
| GET | `/budgets/{id}` | Yes | Budget status |
| PATCH | `/budgets/{id}` | Yes | Change the budget limit |
| DELETE | `/budgets/{id}` | Yes | Delete a budget |
| GET | `/reports/summary` | Yes | Spending per category (`start_date`, `end_date`) |
| GET | `/reports/monthly` | Yes | Spending per month (`year`) |
| GET | `/reports/export.csv` | Yes | Download expenses as CSV |

### Example: budget status

```json
{
  "id": 1,
  "category": "food",
  "month": "2026-09",
  "limit_amount": 300.0,
  "spent": 342.5,
  "remaining": -42.5,
  "percent_used": 114.2,
  "over_budget": true
}
```

**Categories:** food, transport, housing, utilities, health, entertainment, education, shopping, other

## Running Tests

```bash
python -m pytest -v
```

Tests run against a separate in-memory database, so real data is never affected. They cover authentication, input validation, filtering, budget calculations, reports, and verify that users can never read or modify another user's data.