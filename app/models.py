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
class GamePlayRecord:
    game_id: int
    session_id: int
    bet_id: int
    game_number: int
    bet_amount: float
    outcome: str
    payout_amount: float
    stake_before: float
    stake_after: float
    played_at: str


@dataclass
class GameResultRecord:
    result_id: int
    bet_id: int
    gambler_id: int
    outcome_strategy: str
    result_type: str
    payout_amount: float
    net_change: float
    stake_before: float
    stake_after: float
    win_probability: float
    house_edge: float
    current_win_streak: int
    current_loss_streak: int
    longest_win_streak: int
    longest_loss_streak: int
    created_at: str


@dataclass
class PauseRecord:
    pause_id: int
    session_id: int
    pause_reason: str
    paused_at: str
    resumed_at: str | None
    pause_seconds: int


@dataclass
class GamingSessionSummary:
    session_id: int
    gambler_id: int
    status: str
    end_reason: str | None
    default_bet_amount: float
    default_win_probability: float
    max_games: int
    total_games_played: int
    total_wins: int
    total_losses: int
    total_profit: float
    current_stake: float
    started_at: str
    ended_at: str | None
    total_pause_seconds: int
    games: list[GamePlayRecord]
    pauses: list[PauseRecord]


@dataclass
class WinLossStatistics:
    gambler_id: int
    total_games: int
    wins: int
    losses: int
    win_rate: float
    loss_rate: float
    win_loss_ratio: float
    total_winnings: float
    total_losses_amount: float
    net_profit_loss: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    current_win_streak: int
    current_loss_streak: int
    longest_win_streak: int
    longest_loss_streak: int
    profit_factor: float


@dataclass
class RunningTotalsSummary:
    gambler_id: int
    total_games: int
    current_balance: float
    net_profit_loss: float
    balance_history: list[float]
    last_results: list[GameResultRecord]


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
