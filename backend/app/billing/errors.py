"""计费错误。与上游 MiniMax 余额不足区分：这里是本平台钱包或用户未配 Key。"""
from __future__ import annotations


class BillingError(Exception):
    def __init__(self, message: str, http_status: int = 402):
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class WalletInsufficientError(BillingError):
    def __init__(self, message: str = "平台余额不足，请充值或改用自己的 API Key"):
        super().__init__(message, http_status=402)


class CredentialMissingError(BillingError):
    def __init__(self, message: str = "请先填写自己的 API Key，或改用平台模型并充值"):
        super().__init__(message, http_status=400)
