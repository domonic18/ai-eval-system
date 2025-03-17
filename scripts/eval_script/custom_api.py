import os
from opencompass.models import OpenAISDK


internlm_url = os.getenv("API_URL")        # 自定义 API 服务地址
internlm_api_key = os.getenv("API_KEY")    # 自定义 API Key
internlm_model = os.getenv("MODEL")        # 自定义 API 模型

models = [
    dict(
        type=OpenAISDK,
        path=internlm_model,    # 请求服务时的 model name
        key=internlm_api_key, 
        openai_api_base=internlm_url, 
        rpm_verbose=True,                   # 是否打印请求速率
        query_per_second=0.16,              # 服务请求速率
        max_out_len=1024,                   # 最大输出长度
        max_seq_len=4096,                   # 最大输入长度
        temperature=0.01,                   # 生成温度
        batch_size=1,                       # 批处理大小
        retry=3,                            # 重试次数
    )
]