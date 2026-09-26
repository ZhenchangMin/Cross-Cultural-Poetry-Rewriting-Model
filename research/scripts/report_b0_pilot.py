"""Create a concise, source-linked account of measured pilot preparation results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'research/outputs/b0_training_pilot_20260926'
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
p = load(out / 'preflight.json')
s = load(out / 'smoke_not_experiment_result/result.json')
o = load(out / 'overfit_not_experiment_result/result.json')
protocol = load(out / 'protocol.json')
text = f'''# 真实 Qwen2.5-1.5B + LoRA：B0 Pilot 准备报告

本轮只执行10步真实模型smoke和固定8条overfit sanity，均标记为工程诊断、不是正式实验结果。未启动B0-A/B长时间正式训练，未改变标注系统，未新增人工审核或调用LLM进行标注。

## 环境及权重

- GPU：{p['gpu_name']}，总显存{p['gpu_total_bytes'] / 2**30:.2f} GiB，preflight空闲{p['gpu_free_bytes'] / 2**30:.2f} GiB。
- Torch：{p['versions']['torch']}；torch CUDA runtime：{p['torch_cuda_version']}；CUDA available={p['torch_cuda_available']}；bf16 supported={p['bf16_supported']}。
- Transformers {p['versions']['transformers']}、PEFT {p['versions']['peft']}。nvidia-smi的CUDA 13.1代表驱动支持上限，与PyTorch实际12.8 runtime区分。
- 项目盘剩余约{p['project_disk_free_bytes'] / 10**9:.1f} GB。checkpoint预算2 GiB，未重复下载。
- 本地真实weights大小{p['weights_bytes']:,} bytes，SHA256 `{p['weights_sha256']}`，与来源记录一致。
- Base revision：`{p['model_revision']}`。全部加载local_files_only，HF_HUB_OFFLINE=1；未加载历史LoRA，smoke和overfit各自从原base初始化新adapter。

## 数据与泄漏检查

来源保持24 Gold、825 Partial Silver。Gold完整人工review provenance、Silver规则provenance及采样权重保留；未引入unresolved、高风险残句或相关已知异文。四个development fold均检查ID、原文和已知variant隔离。

此次smoke实际训练池为fold 1的18条Gold＋825条Silver，另6条Gold保留未参与诊断；8条sanity子集为固定4 Gold＋4 Silver。正式全量配置则分别为24和849条，指标仅可称in-sample重构描述。若要held-out评估，必须按已保存4-fold清单先过滤Gold为18条再训练，不能拿全24条训练后再声称其中6条是held-out。

## 实测结果

| 指标 | Smoke | Overfit sanity |
|---|---:|---:|
'''
rows = [('通过', s['success'], o['success']), ('optimizer steps', s['optimizer_steps'], o['optimizer_steps']),
    ('初始固定probe NLL', f"{s['initial_teacher_forced']['loss']:.4f}", f"{o['initial_teacher_forced']['loss']:.4f}"),
    ('最终固定probe NLL', f"{s['final_teacher_forced']['loss']:.4f}", f"{o['final_teacher_forced']['loss']:.4f}"),
    ('teacher-forced token accuracy（初始→最终）', f"{s['initial_teacher_forced']['token_accuracy']:.1%} → {s['final_teacher_forced']['token_accuracy']:.1%}", f"{o['initial_teacher_forced']['token_accuracy']:.1%} → {o['final_teacher_forced']['token_accuracy']:.1%}"),
    ('peak allocated MiB', f"{s['peak_allocated_mib']:.1f}", f"{o['peak_allocated_mib']:.1f}"),
    ('peak reserved MiB', f"{s['peak_reserved_mib']:.1f}", f"{o['peak_reserved_mib']:.1f}"),
    ('训练optimizer step平均秒数', f"{s['mean_optimizer_step_seconds']:.3f}", f"{o['mean_optimizer_step_seconds']:.3f}"),
    ('训练tokens/sec（prompt＋target）', f"{s['tokens_per_training_second']:.1f}", f"{o['tokens_per_training_second']:.1f}"),
    ('checkpoint reload', s['checkpoint_reload_ok'], o['checkpoint_reload_ok']),
    ('重载后greedy输出一致', s['reload_generation_identical'], o['reload_generation_identical']),
    ('生成汉字精确复现训练target', f"{s['generation_exact_matches']}/8", f"{o['generation_exact_matches']}/8")]
for label, a, b in rows: text += f'| {label} | {a} | {b} |\n'
text += f"\nLoRA可训练参数{s['trainable_parameters']:,}，含adapter总参数{s['total_parameters']:,}，比例{s['trainable_ratio']:.4%}；仅LoRA参数可训练，B矩阵已有非零更新，梯度有限非零。\n\n"
text += f"Smoke首末随机训练batch的loss分别{s['first_training_batch_loss']:.4f}、{s['last_training_batch_loss']:.4f}；batch不同，效果比较使用表中的固定probe loss。smoke实际采样次数：`{s['trained_source_counts']}`，总计80次。短样本的实际比例可偏离配置30%/70%。\n\n"
text += '显存数字为该PyTorch进程的allocated/reserved峰值，不包含Windows桌面等进程。训练tokens/sec只覆盖forward/backward/optimizer训练段，不含模型加载、评估、保存和重载。849条全控制token检查未发现max_length=512截断。\n\n'
text += f"Checkpoint保存在 `{s['checkpoint']}` 与 `{o['checkpoint']}`；adapter/tokenizer文件只在本地保留，不提交二进制到Git，checkpoint_metadata.json保存逐文件SHA256。重载loss差分别{s['reload_loss_abs_difference']:.8f}、{o['reload_loss_abs_difference']:.8f}。\n\n"
text += 'Overfit通过只说明真实pretrained模型、LoRA、loss mask及更新流程能记忆这个小子集，不代表泛化或诗歌质量。每20步检查，满足预先定义的loss比值≤0.4、TF accuracy≥0.90、generation至少4/8精确复现即停止；没有扩展到正式训练数据epochs。\n\n'
text += '## 最终配置（已保存，未启动）\n\n| 参数 | B0-A | B0-B |\n|---|---|---|\n'
for a, b, c in [('数据', '24 Gold', '24 Gold + 825 Partial Silver'), ('precision', 'bf16', 'bf16'),
    ('batch / grad accumulation / effective batch', '1 / 8 / 8', '1 / 8 / 8'), ('max_length', '512', '512'),
    ('learning rate', '2e-4', '2e-4'), ('epochs', '3', '1'), ('LoRA rank / alpha / dropout', '16 / 32 / 0.05', '16 / 32 / 0.05'),
    ('source sampling masses', 'Gold=1', 'Gold=0.3, Partial Silver=0.7'), ('control dropout', '0.1', '0.1'),
    ('checkpoint interval', '10 optimizer steps + final', '10 optimizer steps + final'), ('seed', '20260926', '20260926')]:
    text += f'| {a} | {b} | {c} |\n'
text += '\n开启gradient checkpointing，无量化；LoRA target_modules为q/k/v/o及gate/up/down投影。每条采样权重=来源总权重/来源样本数，保留完整来源清单；eval时control dropout关闭。旧配置的checkpoint间隔仍默认micro_batches，新配置明确optimizer_steps。\n\n'
text += '按这些epoch起点，A约9个optimizer updates，B约107个；它们不是匹配训练预算的公平消融。此次只冻结保守准备配置，后续决定是否按统一更新次数做正式A/B比较。\n\n'
text += '## Evaluation与测试\n\n正式评价方案固定在docs/b0_pilot_evaluation.md。form compliance与imagery/density规则可作为代理；Gold full-style保留条件重构NLL分组与原始生成。生成诗的emotion/diction/expression/energy准确率目前not_measured，禁止用失败的自动语义annotator充当真值；不新增人工审核。生成非空、重复率和结构指标不替代文学质量判断。\n\n'
text += (out / 'tests.log').read_text(encoding='utf-8').strip().splitlines()[-1] + '\n\n'
text += '完整原始日志、逐步loss、token audit、重载前后生成文本、checkpoint哈希和数据隔离清单均保存在research/outputs/b0_training_pilot_20260926/。本轮没有启动configs/b0_gold_only.json或configs/b0_gold_partial_silver.json的正式训练。\n'
(ROOT / 'docs/b0_pilot_preparation_results.md').write_text(text, encoding='utf-8')
print('Pilot preparation report written')
