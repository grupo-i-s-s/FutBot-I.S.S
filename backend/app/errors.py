class AppError(Exception):
    def __init__(self, code: str, message: str, fields: dict[str, str] | None = None, *, diagnostics: list[dict] | None=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields or {}
        self.diagnostics = diagnostics
