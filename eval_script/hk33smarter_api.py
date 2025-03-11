from opencompass.models import OpenAISDK


internlm_url = 'https://guanghua-api.hk33smarter.com/v1'                    # 前面获得的 api 服务地址
internlm_api_key = "sk-8B8KptRvxQnPTVsH7665380d95A748F7BcAdA3E4279c6bAe"    # 前面获得的 API Key

models = [
    dict(
        type=OpenAISDK,
        path='Qwen/qwen2-1.5b-instruct',    # 请求服务时的 model name
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


# from mmengine.config import read_base

# with read_base():
#     from opencompass.configs.datasets.demo.demo_gsm8k_chat_gen import \
#         gsm8k_datasets
#     from opencompass.configs.datasets.demo.demo_math_chat_gen import \
#         math_datasets
    # from opencompass.configs.models.openai.hk33smarter_api import \
    #     models as hk33smarter_api

# datasets = gsm8k_datasets + math_datasets
models = models


work_dir = 'outputs/hk33smarter_api'