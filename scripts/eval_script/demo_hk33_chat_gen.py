from mmengine.config import read_base

with read_base():    
    # 数据集：BBH
    from opencompass.configs.datasets.bbh.bbh_gen_4a31fa import \
        bbh_datasets
    # 数据集：MMLU-Pro
    from opencompass.configs.datasets.mmlu_pro.mmlu_pro_0shot_cot_gen_08c1de import \
        mmlu_pro_datasets
    # 数据集：TruthfulQA
    from opencompass.configs.datasets.truthfulqa.truthfulqa_gen import \
        truthfulqa_datasets
    # 数据集：FewCLUE/bustm
    from opencompass.configs.datasets.FewCLUE_bustm.FewCLUE_bustm_gen_634f41 import \
        bustm_datasets
    # 数据集：FewCLUE/ocnli
    from opencompass.configs.datasets.FewCLUE_ocnli_fc.FewCLUE_ocnli_fc_gen_f97a97 import \
        ocnli_fc_datasets
    # 数据集：CLUE/cluewsc
    from opencompass.configs.datasets.FewCLUE_cluewsc.FewCLUE_cluewsc_gen_c68933 import \
        cluewsc_datasets
    # 数据集：FewCLUE/prstmt
    from opencompass.configs.datasets.FewCLUE_eprstmt.FewCLUE_eprstmt_gen_740ea0 import \
        eprstmt_datasets

    # # 数据集：CivilComments（API方式不支持）
    # from opencompass.configs.datasets.civilcomments.civilcomments_clp_a3c5fd import \
    #     civilcomments_datasets

datasets = []

for d in bbh_datasets:
    d['reader_cfg']['test_range'] = '[0:1]' # 每个数据集只取1个样本

for d in mmlu_pro_datasets:
    d['reader_cfg']['test_range'] = '[0:5]'

for d in truthfulqa_datasets:
    d['reader_cfg']['test_range'] = '[0:5]' 

for d in bustm_datasets:
    d['reader_cfg']['test_range'] = '[0:5]'

for d in ocnli_fc_datasets:
    d['reader_cfg']['test_range'] = '[0:5]'

for d in cluewsc_datasets:
    d['reader_cfg']['test_range'] = '[0:5]'

for d in eprstmt_datasets:
    d['reader_cfg']['test_range'] = '[0:5]'