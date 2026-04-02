class CsmarMetadataError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "vendor_unknown",
        retriable: bool = False,
        vendor_message: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retriable = retriable
        self.vendor_message = vendor_message or message
