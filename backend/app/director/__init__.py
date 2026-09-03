"""AI Director 层:作品级的理解、规划、决策与状态管理。

- project_state: ProjectState,贯穿全片的十二态作品状态(Agent 的"记忆")
- director(后续阶段):由 orchestrator 瘦身而来的阶段调度器
"""
from .project_state import ProjectState

__all__ = ["ProjectState"]
