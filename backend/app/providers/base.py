"""Provider 统一根抽象。

任务书要求建立统一 Provider 抽象层级:
    ModelProvider
      -> TextModelProvider   (LLM)
      -> ImageModelProvider
      -> VideoModelProvider
      -> VoiceModelProvider
      -> MusicModelProvider

各类型 Provider 基类继承本根类,获得统一的身份标识与健康检查契约,
Agent 不直接耦合具体厂商 API,仅依赖本抽象层。

失败契约:Provider 在 API 不可用/余额不足/鉴权失败时,必须抛出
core.exceptions.ProviderError(携带 error_code/provider/message/retryable),
不得返回假结果或静默降级到 Mock(生产环境)。
"""
from __future__ import annotations

from abc import ABC


class ModelProvider(ABC):
    """所有 Provider 的统一根抽象。

    子类约定:
      - 设置 provider_type 类属性标识自身类型
      - 可覆写 name 属性返回具体模型/服务名
      - 可覆写 health_check() 实现真实可用性探测
    """

    # Provider 类型标识,子类覆写: text | image | video | voice | music | embedding
    provider_type: str = "model"

    @property
    def name(self) -> str:
        """Provider/模型名称,默认返回 provider_type,子类可覆写为具体模型名。"""
        return self.provider_type

    async def health_check(self) -> bool:
        """探测 Provider 是否可用(默认 True,子类可覆写为真实探测)。

        可用于 ModelRouter 在无可用模型时给出更精确的"服务暂不可用"原因。
        """
        return True
