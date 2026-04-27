# Gambling-App

A modular gambling simulation where a player manages stake, places bets using strategies and plays sessions with win/loss limits. Built using Python with SQL-based persistence.

## Project Structure
```
GAMBLING-APP/
│
├── app/
│   ├── services/
│   │   ├── betting_service.py
│   │   ├── gambler_profile_service.py
│   │   ├── game_session_service.py
│   │   ├── stake_management_service.py
│   │   └── win_loss_service.py
│   │
│   ├── db.py
│   ├── default_user.py
│   ├── exceptions.py
│   ├── models.py
│   ├── schema.py
│   ├── settings.py
│   └── validation.py
│
├── main.py
├── requirements.txt
├── .env
└── README.md
```
## Use Cases

### 1. Gambler Profile
Create, update, and reset gambler profiles with stake and limits. Tracks basic stats and validates eligibility.

### 2. Stake Management
Handles balance updates, transactions, and stake limits. Maintains full history and validates boundaries.

### 3. Betting Mechanism
Places bets with strategies and probability-based outcomes. Automatically updates stake after each result.

### 4. Game Session
Manages session lifecycle (start, pause, resume, end). Ends automatically when win/loss limits are reached.

### 5. Win/Loss Calculation
Calculates outcomes, tracks profit/loss, and maintains streaks. Provides basic performance metrics.

### 6. Validation & Errors
Validates inputs (stake, bet, probability). Handles errors using custom exceptions.

### 7. User Interaction
CLI-based interaction to place bets, view status, and see session summaries.

---

## Setup & Run

```bash
# 1. Clone repo
git clone https://github.com/mega1906/Gambling-App.git
cd gambling-app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # (Linux/Mac)
venv\Scripts\activate      # (Windows)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
.env

# 5. Run application
python main.py
```

## Database
- Uses SQL (configurable in .env)
- Schema defined in app/schema.py
- Connection handled via app/db.py
