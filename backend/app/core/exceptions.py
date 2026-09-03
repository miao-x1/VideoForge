"""Provider 相关异常定义。"""
from __future__ import annotations


class ProviderError(Exception):
    """Provider 基础异常。"""

    def __init__(self, provider: str, message: str, error_code: str = "PROVIDER_ERROR"):
        self.provider = provider
        self.message = message
        self.error_code = error_code
        super().__init__(f"[{provider}] {message}")


class ProviderNotConfiguredError(ProviderError):
    """Provider 未配置 API Key 或参数不完整。"""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            provider=provider,
            message=f"Provider 未正确配置: {detail}" if detail else "Provider 未正确配置 (缺少 API Key 或参数)",
            error_code="PROVIDER_NOT_CONFIGURED",
        )


class ProviderUnavailableError(ProviderError):
    """Provider 初始化失败或服务不可用。"""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            provider=provider,
            message=f"Provider 不可用: {detail}" if detail else "Provider 不可用",
            error_code="PROVIDER_UNAVAILABLE",
        )


class InsufficientBalanceError(ProviderError):
    """Provider 账户余额不足。"""

    def __init__(self, provider: str, detail: str = ""):
        super().__init__(
            provider=provider,
            message=f"账户余额不足: {detail}" if detail else "账户余额不足，请充值后重试",
            error_code="INSUFFICIENT_BALANCE",
        )


class ModelUnavailableError(ProviderError):
    """所有真实模型均不可用,或用户指定的模型不可用。"""

    def __init__(self, provider: str = "model_router", message: str = "", error_code: str = "MODEL_UNAVAILABLE"):
        if not message:
            message = "所有已配置模型均不可用，请检查 API Key 和账户状态"
        super().__init__(provider=provider, message=message, error_code=error_code)
