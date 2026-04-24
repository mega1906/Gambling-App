from decimal import Decimal

from app.db import fetch_all, fetch_one
from app.exceptions import ValidationException
from app.models import GameResultRecord, RunningTotalsSummary, WinLossStatistics


class WinLossService:
    def get_win_loss_statistics(self, gambler_id):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        rows = self._get_results(gambler_id)
        if not rows:
            return WinLossStatistics(
                gambler_id=gambler_id,
                total_games=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                loss_rate=0.0,
                win_loss_ratio=0.0,
                total_winnings=0.0,
                total_losses_amount=0.0,
                net_profit_loss=0.0,
                average_win=0.0,
                average_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                current_win_streak=0,
                current_loss_streak=0,
                longest_win_streak=0,
                longest_loss_streak=0,
                profit_factor=0.0,
            )

        wins = [self._to_decimal(row["net_change"]) for row in rows if row["result_type"] == "WIN"]
        losses = [abs(self._to_decimal(row["net_change"])) for row in rows if row["result_type"] == "LOSS"]
        total_games = len(rows)
        win_count = len(wins)
        loss_count = len(losses)
        total_winnings = sum(wins, Decimal("0.00"))
        total_losses_amount = sum(losses, Decimal("0.00"))
        latest = rows[-1]

        return WinLossStatistics(
            gambler_id=gambler_id,
            total_games=total_games,
            wins=win_count,
            losses=loss_count,
            win_rate=round((win_count / total_games) * 100, 2) if total_games else 0.0,
            loss_rate=round((loss_count / total_games) * 100, 2) if total_games else 0.0,
            win_loss_ratio=round((win_count / loss_count), 2) if loss_count else float(win_count),
            total_winnings=self._round_money(total_winnings),
            total_losses_amount=self._round_money(total_losses_amount),
            net_profit_loss=self._round_money(total_winnings - total_losses_amount),
            average_win=self._round_money(total_winnings / win_count) if win_count else Decimal("0.00"),
            average_loss=self._round_money(total_losses_amount / loss_count) if loss_count else Decimal("0.00"),
            largest_win=max(wins) if wins else Decimal("0.00"),
            largest_loss=max(losses) if losses else Decimal("0.00"),
            current_win_streak=latest["current_win_streak"],
            current_loss_streak=latest["current_loss_streak"],
            longest_win_streak=latest["longest_win_streak"],
            longest_loss_streak=latest["longest_loss_streak"],
            profit_factor=round((total_winnings / total_losses_amount), 2) if total_losses_amount else float(total_winnings),
        )

    def get_running_totals(self, gambler_id, limit=10):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        rows = self._get_results(gambler_id)
        recent_rows = rows[-limit:] if limit else rows
        records = [self._to_result_record(row) for row in recent_rows]
        balance_history = [record.stake_after for record in records]

        return RunningTotalsSummary(
            gambler_id=gambler_id,
            total_games=len(rows),
            current_balance=gambler["current_stake"],
            net_profit_loss=self._round_money(self._to_decimal(gambler["current_stake"]) - self._to_decimal(gambler["initial_stake"])),
            balance_history=balance_history,
            last_results=records,
        )

    def get_recent_results(self, gambler_id, limit=10):
        gambler = self._get_gambler(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        rows = fetch_all(
            """
            SELECT id, bet_id, gambler_id, outcome_strategy, result_type, payout_amount, net_change,
                   stake_before, stake_after, win_probability, house_edge, current_win_streak,
                   current_loss_streak, longest_win_streak, longest_loss_streak, created_at
            FROM game_results
            WHERE gambler_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (gambler_id, limit),
        )
        return [self._to_result_record(row) for row in rows]

    def _get_results(self, gambler_id):
        return fetch_all(
            """
            SELECT id, bet_id, gambler_id, outcome_strategy, result_type, payout_amount, net_change,
                   stake_before, stake_after, win_probability, house_edge, current_win_streak,
                   current_loss_streak, longest_win_streak, longest_loss_streak, created_at
            FROM game_results
            WHERE gambler_id = %s
            ORDER BY id
            """,
            (gambler_id,),
        )

    def _get_gambler(self, gambler_id):
        return fetch_one("SELECT * FROM gamblers WHERE id = %s", (gambler_id,))

    def _to_result_record(self, row):
        return GameResultRecord(
            result_id=row["id"],
            bet_id=row["bet_id"],
            gambler_id=row["gambler_id"],
            outcome_strategy=row["outcome_strategy"],
            result_type=row["result_type"],
            payout_amount=row["payout_amount"],
            net_change=row["net_change"],
            stake_before=row["stake_before"],
            stake_after=row["stake_after"],
            win_probability=row["win_probability"],
            house_edge=row["house_edge"],
            current_win_streak=row["current_win_streak"],
            current_loss_streak=row["current_loss_streak"],
            longest_win_streak=row["longest_win_streak"],
            longest_loss_streak=row["longest_loss_streak"],
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _to_decimal(value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _round_money(value):
        return value.quantize(Decimal("0.01"))
