from dataclasses import dataclass


@dataclass
class BettingPreferences:
    min_bet: float
    max_bet: float
    preferred_game_type: str = "CUSTOM"
    session_game_limit: int = 20
    notes: str | None = None


@dataclass
class GamblerStatistics:
    gambler_id: int
    full_name: str
    email: str
    phone_number: str | None
    current_stake: float
    initial_stake: float
    win_threshold: float
    loss_threshold: float
    threshold_status: str
    total_bets: int
    total_wins: int
    total_losses: int
    total_winnings: float
    net_profit_loss: float
    win_rate: float
    account_status: str
    preferred_game_type: str
    min_bet: float
    max_bet: float
    session_game_limit: int
    notes: str | None
