from enum import Enum


class ValidationErrorType(Enum):
    STAKE_ERROR = "STAKE_ERROR"
    BET_ERROR = "BET_ERROR"
    LIMIT_ERROR = "LIMIT_ERROR"
    PROBABILITY_ERROR = "PROBABILITY_ERROR"
    NUMERIC_ERROR = "NUMERIC_ERROR"
    RANGE_ERROR = "RANGE_ERROR"
    NULL_ERROR = "NULL_ERROR"
    TEXT_ERROR = "TEXT_ERROR"


class ValidationException(Exception):
    def __init__(self, message, error_type=ValidationErrorType.RANGE_ERROR, field_name=None, attempted_value=None):
        self.error_type = error_type
        self.field_name = field_name
        self.attempted_value = attempted_value
        super().__init__(message)


class StakeValidationException(ValidationException):
    def __init__(self, message, field_name=None, attempted_value=None):
        super().__init__(message, ValidationErrorType.STAKE_ERROR, field_name, attempted_value)


class BetValidationException(ValidationException):
    def __init__(self, message, field_name=None, attempted_value=None):
        super().__init__(message, ValidationErrorType.BET_ERROR, field_name, attempted_value)


class LimitValidationException(ValidationException):
    def __init__(self, message, field_name=None, attempted_value=None):
        super().__init__(message, ValidationErrorType.LIMIT_ERROR, field_name, attempted_value)


class ProbabilityValidationException(ValidationException):
    def __init__(self, message, field_name=None, attempted_value=None):
        super().__init__(message, ValidationErrorType.PROBABILITY_ERROR, field_name, attempted_value)


class TextValidationException(ValidationException):
    def __init__(self, message, field_name=None, attempted_value=None):
        super().__init__(message, ValidationErrorType.TEXT_ERROR, field_name, attempted_value)
