import random
from decimal import Decimal

from app.db import fetch_all, fetch_one, get_connection
from app.exceptions import ValidationException
from app.models import BetRecord, BettingSessionSummary


STRATEGY_TYPES = [
    "FIXED_AMOUNT",
    "PERCENTAGE",
    "MARTINGALE",
    "REVERSE_MARTINGALE",
    "FIBONACCI",
    "DALEMBERT",
]


class BettingService:
    def place_bet(self, gambler_id, bet_amount, win_probability, strategy_type="FIXED_AMOUNT", session_id=None):
        gambler = self._get_gambler(gambler_id)
        preferences = self._get_preferences(gambler_id)
        if not gambler or not preferences:
            raise ValidationException("Gambler profile not found.")

        bet_amount = self._to_decimal(bet_amount)
        win_probability = self._to_decimal(win_probability)
        self._validate_bet(gambler, preferences, bet_amount, win_probability, strategy_type)

        stake_before = self._to_decimal(gambler["current_stake"])
        outcome = "WIN" if self._is_win(win_probability) else "LOSS"
        odds_multiplier = self._calculate_odds_multiplier(win_probability)
        payout_amount = self._calculate_payout(bet_amount, odds_multiplier, outcome)
        stake_after = self._round_money(stake_before + payout_amount)

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO bets (
                    gambler_id, session_id, strategy_type, bet_amount, win_probability, odds_multiplier,
                    outcome, payout_amount, stake_before, stake_after, placed_at, settled_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (
                    gambler_id,
                    session_id,
                    strategy_type,
                    bet_amount,
                    win_probability,
                    odds_multiplier,
                    outcome,
                    payout_amount,
                    stake_before,
                    stake_after,
                ),
            )
            bet_id = cursor.lastrowid

            cursor.execute(
                """
                UPDATE gamblers
                SET current_stake = %s,
                    total_bets = total_bets + 1,
                    total_wins = total_wins + %s,
                    total_losses = total_losses + %s,
                    total_winnings = total_winnings + %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    stake_after,
                    1 if outcome == "WIN" else 0,
                    1 if outcome == "LOSS" else 0,
                    payout_amount if outcome == "WIN" else Decimal("0.00"),
                    gambler_id,
                ),
            )

            cursor.execute(
                """
                INSERT INTO stake_transactions (
                    gambler_id, transaction_type, amount, balance_before, balance_after, note, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    gambler_id,
                    "BET_WIN" if outcome == "WIN" else "BET_LOSS",
                    abs(payout_amount),
                    stake_before,
                    stake_after,
                    f"Bet #{bet_id} settled with {outcome.lower()}",
                ),
            )

            if session_id is not None:
                cursor.execute(
                    """
                    UPDATE betting_sessions
                    SET total_bets = total_bets + 1,
                        total_wins = total_wins + %s,
                        total_losses = total_losses + %s,
                        total_profit = total_profit + %s
                    WHERE id = %s
                    """,
                    (
                        1 if outcome == "WIN" else 0,
                        1 if outcome == "LOSS" else 0,
                        payout_amount,
                        session_id,
                    ),
                )

            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        return self.get_bet_record(bet_id)

    def place_bet_with_strategy(self, gambler_id, strategy_type, win_probability, fixed_amount=None, percentage_value=None, rounds=1):
        strategy_type = strategy_type.upper()
        if strategy_type not in STRATEGY_TYPES:
            raise ValidationException("Choose a valid betting strategy.")
        if rounds <= 0:
            raise ValidationException("Rounds must be greater than zero.")

        session_id = self._create_session(gambler_id, strategy_type)
        fibonacci_sequence = [1, 1]
        fibonacci_index = 0
        dalembert_step = Decimal("1.00")
        current_amount = self._to_decimal(fixed_amount or 0)
        bet_records = []

        previous_outcome = None
        try:
            for _ in range(rounds):
                gambler = self._get_gambler(gambler_id)
                preferences = self._get_preferences(gambler_id)
                stake = self._to_decimal(gambler["current_stake"])

                if strategy_type == "FIXED_AMOUNT":
                    amount = self._to_decimal(fixed_amount)
                elif strategy_type == "PERCENTAGE":
                    percent = self._to_decimal(percentage_value)
                    amount = self._round_money(stake * percent / Decimal("100"))
                elif strategy_type == "MARTINGALE":
                    if previous_outcome in {None, "WIN"}:
                        current_amount = self._to_decimal(fixed_amount)
                    amount = current_amount
                elif strategy_type == "REVERSE_MARTINGALE":
                    if previous_outcome in {None, "LOSS"}:
                        current_amount = self._to_decimal(fixed_amount)
                    amount = current_amount
                elif strategy_type == "FIBONACCI":
                    while len(fibonacci_sequence) <= fibonacci_index:
                        fibonacci_sequence.append(fibonacci_sequence[-1] + fibonacci_sequence[-2])
                    amount = self._to_decimal(fixed_amount) * Decimal(str(fibonacci_sequence[fibonacci_index]))
                else:
                    if previous_outcome is None:
                        current_amount = self._to_decimal(fixed_amount)
                    amount = current_amount

                amount = self._fit_amount_to_limits(amount, preferences, stake)
                bet_record = self.place_bet(gambler_id, amount, win_probability, strategy_type, session_id)
                bet_records.append(bet_record)
                previous_outcome = bet_record.outcome

                if strategy_type == "MARTINGALE":
                    current_amount = self._to_decimal(fixed_amount) if previous_outcome == "WIN" else self._round_money(amount * Decimal("2"))
                elif strategy_type == "REVERSE_MARTINGALE":
                    current_amount = self._round_money(amount * Decimal("2")) if previous_outcome == "WIN" else self._to_decimal(fixed_amount)
                elif strategy_type == "FIBONACCI":
                    if previous_outcome == "WIN":
                        fibonacci_index = max(0, fibonacci_index - 2)
                    else:
                        fibonacci_index += 1
                elif strategy_type == "DALEMBERT":
                    if previous_outcome == "LOSS":
                        current_amount = self._round_money(amount + dalembert_step)
                    else:
                        next_amount = amount - dalembert_step
                        current_amount = self._to_decimal(fixed_amount) if next_amount < self._to_decimal(fixed_amount) else self._round_money(next_amount)

            self._close_session(session_id)
        except Exception:
            self._close_session(session_id)
            raise

        return self.get_session_summary(session_id)

    def get_bet_record(self, bet_id):
        row = fetch_one(
            """
            SELECT id, gambler_id, session_id, strategy_type, bet_amount, win_probability, odds_multiplier,
                   outcome, payout_amount, stake_before, stake_after, placed_at
            FROM bets
            WHERE id = %s
            """,
            (bet_id,),
        )
        if not row:
            raise ValidationException("Bet not found.")
        return BetRecord(
            bet_id=row["id"],
            gambler_id=row["gambler_id"],
            session_id=row["session_id"],
            strategy_type=row["strategy_type"],
            bet_amount=row["bet_amount"],
            win_probability=row["win_probability"],
            odds_multiplier=row["odds_multiplier"],
            outcome=row["outcome"],
            payout_amount=row["payout_amount"],
            stake_before=row["stake_before"],
            stake_after=row["stake_after"],
            placed_at=str(row["placed_at"]),
        )

    def get_recent_bets(self, gambler_id, limit=10):
        rows = fetch_all(
            """
            SELECT id, gambler_id, session_id, strategy_type, bet_amount, win_probability, odds_multiplier,
                   outcome, payout_amount, stake_before, stake_after, placed_at
            FROM bets
            WHERE gambler_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (gambler_id, limit),
        )
        return [
            BetRecord(
                bet_id=row["id"],
                gambler_id=row["gambler_id"],
                session_id=row["session_id"],
                strategy_type=row["strategy_type"],
                bet_amount=row["bet_amount"],
                win_probability=row["win_probability"],
                odds_multiplier=row["odds_multiplier"],
                outcome=row["outcome"],
                payout_amount=row["payout_amount"],
                stake_before=row["stake_before"],
                stake_after=row["stake_after"],
                placed_at=str(row["placed_at"]),
            )
            for row in rows
        ]

    def get_session_summary(self, session_id):
        session_row = fetch_one(
            """
            SELECT id, gambler_id, strategy_type, total_bets, total_wins, total_losses, total_profit, started_at, ended_at
            FROM betting_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        if not session_row:
            raise ValidationException("Betting session not found.")

        bets = fetch_all(
            """
            SELECT id, gambler_id, session_id, strategy_type, bet_amount, win_probability, odds_multiplier,
                   outcome, payout_amount, stake_before, stake_after, placed_at
            FROM bets
            WHERE session_id = %s
            ORDER BY id
            """,
            (session_id,),
        )

        return BettingSessionSummary(
            session_id=session_row["id"],
            gambler_id=session_row["gambler_id"],
            strategy_type=session_row["strategy_type"],
            total_bets=session_row["total_bets"],
            total_wins=session_row["total_wins"],
            total_losses=session_row["total_losses"],
            total_profit=session_row["total_profit"],
            started_at=str(session_row["started_at"]),
            ended_at=str(session_row["ended_at"]) if session_row["ended_at"] else None,
            bets=[
                BetRecord(
                    bet_id=row["id"],
                    gambler_id=row["gambler_id"],
                    session_id=row["session_id"],
                    strategy_type=row["strategy_type"],
                    bet_amount=row["bet_amount"],
                    win_probability=row["win_probability"],
                    odds_multiplier=row["odds_multiplier"],
                    outcome=row["outcome"],
                    payout_amount=row["payout_amount"],
                    stake_before=row["stake_before"],
                    stake_after=row["stake_after"],
                    placed_at=str(row["placed_at"]),
                )
                for row in bets
            ],
        )

    def _create_session(self, gambler_id, strategy_type):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO betting_sessions (
                    gambler_id, strategy_type, status, total_bets, total_wins, total_losses, total_profit, started_at
                )
                VALUES (%s, %s, 'ACTIVE', 0, 0, 0, 0.00, NOW())
                """,
                (gambler_id, strategy_type),
            )
            connection.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            connection.close()

    def _close_session(self, session_id):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE betting_sessions
                SET status = 'COMPLETED', ended_at = NOW()
                WHERE id = %s
                """,
                (session_id,),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _validate_bet(self, gambler, preferences, bet_amount, win_probability, strategy_type):
        if strategy_type.upper() not in STRATEGY_TYPES:
            raise ValidationException("Choose a valid betting strategy.")
        if bet_amount <= 0:
            raise ValidationException("Bet amount must be greater than zero.")
        if win_probability <= 0 or win_probability >= 1:
            raise ValidationException("Win probability must be greater than 0 and less than 1.")

        current_stake = self._to_decimal(gambler["current_stake"])
        min_bet = self._to_decimal(preferences["min_bet"])
        max_bet = self._to_decimal(preferences["max_bet"])

        if bet_amount < min_bet:
            raise ValidationException(f"Bet amount must be at least {min_bet:.2f}.")
        if bet_amount > max_bet:
            raise ValidationException(f"Bet amount must be at most {max_bet:.2f}.")
        if bet_amount > current_stake:
            raise ValidationException("Bet amount cannot be greater than the current stake.")

    def _get_gambler(self, gambler_id):
        return fetch_one("SELECT * FROM gamblers WHERE id = %s", (gambler_id,))

    def _get_preferences(self, gambler_id):
        return fetch_one("SELECT * FROM betting_preferences WHERE gambler_id = %s", (gambler_id,))

    def _calculate_odds_multiplier(self, win_probability):
        house_margin = Decimal("0.95")
        return self._round_money(house_margin / win_probability)

    def _calculate_payout(self, bet_amount, odds_multiplier, outcome):
        if outcome == "WIN":
            return self._round_money(bet_amount * (odds_multiplier - Decimal("1.00")))
        return self._round_money(-bet_amount)

    def _is_win(self, win_probability):
        return Decimal(str(random.random())) <= win_probability

    def _fit_amount_to_limits(self, amount, preferences, current_stake):
        min_bet = self._to_decimal(preferences["min_bet"])
        max_bet = self._to_decimal(preferences["max_bet"])
        amount = self._round_money(amount)
        if amount < min_bet:
            amount = min_bet
        if amount > max_bet:
            amount = max_bet
        if amount > current_stake:
            amount = current_stake
        if amount < min_bet:
            raise ValidationException("Current stake is lower than the minimum bet.")
        return amount

    @staticmethod
    def _to_decimal(value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _round_money(value):
        return value.quantize(Decimal("0.01"))
