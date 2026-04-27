from dataclasses import dataclass
import math
import re

from app.exceptions import (
    BetValidationException,
    LimitValidationException,
    ProbabilityValidationException,
    StakeValidationException,
    TextValidationException,
    ValidationErrorType,
    ValidationException,
)


@dataclass(frozen=True)
class ValidationConfig:
    min_stake: float = 100.0
    max_stake: float = 1_000_000.0
    min_bet: float = 0.01
    max_bet: float = 100_000.0
    min_probability: float = 0.0001
    max_probability: float = 0.9999
    strict_mode: bool = True
    allow_zero_stake: bool = False


class InputValidator:
    def __init__(self, config=None):
        self.config = config or ValidationConfig()

    def validate_initial_stake(self, value, field_name="initial_stake"):
        value = self.parse_and_validate_numeric(value, field_name)
        if value < self.config.min_stake:
            raise StakeValidationException(
                f"Initial stake must be at least {self.config.min_stake:.2f}.",
                field_name,
                value,
            )
        if value > self.config.max_stake:
            raise StakeValidationException(
                f"Initial stake must be at most {self.config.max_stake:.2f}.",
                field_name,
                value,
            )
        return value

    def validate_bet_amount(self, value, current_stake=None, min_bet=None, max_bet=None, field_name="bet_amount"):
        value = self.parse_and_validate_numeric(value, field_name)
        minimum = self.config.min_bet if min_bet is None else min_bet
        maximum = self.config.max_bet if max_bet is None else max_bet
        if value < minimum:
            raise BetValidationException(f"Bet amount must be at least {minimum:.2f}.", field_name, value)
        if value > maximum:
            raise BetValidationException(f"Bet amount must be at most {maximum:.2f}.", field_name, value)
        if current_stake is not None and value > current_stake:
            raise BetValidationException("Bet amount cannot be greater than the current stake.", field_name, value)
        return value

    def validate_limits(self, initial_stake, win_threshold, loss_threshold):
        initial_stake = self.parse_and_validate_numeric(initial_stake, "initial_stake")
        win_threshold = self.parse_and_validate_numeric(win_threshold, "win_threshold")
        loss_threshold = self.parse_and_validate_numeric(loss_threshold, "loss_threshold")
        if win_threshold <= initial_stake:
            raise LimitValidationException("Win threshold must be greater than initial stake.", "win_threshold", win_threshold)
        if loss_threshold < 0:
            raise LimitValidationException("Loss threshold cannot be negative.", "loss_threshold", loss_threshold)
        if loss_threshold >= initial_stake:
            raise LimitValidationException("Loss threshold must be less than initial stake.", "loss_threshold", loss_threshold)
        return win_threshold, loss_threshold

    def parse_and_validate_numeric(self, value, field_name="value"):
        if value is None or value == "":
            raise ValidationException(f"{field_name} is required.", ValidationErrorType.NULL_ERROR, field_name, value)
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as error:
            raise ValidationException(
                f"Enter a valid number for {field_name}.",
                ValidationErrorType.NUMERIC_ERROR,
                field_name,
                value,
            ) from error
        if math.isnan(numeric_value) or math.isinf(numeric_value):
            raise ValidationException(
                f"{field_name} cannot be NaN or Infinity.",
                ValidationErrorType.NUMERIC_ERROR,
                field_name,
                value,
            )
        return numeric_value

    def validate_stake_non_negative(self, value, field_name="stake"):
        value = self.parse_and_validate_numeric(value, field_name)
        if value < 0:
            raise StakeValidationException(f"{field_name} cannot be negative.", field_name, value)
        if value == 0 and not self.config.allow_zero_stake and self.config.strict_mode:
            raise StakeValidationException(f"{field_name} cannot be zero.", field_name, value)
        return value

    def validate_probability(self, value, field_name="win_probability"):
        value = self.parse_and_validate_numeric(value, field_name)
        if value < self.config.min_probability or value > self.config.max_probability:
            raise ProbabilityValidationException(
                f"{field_name} must be between {self.config.min_probability:.4f} and {self.config.max_probability:.4f}.",
                field_name,
                value,
            )
        return value

    def validate_name(self, value, field_name="full_name"):
        if not value or not value.strip():
            raise TextValidationException(f"{field_name} is required.", field_name, value)
        value = value.strip()
        if len(value) < 2:
            raise TextValidationException(f"{field_name} must be at least 2 characters long.", field_name, value)
        if len(value) > 100:
            raise TextValidationException(f"{field_name} must be at most 100 characters long.", field_name, value)
        if not re.match(r"^[a-zA-Z\s\-']+$", value):
            raise TextValidationException(f"{field_name} can only contain letters, spaces, hyphens, and apostrophes.", field_name, value)
        return value

    def validate_email(self, value, field_name="email"):
        if not value or not value.strip():
            raise TextValidationException(f"{field_name} is required.", field_name, value)
        value = value.strip()
        if len(value) > 100:
            raise TextValidationException(f"{field_name} must be at most 100 characters long.", field_name, value)
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise TextValidationException(f"Enter a valid email address for {field_name}.", field_name, value)
        return value

    def validate_phone_number(self, value, field_name="phone_number"):
        if not value or not value.strip():
            raise TextValidationException(f"{field_name} is required.", field_name, value)
        value = value.strip()
        if len(value) > 20:
            raise TextValidationException(f"{field_name} must be at most 20 characters long.", field_name, value)
        if not re.match(r'^[\d\s\-\(\)\+]+$', value):
            raise TextValidationException(f"{field_name} can only contain digits, spaces, hyphens, parentheses, and plus sign.", field_name, value)
        digits_only = re.sub(r'\D', '', value)
        if len(digits_only) < 7:
            raise TextValidationException(f"{field_name} must contain at least 7 digits.", field_name, value)
        return value


class SafeInputHandler:
    def __init__(self, validator=None):
        self.validator = validator or InputValidator()

    def prompt_text(self, label, allow_empty=False):
        while True:
            value = input(f"{label}: ").strip()
            if value or allow_empty:
                return value if value else None
            print(f"{label} is required.")

    def prompt_number(self, label, validator_fn=None, **validator_kwargs):
        while True:
            raw_value = input(f"{label}: ").strip()
            try:
                if validator_fn is None:
                    return self.validator.parse_and_validate_numeric(raw_value, label)
                return validator_fn(raw_value, **validator_kwargs)
            except ValidationException as error:
                print(error)

    def prompt_int(self, label, minimum=None):
        while True:
            raw_value = input(f"{label}: ").strip()
            try:
                value = int(raw_value)
            except ValueError:
                print(f"Enter a whole number for {label}.")
                continue
            if minimum is not None and value < minimum:
                print(f"{label} must be at least {minimum}.")
                continue
            return value

    def prompt_name(self, label="Name"):
        while True:
            value = input(f"{label}: ").strip()
            try:
                return self.validator.validate_name(value, label.lower().replace(" ", "_"))
            except ValidationException as error:
                print(error)

    def prompt_email(self, label="Email"):
        while True:
            value = input(f"{label}: ").strip()
            try:
                return self.validator.validate_email(value, label.lower())
            except ValidationException as error:
                print(error)

    def prompt_phone_number(self, label="Phone Number"):
        while True:
            value = input(f"{label}: ").strip()
            try:
                return self.validator.validate_phone_number(value, label.lower().replace(" ", "_"))
            except ValidationException as error:
                print(error)
