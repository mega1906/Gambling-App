from dataclasses import dataclass


@dataclass
class BettingPreferences:
    min_bet: float
    max_bet: float
    preferred_game_type: str = "CUSTOM"
    session_game_limit: int = 20
    notes: str | None = None


@dataclass
class StakeTransaction:
    transaction_id: int
    gambler_id: int
    transaction_type: str
    amount: float
    balance_before: float
    balance_after: float
    note: str | None
    created_at: str


@dataclass
class StakeBoundaryStatus:
    current_stake: float
    upper_limit: float
    lower_limit: float
    warning_level: str
    within_bounds: bool


@dataclass
class StakeMonitorSummary:
    current_stake: float
    peak_stake: float
    lowest_stake: float
    total_change: float
    volatility: float
    transaction_count: int


@dataclass
class StakeHistoryReport:
    gambler_id: int
    current_stake: float
    total_transactions: int
    deposits_total: float
    withdrawals_total: float
    bet_wins_total: float
    bet_losses_total: float
    adjustments_total: float
    net_change: float
    transactions: list[StakeTransaction]


@dataclass
class BetRecord:
    bet_id: int
    gambler_id: int
    session_id: int | None
    strategy_type: str
    bet_amount: float
    win_probability: float
    odds_multiplier: float
    outcome: str
    payout_amount: float
    stake_before: float
    stake_after: float
    placed_at: str


@dataclass
class BettingSessionSummary:
    session_id: int
    gambler_id: int
    strategy_type: str
    total_bets: int
    total_wins: int
    total_losses: int
    total_profit: float
    started_at: str
    ended_at: str | None
    bets: list[BetRecord]


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
