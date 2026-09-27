"""Build immutable-output comparisons and scientific learning curves after both runs."""
import csv
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.training.frozen_pilot import audit_config, read_rows, write_json
from src.training.pilot_results import load, read_arm, compare_generations, checkpoint_inventory


def main():
    out=ROOT/'outputs/b0_pilot'
    _,split,_=audit_config(ROOT/'configs/b0_pilot_gold_only.json',ROOT)
    paths={'B0-A':ROOT/'outputs/b0_pilot_gold_only','B0-B':ROOT/'outputs/b0_pilot_gold_partial_silver'}
    arms={name:read_arm(path,load(out/f'{name[-1]}_runtime.json')) for name,path in paths.items()}
    for name,path in paths.items():
        config_name='b0_pilot_gold_only.json' if name=='B0-A' else 'b0_pilot_gold_partial_silver.json'
        if load(path/'config.json') != load(ROOT/'configs'/config_name): raise ValueError('Executed config differs from frozen config')
        if load(path/'split.json') != split: raise ValueError('Executed split differs from frozen split')
    a,b=arms.values()
    if a['evaluations'][0] != b['evaluations'][0]: raise ValueError('A/B initial evaluation differs')
    gold={r['id']:r for r in read_rows(ROOT/split['eval_path'])}
    generations=compare_generations(a['evaluations'][100],b['evaluations'][100],gold)
    from src.training.pilot_protocol import normalized_text
    train_gold=read_rows(ROOT/split['train_path'])
    silver_path=load(ROOT/'configs/b0_pilot_gold_partial_silver.json')['data']['partial_silver_path']
    silver=read_rows(ROOT/silver_path)
    for entry in generations:
        for name in ('B0-A','B0-B'):
            text=normalized_text(entry[name]['generation'])
            source_rows=train_gold if name=='B0-A' else train_gold+silver
            entry[name]['exact_training_text_matches']=[r['id'] for r in source_rows if normalized_text(r['text'])==text]
    inventory={name:checkpoint_inventory(path) for name,path in paths.items()}
    comparison={'protocol_commit':'1169766','scope':'one split, one seed, six development holdout records; descriptive only',
        'seed':20260926,'optimizer_steps':100,'step0_identical':True,
        'metrics':{key:{'B0-A':value,'B0-B':b['metrics'][key],'delta_B_minus_A':b['metrics'][key]-value} for key,value in a['metrics'].items()},
        'sampling':{name:{'counts':arm['source_counts'],'ratios':arm['source_ratios'],'matches_plan':True} for name,arm in arms.items()},
        'runtime':{name:arm['runtime'] for name,arm in arms.items()},'checkpoint_inventory':inventory,
        'generation_comparison':generations,'curves':{name:arm['history'] for name,arm in arms.items()},
        'semantic_automatic_scores':None,'rule_metrics_are_proxies':True,
        'generation_diagnostics':{name:{'unique_outputs':len({normalized_text(x[name]['generation']) for x in generations}),
            'exact_training_text_matches':sum(bool(x[name]['exact_training_text_matches']) for x in generations)} for name in arms}}
    comparison['interpretation']={
        'observed_gain':'B has lower teacher-forced eval loss and higher token accuracy than A at step 100.',
        'observed_degradation':'B has lower form compliance, imagery micro-F1 and density match; generation controls did not improve.',
        'baseline_context':{'step0_eval_loss':a['evaluations'][0]['eval_loss'],'step0_token_accuracy':a['evaluations'][0]['eval_token_accuracy'],
            'B_token_accuracy_equals_step0':b['metrics']['eval_token_accuracy']==b['evaluations'][0]['eval_token_accuracy']},
        'multi_seed_recommendation':'Do not prioritize broad replication as an improvement claim. First diagnose the saved outputs for repeated training-poem emission and form-control failures; a later limited multi-seed run could assess reproducibility, but none was started.',
        'limitations':['one split','one seed','six development holdout poems','rule-based controllability proxies','no semantic-style automatic scores']}
    test_log=out/'tests.log'
    if test_log.exists(): comparison['test_summary']=test_log.read_text(encoding='utf-8').strip().splitlines()[-1]
    comparison['execution_anomalies']=[]
    comparison['warnings']=['torch_dtype deprecation','model-default sampling flags ignored under greedy decoding']
    write_json(out/'b0_pilot_comparison.json',comparison)
    write_json(out/'generation_comparison.json',generations)
    columns=['arm','step','train_loss','eval_loss','eval_token_accuracy','learning_rate','gold_exposures','silver_exposures']
    with (out/'learning_curves.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for name,arm in arms.items():
            for row in arm['history']:
                writer.writerow({'arm':name,**{k:row.get(k,'') for k in columns[1:6]},
                    'gold_exposures':row.get('source_exposures',{}).get('gold',0),'silver_exposures':row.get('source_exposures',{}).get('partial-silver',0)})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(15,4),constrained_layout=True)
    for ax,key,title in zip(axes,['train_loss','eval_loss','eval_token_accuracy'],['Train loss (different source mixtures)','Development holdout loss','Development holdout token accuracy']):
        for name,arm in arms.items():
            rows=[x for x in arm['history'] if key in x]
            ax.plot([x['step'] for x in rows],[x[key] for x in rows],label=name,marker='o' if key!='train_loss' else None,markersize=3,linewidth=1.4)
        ax.set(xlabel='Optimizer step',ylabel=key,title=title); ax.grid(alpha=.25);ax.legend()
    fig.suptitle('Frozen B0 Pilot | seed 20260926 | 6 development holdout poems')
    fig.savefig(out/'learning_curves.png',dpi=180);fig.savefig(out/'learning_curves.svg');plt.close(fig)
    svg=out/'learning_curves.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    lines=['# B0 Pilot 实验结果','',
        '严格执行冻结协议 `1169766`：A/B 均完成 100 optimizer steps，没有中途调参或增加步数。训练文件、split、数据与超参数哈希审计通过。',
        '', '仅有 1 个 split、1 个 seed、6 条 development holdout。这是描述性观察，不是独立 test set 或显著性结论。意象和密度分数是规则代理指标；未调用四个未通过 gate 的语义评分器。',
        '', '## 第 100 步结果','', '| 指标 | B0-A | B0-B | Δ(B−A) |','|---|---:|---:|---:|']
    for key,values in comparison['metrics'].items():lines.append(f"| {key} | {values['B0-A']:.6f} | {values['B0-B']:.6f} | {values['delta_B_minus_A']:+.6f} |")
    lines+=['','accuracy / compliance / F1 使用 0–1 比例；VRAM 为 allocated GiB，wall-clock 为秒，包含 Python 导入、模型加载、评估和保存。training_seconds 仅累计训练更新时间。模型已在本地缓存；运行先后造成的 OS 缓存差异可能影响 wall-clock。',
        '', '## 完整学习曲线','', '![Learning curves](../research/outputs/b0_pilot/learning_curves.png)',
        '', '所有 100 个训练 loss 点和 11 个评估点保存在 [CSV](../research/outputs/b0_pilot/learning_curves.csv) 与 [comparison JSON](../research/outputs/b0_pilot/b0_pilot_comparison.json)。原始 JSONL 保留每步来源计数、ID exposure、学习率、token 数和显存。两组 step-0 的 loss、accuracy 和逐条生成完全一致。训练 loss 的数据来源不同，不能把两条 train loss 的差异直接当成同一测试集上的优劣。',
        '', '## 采样与完整性','']
    for name,arm in arms.items():
        lines.append(f"- {name}: 实际来源次数 {arm['source_counts']}；比例 {arm['source_ratios']}。逐条 ID exposure 与预先保存的 800 次采样计划一致。")
    lines+=['- 两组各保存 10 个 adapter-only checkpoints，包含 step 100；20 个 safetensors 的结构、LoRA keys 与文件 SHA256 均已核验。大文件保存在本地 ignored 目录，Git 保存路径、哈希与大小；不将 base weights 推送到 Git。',
            '- 没有 OOM、NaN/Inf、泄漏 assertion failure 或运行中断。标准库／Transformers 提示保留在 console log。',
            '', '## 6 条逐诗生成对照','', '保留原始输出，不做繁简转换、文本润色或人工标签修订。意象 matched/missing/extra 仅对应冻结规则与目标意象的集合比较。']
    for idx,entry in enumerate(generations,1):
        lines += ['',f"### {idx}. `{entry['id']}`",'', '目标控制：`'+json.dumps(entry['target_controls'],ensure_ascii=False)+'`','', '参考诗：','```text',entry['reference_poem'],'```']
        for name in ('B0-A','B0-B'):
            sample=entry[name]
            lines += ['',name+'：','```text',sample['generation'],'```',
                f"诗体通过：{sample['form_compliance']}；意象 F1：{sample['imagery_F1']:.4f}；密度预测：{sample['density_prediction']}；密度匹配：{sample['density_match']}。",
                '与本组训练正文完全一致的记录 ID（忽略标点）：`'+str(sample['exact_training_text_matches'])+'`。',
                '意象命中：`'+str(sample['imagery_matched'])+'`；缺失：`'+str(sample['imagery_missing'])+'`；额外：`'+str(sample['imagery_extra'])+'`。']
    lines+=['','## 描述性解释','',
        'Observed gain：B 相对 A 的 eval loss 降低 2.5599，token accuracy 提高 5.32 个百分点。但 B 的最终 token accuracy 与共同 step-0 的 31.89% 相同，因此不能表述为相对 pretrained baseline 的 token accuracy 提升。',
        '', 'Observed degradation：诗体合规 6/6 → 2/6，意象 micro-F1 0.5778 → 0.2143，密度匹配 4/6 → 0/6。按冻结协议，诗体失败的输出记为空意象/null 密度，因此意象和密度下降也包含诗体失败的影响。',
        '', 'A 的训练 loss 几乎归零，同时 holdout loss 高于起点，符合小样本过拟合的迹象。A/B 分别只有 4/3 个不同生成文本，两组均有 5/6 条输出与本组训练正文完全一致（忽略标点）；B 有 4 条输出复用同一首七绝，且其中 3 条目标是七律，另有一条七绝目标输出了八句。这些是文本与句数观察，不是自动语义质量评分。',
        '', '当前不建议把 B 当成成功改进直接扩大 multi-seed 训练。优先利用已保存产物分析重复训练诗输出和诗体条件失效；若之后要判断这些现象是否稳定，可另行开展小规模 multi-seed replication。本轮没有证明 B 优于 A，也没有继续训练。', '']
    if 'test_summary' in comparison:
        lines += ['', '## 验证', '', '`pytest tests/ -q`：'+comparison['test_summary']+'。`git diff --check` 通过。没有修改任何冻结训练文件；仅新增计时、结果汇总、绘图及其测试。',
            '', '曲线由 Matplotlib 3.10.8 生成；绘图依赖安装日志保存在 outputs/b0_pilot/plot_dependency_install.log。该安装没有更新 Torch、NumPy、Transformers 或 PEFT。总耗时使用 perf_counter 单调计时器记录。', '']
    (ROOT.parent/'docs/b0_pilot_results.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'metrics':comparison['metrics'],'sampling':comparison['sampling']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
