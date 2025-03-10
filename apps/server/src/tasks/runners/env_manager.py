import json
from typing import Dict
from pydantic import ValidationError


class EnvManager:
    def __init__(self, eval_id: int):
        self.eval_id = eval_id
        self.vars: Dict[str, str] = {}  # 明确类型注解
        
    def load_from_json_str(self, json_str: str) -> None:
        """从JSON字符串加载环境变量
        
        Args:
            json_str: JSON格式的字符串，例如 '{"API_KEY": "sk-xxx", "MODEL": "gpt-4"}'
            
        Raises:
            ValueError: 当JSON解析失败或格式不符合要求时
        """
        try:
            env_dict = json.loads(json_str)
            if not isinstance(env_dict, dict):
                raise ValueError("JSON数据必须为字典格式")
                
            # 验证键值类型并过滤非字符串值
            filtered_vars = {}
            for k, v in env_dict.items():
                if not isinstance(k, str):
                    raise ValueError(f"环境变量键必须为字符串类型，发现类型: {type(k)}")
                if not isinstance(v, (str, int, float)):
                    raise ValueError(f"环境变量值必须为基本类型，键 '{k}' 的值为类型: {type(v)}")
                filtered_vars[k] = str(v)  # 统一转换为字符串
                
            self.vars = filtered_vars
            
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON格式: {str(e)}") from e
        except ValueError as e:
            raise  # 直接抛出已处理的验证错误
            
    # 接收传入的Json结构体获得环境变量
    def load_env_json(self, env_json: dict):
        """兼容原有接口"""
        self.vars = {str(k): str(v) for k, v in env_json.items()}
    
    def inject_to_command(self, command: str) -> str:
        """生成带环境变量的完整命令"""
        env_str = " ".join([f"env {k}={v}" for k, v in self.vars.items()])
        return f"{env_str} {command}"
    
    # def validate(self):
    #     """安全检查"""
    #     if 'API_KEY' in self.vars and len(self.vars['API_KEY']) < 8:
    #         raise SecurityError("API密钥强度不足")