class ValidationException(Exception):
    def __init__(self, message, field_name=None, attempted_value=None):
        self.field_name = field_name
        self.attempted_value = attempted_value
        super().__init__(message)
