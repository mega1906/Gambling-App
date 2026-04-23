from datetime import datetime
from decimal import Decimal

from mysql.connector import Error

from app.db import execute_many, execute_write, fetch_all, fetch_one, get_connection
from app.exceptions import ValidationException
from app.models import GamblerStatistics


GAME_TYPES = [
    "COIN_FLIP",
    "DICE",
    "ROULETTE",
    "SLOT_STYLE",
    "PROBABILITY_GAME",
    "CUSTOM",
]


class GamblerProfileService:
    def __init__(self, minimum_stake=100.0):
        self.minimum_stake = self._to_decimal(minimum_stake)

    def ensure_gambler_exists(self, gambler_data):
        existing_gambler = self.find_gambler_by_email(gambler_data["email"])
        if existing_gambler:
            self._ensure_initial_stake_transaction(existing_gambler["id"])
            return existing_gambler["id"]

        return self.create_gambler(
            full_name=gambler_data["full_name"],
            email=gambler_data["email"],
            phone_number=gambler_data["phone_number"],
            initial_stake=gambler_data["initial_stake"],
            win_threshold=gambler_data["win_threshold"],
            loss_threshold=gambler_data["loss_threshold"],
            preferences=gambler_data["preferences"],
        )

    def create_gambler(self, full_name, email, phone_number, initial_stake, win_threshold, loss_threshold, preferences):
        initial_stake = self._to_decimal(initial_stake)
        win_threshold = self._to_decimal(win_threshold)
        loss_threshold = self._to_decimal(loss_threshold)
        clean_preferences = self._normalize_preferences(preferences)

        self._validate_profile_inputs(
            full_name=full_name,
            email=email,
            initial_stake=initial_stake,
            win_threshold=win_threshold,
            loss_threshold=loss_threshold,
            preferences=clean_preferences,
        )

        timestamp = self._now()
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO gamblers (
                    full_name, email, phone_number, initial_stake, current_stake,
                    win_threshold, loss_threshold, account_status, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE', %s, %s)
                """,
                (
                    full_name.strip(),
                    email.strip().lower(),
                    phone_number.strip() if phone_number else None,
                    initial_stake,
                    initial_stake,
                    win_threshold,
                    loss_threshold,
                    timestamp,
                    timestamp,
                ),
            )
            gambler_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO betting_preferences (
                    gambler_id, min_bet, max_bet, preferred_game_type,
                    session_game_limit, notes, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    gambler_id,
                    clean_preferences["min_bet"],
                    clean_preferences["max_bet"],
                    clean_preferences["preferred_game_type"],
                    clean_preferences["session_game_limit"],
                    clean_preferences["notes"],
                    timestamp,
                    timestamp,
                ),
            )
            cursor.execute(
                """
                INSERT INTO stake_transactions (
                    gambler_id, transaction_type, amount, balance_before, balance_after, note, created_at
                )
                VALUES (%s, 'INITIAL_STAKE', %s, %s, %s, %s, %s)
                """,
                (
                    gambler_id,
                    initial_stake,
                    Decimal("0.00"),
                    initial_stake,
                    "Initial stake recorded during profile creation",
                    timestamp,
                ),
            )
            connection.commit()
        except Error as error:
            connection.rollback()
            raise ValidationException(f"Could not create gambler profile: {error}") from error
        finally:
            cursor.close()
            connection.close()
        return gambler_id

    def update_gambler(self, gambler_id, profile_updates=None, preference_updates=None):
        profile_updates = profile_updates or {}
        preference_updates = preference_updates or {}

        gambler = self._get_gambler_row(gambler_id)
        preferences = self._get_preferences_row(gambler_id)
        if not gambler or not preferences:
            raise ValidationException("Gambler profile not found.")

        merged_profile = {
            "full_name": profile_updates.get("full_name", gambler["full_name"]),
            "email": profile_updates.get("email", gambler["email"]),
            "phone_number": profile_updates.get("phone_number", gambler["phone_number"]),
            "initial_stake": profile_updates.get("initial_stake", gambler["initial_stake"]),
            "current_stake": profile_updates.get("current_stake", gambler["current_stake"]),
            "win_threshold": profile_updates.get("win_threshold", gambler["win_threshold"]),
            "loss_threshold": profile_updates.get("loss_threshold", gambler["loss_threshold"]),
        }
        merged_preferences = self._normalize_preferences(
            {
                "min_bet": preference_updates.get("min_bet", preferences["min_bet"]),
                "max_bet": preference_updates.get("max_bet", preferences["max_bet"]),
                "preferred_game_type": preference_updates.get("preferred_game_type", preferences["preferred_game_type"]),
                "session_game_limit": preference_updates.get("session_game_limit", preferences["session_game_limit"]),
                "notes": preference_updates.get("notes", preferences["notes"]),
            }
        )

        merged_profile["initial_stake"] = self._to_decimal(merged_profile["initial_stake"])
        merged_profile["current_stake"] = self._to_decimal(merged_profile["current_stake"])
        merged_profile["win_threshold"] = self._to_decimal(merged_profile["win_threshold"])
        merged_profile["loss_threshold"] = self._to_decimal(merged_profile["loss_threshold"])

        self._validate_profile_inputs(
            full_name=merged_profile["full_name"],
            email=merged_profile["email"],
            initial_stake=merged_profile["initial_stake"],
            win_threshold=merged_profile["win_threshold"],
            loss_threshold=merged_profile["loss_threshold"],
            preferences=merged_preferences,
            current_stake=merged_profile["current_stake"],
        )

        execute_many(
            [
                (
                    """
                    UPDATE gamblers
                    SET full_name = %s, email = %s, phone_number = %s, current_stake = %s,
                        initial_stake = %s, win_threshold = %s, loss_threshold = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        merged_profile["full_name"].strip(),
                        merged_profile["email"].strip().lower(),
                        merged_profile["phone_number"].strip() if merged_profile["phone_number"] else None,
                        merged_profile["current_stake"],
                        merged_profile["initial_stake"],
                        merged_profile["win_threshold"],
                        merged_profile["loss_threshold"],
                        self._now(),
                        gambler_id,
                    ),
                ),
                (
                    """
                    UPDATE betting_preferences
                    SET min_bet = %s, max_bet = %s, preferred_game_type = %s,
                        session_game_limit = %s, notes = %s, updated_at = %s
                    WHERE gambler_id = %s
                    """,
                    (
                        merged_preferences["min_bet"],
                        merged_preferences["max_bet"],
                        merged_preferences["preferred_game_type"],
                        merged_preferences["session_game_limit"],
                        merged_preferences["notes"],
                        self._now(),
                        gambler_id,
                    ),
                ),
            ]
        )

    def retrieve_gambler_statistics(self, gambler_id):
        row = self._get_joined_profile(gambler_id)
        if not row:
            raise ValidationException("Gambler profile not found.")

        total_bets = row["total_bets"]
        total_wins = row["total_wins"]
        win_rate = (total_wins / total_bets * 100) if total_bets else 0.0

        return GamblerStatistics(
            gambler_id=row["id"],
            full_name=row["full_name"],
            email=row["email"],
            phone_number=row["phone_number"],
            current_stake=row["current_stake"],
            initial_stake=row["initial_stake"],
            win_threshold=row["win_threshold"],
            loss_threshold=row["loss_threshold"],
            threshold_status=self._get_threshold_status(row["current_stake"], row["win_threshold"], row["loss_threshold"]),
            total_bets=total_bets,
            total_wins=total_wins,
            total_losses=row["total_losses"],
            total_winnings=row["total_winnings"],
            net_profit_loss=row["current_stake"] - row["initial_stake"],
            win_rate=round(win_rate, 2),
            account_status=row["account_status"],
            preferred_game_type=row["preferred_game_type"],
            min_bet=row["min_bet"],
            max_bet=row["max_bet"],
            session_game_limit=row["session_game_limit"],
            notes=row["notes"],
        )

    def validate_gambler_eligibility(self, gambler_id):
        row = self._get_joined_profile(gambler_id)
        if not row:
            raise ValidationException("Gambler profile not found.")

        current_stake = self._to_decimal(row["current_stake"])
        reasons = []

        if row["account_status"] != "ACTIVE":
            reasons.append("Account is not active.")
        if current_stake < self.minimum_stake:
            reasons.append(f"Current stake is below the minimum stake of {self.minimum_stake:.2f}.")
        if current_stake <= self._to_decimal(row["loss_threshold"]):
            reasons.append("Current stake has already reached the loss threshold.")
        if current_stake >= self._to_decimal(row["win_threshold"]):
            reasons.append("Current stake has already reached the win threshold.")

        return {
            "is_eligible": len(reasons) == 0,
            "reasons": reasons,
        }

    def reset_gambler_profile(self, gambler_id, new_initial_stake=None):
        gambler = self._get_gambler_row(gambler_id)
        if not gambler:
            raise ValidationException("Gambler profile not found.")

        base_stake = self._to_decimal(new_initial_stake) if new_initial_stake is not None else self._to_decimal(gambler["initial_stake"])
        if base_stake < self.minimum_stake:
            raise ValidationException(f"Reset stake must be at least {self.minimum_stake:.2f}.")

        initial_stake = self._to_decimal(gambler["initial_stake"])
        win_gap = self._to_decimal(gambler["win_threshold"]) - initial_stake
        loss_gap = initial_stake - self._to_decimal(gambler["loss_threshold"])
        new_win_threshold = self._round_money(base_stake + win_gap)
        new_loss_threshold = self._round_money(max(Decimal("0"), base_stake - loss_gap))

        execute_write(
            """
            UPDATE gamblers
            SET initial_stake = %s, current_stake = %s, win_threshold = %s, loss_threshold = %s,
                total_bets = 0, total_wins = 0, total_losses = 0, total_winnings = 0,
                account_status = 'ACTIVE', updated_at = %s
            WHERE id = %s
            """,
            (
                base_stake,
                base_stake,
                new_win_threshold,
                new_loss_threshold,
                self._now(),
                gambler_id,
            ),
        )

        return {
            "new_initial_stake": base_stake,
            "new_win_threshold": new_win_threshold,
            "new_loss_threshold": new_loss_threshold,
        }

    def deactivate_gambler(self, gambler_id):
        execute_write(
            "UPDATE gamblers SET account_status = 'INACTIVE', updated_at = %s WHERE id = %s",
            (self._now(), gambler_id),
        )

    def list_gamblers(self):
        return fetch_all(
            """
            SELECT id, full_name, email, phone_number, current_stake, account_status
            FROM gamblers
            ORDER BY id
            """
        )

    def find_gambler_by_email(self, email):
        return fetch_one(
            """
            SELECT id, full_name, email, phone_number, current_stake, account_status
            FROM gamblers
            WHERE email = %s
            """,
            (email.strip().lower(),),
        )

    def _validate_profile_inputs(self, full_name, email, initial_stake, win_threshold, loss_threshold, preferences, current_stake=None):
        if not full_name or not full_name.strip():
            raise ValidationException("Full name is required.")
        if not email or "@" not in email:
            raise ValidationException("Enter a valid email.")
        if initial_stake < self.minimum_stake:
            raise ValidationException(f"Initial stake must be at least {self.minimum_stake:.2f}.")
        if win_threshold <= initial_stake:
            raise ValidationException("Win threshold must be greater than initial stake.")
        if loss_threshold < 0:
            raise ValidationException("Loss threshold cannot be negative.")
        if loss_threshold >= initial_stake:
            raise ValidationException("Loss threshold must be less than initial stake.")
        if current_stake is not None and current_stake < 0:
            raise ValidationException("Current stake cannot be negative.")

        min_bet = preferences.get("min_bet")
        max_bet = preferences.get("max_bet")
        if min_bet is None or min_bet <= 0:
            raise ValidationException("Minimum bet must be greater than zero.")
        if max_bet is None or max_bet < min_bet:
            raise ValidationException("Maximum bet must be greater than or equal to minimum bet.")
        if max_bet > initial_stake:
            raise ValidationException("Maximum bet cannot be greater than initial stake.")
        if preferences.get("preferred_game_type") not in GAME_TYPES:
            raise ValidationException("Choose a valid game type.")
        if preferences.get("session_game_limit", 0) <= 0:
            raise ValidationException("Session game limit must be greater than zero.")

    def _normalize_preferences(self, preferences):
        return {
            "min_bet": self._to_decimal(preferences.get("min_bet")),
            "max_bet": self._to_decimal(preferences.get("max_bet")),
            "preferred_game_type": preferences.get("preferred_game_type", "CUSTOM"),
            "session_game_limit": int(preferences.get("session_game_limit", 20)),
            "notes": preferences.get("notes"),
        }

    def _get_joined_profile(self, gambler_id):
        return fetch_one(
            """
            SELECT g.*, bp.min_bet, bp.max_bet, bp.preferred_game_type, bp.session_game_limit, bp.notes
            FROM gamblers g
            JOIN betting_preferences bp ON bp.gambler_id = g.id
            WHERE g.id = %s
            """,
            (gambler_id,),
        )

    def _get_gambler_row(self, gambler_id):
        return fetch_one("SELECT * FROM gamblers WHERE id = %s", (gambler_id,))

    def _get_preferences_row(self, gambler_id):
        return fetch_one("SELECT * FROM betting_preferences WHERE gambler_id = %s", (gambler_id,))

    def _ensure_initial_stake_transaction(self, gambler_id):
        existing_transaction = fetch_one(
            """
            SELECT id
            FROM stake_transactions
            WHERE gambler_id = %s AND transaction_type = 'INITIAL_STAKE'
            LIMIT 1
            """,
            (gambler_id,),
        )
        if existing_transaction:
            return

        gambler = self._get_gambler_row(gambler_id)
        execute_write(
            """
            INSERT INTO stake_transactions (
                gambler_id, transaction_type, amount, balance_before, balance_after, note, created_at
            )
            VALUES (%s, 'INITIAL_STAKE', %s, %s, %s, %s, %s)
            """,
            (
                gambler_id,
                gambler["initial_stake"],
                Decimal("0.00"),
                gambler["initial_stake"],
                "Initial stake backfilled for existing user",
                self._now(),
            ),
        )

    @staticmethod
    def _get_threshold_status(current_stake, win_threshold, loss_threshold):
        if current_stake >= win_threshold:
            return "WIN_THRESHOLD_REACHED"
        if current_stake <= loss_threshold:
            return "LOSS_THRESHOLD_REACHED"
        return "WITHIN_LIMITS"

    @staticmethod
    def _to_decimal(value):
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _round_money(value):
        return value.quantize(Decimal("0.01"))

    @staticmethod
    def _now():
        return datetime.now().isoformat(timespec="seconds")
