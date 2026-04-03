class CsmarMetadataError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "vendor_unknown",
        retriable: bool = False,
        vendor_message: str = "",
        hint: str = "",
        retry_after_seconds: int | None = None,
        suggested_args_patch: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retriable = retriable
        self.vendor_message = vendor_message or message
        self.hint = hint
        self.retry_after_seconds = retry_after_seconds
        self.suggested_args_patch = suggested_args_patch
