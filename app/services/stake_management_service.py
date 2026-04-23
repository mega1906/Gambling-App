from decimal import Decimal

from app.db import execute_write, fetch_all, fetch_one, get_connection
from app.exceptions import ValidationException
from app.models import StakeBoundaryStatus, StakeHistoryReport, StakeMonitorSummary, StakeTransaction


TRANSACTION_TYPES = [
    "INITIAL_STAKE",
    "BET_PLACED",
    "BET_WIN",
    "BET_LOSS",
    "DEPOSIT",
    "WITHDRAWAL",
    "ADJUSTMENT",
    "RESET",
]


class StakeManagementService:
    def initialize_stake(self, gambler_id, amount, note="Stake initialized"):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        amount = self._to_decimal(amount)
        if amount <= 0:
            raise ValidationException("Initial stake must be greater than zero.")

        win_gap = self._to_decimal(gambler["win_threshold"]) - self._to_decimal(gambler["initial_stake"])
        loss_gap = self._to_decimal(gambler["initial_stake"]) - self._to_decimal(gambler["loss_threshold"])
        new_win_threshold = self._round_money(amount + win_gap)
        new_loss_threshold = self._round_money(max(Decimal("0"), amount - loss_gap))

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE gamblers
                SET initial_stake = %s, current_stake = %s, win_threshold = %s, loss_threshold = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (amount, amount, new_win_threshold, new_loss_threshold, gambler_id),
            )
            cursor.execute(
                """
                INSERT INTO stake_transactions (
                    gambler_id, transaction_type, amount, balance_before, balance_after, note, created_at
                )
                VALUES (%s, 'INITIAL_STAKE', %s, %s, %s, %s, NOW())
                """,
                (gambler_id, amount, Decimal("0.00"), amount, note),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def deposit_stake(self, gambler_id, amount, note="Stake deposit"):
        return self._apply_balance_change(gambler_id, amount, "DEPOSIT", note)

    def withdraw_stake(self, gambler_id, amount, note="Stake withdrawal"):
        amount = self._to_decimal(amount)
        return self._apply_balance_change(gambler_id, -amount, "WITHDRAWAL", note)

    def apply_bet_result(self, gambler_id, amount, outcome, note=None):
        amount = self._to_decimal(amount)
        if amount <= 0:
            raise ValidationException("Bet amount must be greater than zero.")

        outcome = outcome.upper()
        if outcome not in {"WIN", "LOSS"}:
            raise ValidationException("Outcome must be WIN or LOSS.")

        if outcome == "WIN":
            return self._apply_balance_change(gambler_id, amount, "BET_WIN", note or "Bet win recorded")
        return self._apply_balance_change(gambler_id, -amount, "BET_LOSS", note or "Bet loss recorded")

    def adjust_stake(self, gambler_id, new_stake, note="Manual adjustment"):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        new_stake = self._to_decimal(new_stake)
        if new_stake < 0:
            raise ValidationException("Stake cannot be negative.")

        current_stake = self._to_decimal(gambler["current_stake"])
        difference = new_stake - current_stake
        return self._apply_balance_change(gambler_id, difference, "ADJUSTMENT", note)

    def validate_boundaries(self, gambler_id):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        current_stake = self._to_decimal(gambler["current_stake"])
        upper_limit = self._to_decimal(gambler["win_threshold"])
        lower_limit = self._to_decimal(gambler["loss_threshold"])
        range_gap = upper_limit - lower_limit
        upper_warning = upper_limit - (range_gap * Decimal("0.20"))
        lower_warning = lower_limit + (range_gap * Decimal("0.20"))

        warning_level = "NORMAL"
        within_bounds = lower_limit <= current_stake <= upper_limit

        if current_stake >= upper_limit:
            warning_level = "UPPER_LIMIT_REACHED"
        elif current_stake <= lower_limit:
            warning_level = "LOWER_LIMIT_REACHED"
        elif current_stake >= upper_warning:
            warning_level = "NEAR_UPPER_LIMIT"
        elif current_stake <= lower_warning:
            warning_level = "NEAR_LOWER_LIMIT"

        return StakeBoundaryStatus(
            current_stake=current_stake,
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            warning_level=warning_level,
            within_bounds=within_bounds,
        )

    def get_monitor_summary(self, gambler_id):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        rows = fetch_all(
            """
            SELECT balance_after
            FROM stake_transactions
            WHERE gambler_id = %s
            ORDER BY created_at, id
            """,
            (gambler_id,),
        )

        initial_stake = self._to_decimal(gambler["initial_stake"])
        current_stake = self._to_decimal(gambler["current_stake"])

        balances = [initial_stake]
        balances.extend(self._to_decimal(row["balance_after"]) for row in rows)

        peak_stake = max(balances)
        lowest_stake = min(balances)
        total_change = self._round_money(current_stake - initial_stake)
        volatility = self._round_money(peak_stake - lowest_stake)

        return StakeMonitorSummary(
            current_stake=current_stake,
            peak_stake=peak_stake,
            lowest_stake=lowest_stake,
            total_change=total_change,
            volatility=volatility,
            transaction_count=len(rows),
        )

    def get_history_report(self, gambler_id):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        rows = fetch_all(
            """
            SELECT id, gambler_id, transaction_type, amount, balance_before, balance_after, note, created_at
            FROM stake_transactions
            WHERE gambler_id = %s
            ORDER BY created_at, id
            """,
            (gambler_id,),
        )

        transactions = [
            StakeTransaction(
                transaction_id=row["id"],
                gambler_id=row["gambler_id"],
                transaction_type=row["transaction_type"],
                amount=row["amount"],
                balance_before=row["balance_before"],
                balance_after=row["balance_after"],
                note=row["note"],
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

        totals = {
            "DEPOSIT": Decimal("0.00"),
            "WITHDRAWAL": Decimal("0.00"),
            "BET_WIN": Decimal("0.00"),
            "BET_LOSS": Decimal("0.00"),
            "ADJUSTMENT": Decimal("0.00"),
        }
        for row in rows:
            transaction_type = row["transaction_type"]
            if transaction_type in totals:
                totals[transaction_type] += self._to_decimal(row["amount"])

        current_stake = self._to_decimal(gambler["current_stake"])
        initial_stake = self._to_decimal(gambler["initial_stake"])

        return StakeHistoryReport(
            gambler_id=gambler_id,
            current_stake=current_stake,
            total_transactions=len(transactions),
            deposits_total=self._round_money(totals["DEPOSIT"]),
            withdrawals_total=self._round_money(totals["WITHDRAWAL"]),
            bet_wins_total=self._round_money(totals["BET_WIN"]),
            bet_losses_total=self._round_money(totals["BET_LOSS"]),
            adjustments_total=self._round_money(totals["ADJUSTMENT"]),
            net_change=self._round_money(current_stake - initial_stake),
            transactions=transactions,
        )

    def _apply_balance_change(self, gambler_id, signed_amount, transaction_type, note):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        signed_amount = self._to_decimal(signed_amount)
        balance_before = self._to_decimal(gambler["current_stake"])
        balance_after = self._round_money(balance_before + signed_amount)

        if transaction_type in {"DEPOSIT", "BET_WIN"} and signed_amount <= 0:
            raise ValidationException("Amount must be greater than zero.")
        if transaction_type in {"WITHDRAWAL", "BET_LOSS"} and signed_amount >= 0:
            raise ValidationException("Amount must reduce the stake.")
        if balance_after < 0:
            raise ValidationException("Insufficient stake for this operation.")

        execute_write(
            """
            UPDATE gamblers
            SET current_stake = %s, updated_at = NOW()
            WHERE id = %s
            """,
            (balance_after, gambler_id),
        )
        execute_write(
            """
            INSERT INTO stake_transactions (
                gambler_id, transaction_type, amount, balance_before, balance_after, note, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """,
            (gambler_id, transaction_type, abs(signed_amount), balance_before, balance_after, note),
        )
        return balance_after

    def _get_gambler(self, gambler_id):
        return fetch_one("SELECT * FROM gamblers WHERE id = %s", (gambler_id,))

    @staticmethod
    def _to_decimal(value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _round_money(value):
        return value.quantize(Decimal("0.01"))
