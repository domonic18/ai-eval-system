# 确保先导入被依赖的模型

# 模型加载顺序（按依赖关系从基础到复杂）
from .user import User          # 基础模型，被多个模型依赖
from .dataset import Dataset    # 依赖User，被Arena依赖
from .model import AIModel      # 依赖User，被ArenaParticipant依赖
from .arena import Arena, ArenaParticipant  # 依赖Dataset和AIModel
from .eval import Evaluation    # 独立模型，最后加载

# 显式导出模型类
__all__ = [
    'User',
    'Dataset',
    'AIModel',
    'Arena',
    'ArenaParticipant',
    'Evaluation'
]
