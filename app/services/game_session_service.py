from decimal import Decimal

from app.db import fetch_all, fetch_one, get_connection
from app.exceptions import ValidationException
from app.models import GamePlayRecord, GamingSessionSummary, PauseRecord
from app.services.betting_service import BettingService
from app.validation import InputValidator, ValidationConfig


SESSION_STATUSES = ["ACTIVE", "PAUSED", "ENDED_WIN", "ENDED_LOSS", "ENDED_MANUAL", "ENDED_LIMIT", "ENDED_MAX_GAMES"]
SESSION_END_REASONS = ["UPPER_LIMIT_REACHED", "LOWER_LIMIT_REACHED", "MANUAL_EXIT", "MAX_GAMES_REACHED"]


class GameSessionService:
    def __init__(self, betting_service=None):
        self.betting_service = betting_service or BettingService()
        self.validator = InputValidator(ValidationConfig(allow_zero_stake=True))

    def start_new_session(self, gambler_id, default_bet_amount, default_win_probability, max_games):
        gambler = self._get_gambler(gambler_id)
        preferences = self._get_preferences(gambler_id)
        if not gambler or not preferences:
            raise ValidationException("Gambler profile not found.")
        if self._find_open_session(gambler_id):
            raise ValidationException("This gambler already has an open session.")

        default_bet_amount = self._to_decimal(
            self.validator.validate_bet_amount(default_bet_amount, current_stake=10**9, min_bet=0.01, max_bet=10**9, field_name="default_bet_amount")
        )
        default_win_probability = self._to_decimal(self.validator.validate_probability(default_win_probability, "default_win_probability"))
        if max_games <= 0:
            raise ValidationException("Max games must be greater than zero.")

        min_bet = self._to_decimal(preferences["min_bet"])
        max_bet = self._to_decimal(preferences["max_bet"])
        current_stake = self._to_decimal(gambler["current_stake"])
        if default_bet_amount < min_bet or default_bet_amount > max_bet or default_bet_amount > current_stake:
            raise ValidationException("Default bet amount must fit the current bet limits and available stake.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO gaming_sessions (
                    gambler_id, status, end_reason, default_bet_amount, default_win_probability,
                    max_games, total_games_played, total_wins, total_losses, total_profit,
                    total_pause_seconds, started_at, ended_at, updated_at
                )
                VALUES (%s, 'ACTIVE', NULL, %s, %s, %s, 0, 0, 0, 0.00, 0, NOW(), NULL, NOW())
                """,
                (gambler_id, default_bet_amount, default_win_probability, max_games),
            )
            connection.commit()
            return cursor.lastrowid
        finally:
            cursor.close()
            connection.close()

    def play_games(self, session_id, number_of_games=1, bet_amount=None, win_probability=None):
        session = self._get_session(session_id)
        if not session:
            raise ValidationException("Session not found.")
        if session["status"] != "ACTIVE":
            raise ValidationException("Only active sessions can play games.")
        if number_of_games <= 0:
            raise ValidationException("Number of games must be greater than zero.")

        results = []
        for _ in range(number_of_games):
            session = self._get_session(session_id)
            if session["status"] != "ACTIVE":
                break
            if session["total_games_played"] >= session["max_games"]:
                self._end_session(session_id, "ENDED_MAX_GAMES", "MAX_GAMES_REACHED")
                break

            actual_bet_amount = bet_amount if bet_amount is not None else session["default_bet_amount"]
            actual_probability = win_probability if win_probability is not None else session["default_win_probability"]
            bet_record = self.betting_service.place_bet(
                session["gambler_id"],
                actual_bet_amount,
                actual_probability,
                "FIXED_AMOUNT",
            )
            self._record_game(session_id, bet_record)
            results.append(bet_record)

            current_session = self._get_session(session_id)
            current_stake = self._to_decimal(self._get_gambler(current_session["gambler_id"])["current_stake"])
            upper_limit = self._to_decimal(self._get_gambler(current_session["gambler_id"])["win_threshold"])
            lower_limit = self._to_decimal(self._get_gambler(current_session["gambler_id"])["loss_threshold"])

            if current_stake >= upper_limit:
                self._end_session(session_id, "ENDED_WIN", "UPPER_LIMIT_REACHED")
                break
            if current_stake <= lower_limit:
                self._end_session(session_id, "ENDED_LOSS", "LOWER_LIMIT_REACHED")
                break
            if current_session["total_games_played"] >= current_session["max_games"]:
                self._end_session(session_id, "ENDED_MAX_GAMES", "MAX_GAMES_REACHED")
                break

        return results

    def pause_session(self, session_id, reason):
        session = self._get_session(session_id)
        if not session:
            raise ValidationException("Session not found.")
        if session["status"] != "ACTIVE":
            raise ValidationException("Only active sessions can be paused.")
        if not reason.strip():
            raise ValidationException("Pause reason is required.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE gaming_sessions
                SET status = 'PAUSED', updated_at = NOW()
                WHERE id = %s
                """,
                (session_id,),
            )
            cursor.execute(
                """
                INSERT INTO pause_records (session_id, pause_reason, paused_at, resumed_at, pause_seconds)
                VALUES (%s, %s, NOW(), NULL, 0)
                """,
                (session_id, reason.strip()),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def resume_session(self, session_id):
        session = self._get_session(session_id)
        if not session:
            raise ValidationException("Session not found.")
        if session["status"] != "PAUSED":
            raise ValidationException("Only paused sessions can be resumed.")

        pause_record = fetch_one(
            """
            SELECT id, TIMESTAMPDIFF(SECOND, paused_at, NOW()) AS pause_seconds
            FROM pause_records
            WHERE session_id = %s AND resumed_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        )
        if not pause_record:
            raise ValidationException("No active pause record found.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE pause_records
                SET resumed_at = NOW(), pause_seconds = %s
                WHERE id = %s
                """,
                (pause_record["pause_seconds"], pause_record["id"]),
            )
            cursor.execute(
                """
                UPDATE gaming_sessions
                SET status = 'ACTIVE',
                    total_pause_seconds = total_pause_seconds + %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (pause_record["pause_seconds"], session_id),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def end_session(self, session_id):
        session = self._get_session(session_id)
        if not session:
            raise ValidationException("Session not found.")
        if session["status"] in {"ENDED_WIN", "ENDED_LOSS", "ENDED_MANUAL", "ENDED_LIMIT", "ENDED_MAX_GAMES"}:
            raise ValidationException("Session is already ended.")
        self._end_session(session_id, "ENDED_MANUAL", "MANUAL_EXIT")

    def get_session_summary(self, session_id):
        session = self._get_session(session_id)
        if not session:
            raise ValidationException("Session not found.")

        games = fetch_all(
            """
            SELECT id, session_id, bet_id, game_number, bet_amount, outcome, payout_amount, stake_before, stake_after, played_at
            FROM game_records
            WHERE session_id = %s
            ORDER BY game_number
            """,
            (session_id,),
        )
        pauses = fetch_all(
            """
            SELECT id, session_id, pause_reason, paused_at, resumed_at, pause_seconds
            FROM pause_records
            WHERE session_id = %s
            ORDER BY id
            """,
            (session_id,),
        )
        gambler = self._get_gambler(session["gambler_id"])

        return GamingSessionSummary(
            session_id=session["id"],
            gambler_id=session["gambler_id"],
            status=session["status"],
            end_reason=session["end_reason"],
            default_bet_amount=session["default_bet_amount"],
            default_win_probability=session["default_win_probability"],
            max_games=session["max_games"],
            total_games_played=session["total_games_played"],
            total_wins=session["total_wins"],
            total_losses=session["total_losses"],
            total_profit=session["total_profit"],
            current_stake=gambler["current_stake"],
            started_at=str(session["started_at"]),
            ended_at=str(session["ended_at"]) if session["ended_at"] else None,
            total_pause_seconds=session["total_pause_seconds"],
            games=[
                GamePlayRecord(
                    game_id=row["id"],
                    session_id=row["session_id"],
                    bet_id=row["bet_id"],
                    game_number=row["game_number"],
                    bet_amount=row["bet_amount"],
                    outcome=row["outcome"],
                    payout_amount=row["payout_amount"],
                    stake_before=row["stake_before"],
                    stake_after=row["stake_after"],
                    played_at=str(row["played_at"]),
                )
                for row in games
            ],
            pauses=[
                PauseRecord(
                    pause_id=row["id"],
                    session_id=row["session_id"],
                    pause_reason=row["pause_reason"],
                    paused_at=str(row["paused_at"]),
                    resumed_at=str(row["resumed_at"]) if row["resumed_at"] else None,
                    pause_seconds=row["pause_seconds"],
                )
                for row in pauses
            ],
        )

    def list_sessions(self, gambler_id):
        return fetch_all(
            """
            SELECT id, status, end_reason, total_games_played, max_games, total_profit, started_at, ended_at
            FROM gaming_sessions
            WHERE gambler_id = %s
            ORDER BY id DESC
            """,
            (gambler_id,),
        )

    def _record_game(self, session_id, bet_record):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT total_games_played FROM gaming_sessions WHERE id = %s",
                (session_id,),
            )
            session_row = cursor.fetchone()
            game_number = session_row[0] + 1
            cursor.execute(
                """
                INSERT INTO game_records (
                    session_id, bet_id, game_number, bet_amount, outcome, payout_amount,
                    stake_before, stake_after, played_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    session_id,
                    bet_record.bet_id,
                    game_number,
                    bet_record.bet_amount,
                    bet_record.outcome,
                    bet_record.payout_amount,
                    bet_record.stake_before,
                    bet_record.stake_after,
                ),
            )
            cursor.execute(
                """
                UPDATE gaming_sessions
                SET total_games_played = total_games_played + 1,
                    total_wins = total_wins + %s,
                    total_losses = total_losses + %s,
                    total_profit = total_profit + %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    1 if bet_record.outcome == "WIN" else 0,
                    1 if bet_record.outcome == "LOSS" else 0,
                    bet_record.payout_amount,
                    session_id,
                ),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _end_session(self, session_id, status, end_reason):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                UPDATE gaming_sessions
                SET status = %s, end_reason = %s, ended_at = NOW(), updated_at = NOW()
                WHERE id = %s
                """,
                (status, end_reason, session_id),
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def _find_open_session(self, gambler_id):
        return fetch_one(
            """
            SELECT id
            FROM gaming_sessions
            WHERE gambler_id = %s AND status IN ('ACTIVE', 'PAUSED')
            LIMIT 1
            """,
            (gambler_id,),
        )

    def _get_session(self, session_id):
        return fetch_one("SELECT * FROM gaming_sessions WHERE id = %s", (session_id,))

    def _get_gambler(self, gambler_id):
        return fetch_one("SELECT * FROM gamblers WHERE id = %s", (gambler_id,))

    def _get_preferences(self, gambler_id):
        return fetch_one("SELECT * FROM betting_preferences WHERE gambler_id = %s", (gambler_id,))

    @staticmethod
    def _to_decimal(value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
