<div align="center">

# 跨文化诗歌重写模型
### Cross-Cultural Poetry Rewriting Model

**用「语义—风格—文化」三位一体的可控生成，让异国诗歌脱胎换骨为中文七律。**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![Transformers](https://img.shields.io/badge/Transformers-4.44+-FFAE00?logo=huggingface&logoColor=white)](https://huggingface.co/docs/transformers)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-6DB33F?logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![License](https://img.shields.io/badge/Use-%E6%95%99%E5%AD%A6%20%C2%B7%20%E7%A7%91%E7%A0%94-blue.svg)](#-许可声明)

[项目简介](#-项目简介) ·
[模型架构](#-模型架构三位一体) ·
[快速开始](#-快速开始) ·
[目录结构](#-目录结构) ·
[示例](#-示例) ·
[致谢](#-致谢)

</div>

---

## 项目简介

本项目为**南京大学大学生创新训练计划**作品（2025.12 – 2026.12）。

传统机器翻译在处理诗歌时常常**丢失文化意象、违反格律、风格走形**——把"白桦树"译成"杨柳"很容易，但要让一首叶赛宁写成李商隐的风骨，靠翻译 API 是做不到的。

我们提出**「语义—风格—文化」三位一体可控生成框架**：

> **不翻译原文，只提取语义。** 用冻结的 **XLM-RoBERTa** 把任意语言的诗歌编码成多语言对齐的语义向量，再经一个可学习的投影头与文化嵌入，作为前缀注入 **Qwen2.5-1.5B**，由 LoRA 微调后的解码器生成符合**七律平仄、押韵、对仗**约束的中文诗。

**MVP 阶段**支持 🇷🇺 俄语 → 七律 与 🇰🇷 韩语 → 七律（零样本跨语言），未来可扩展至更多语言与诗体（绝句、宋词等）。

---

## 模型架构（三位一体）

```
   源语言诗歌（俄 / 韩 / 中 …）
            │
            ▼
   ┌────────────────────────┐
   │  XLM-RoBERTa  ❄ 冻结    │   多语言语义对齐
   └────────────┬───────────┘
                │ [CLS]  768-d
                ▼
   ┌────────────────────────┐
   │  ProjectionMLP  🔥 可训 │   768 → 1536
   └────────────┬───────────┘
                │   语义前缀 [B, 1, 1536]
                │
   ┌────────────────────────┐
   │  CultureEmbedding 🔥可训│   ←  唐诗 / 宋词 / 现代…
   └────────────┬───────────┘
                │   文化前缀 [B, 1, 1536]
                ▼
        [prefix_embeds: B, 2, 1536]
                │  concat
                ▼
   ┌────────────────────────┐
   │  Qwen2.5-1.5B + LoRA   │   🔥 LoRA r=16 可训
   └────────────┬───────────┘
                ▼
   ┌────────────────────────┐
   │  格律打分器 (scorer)    │   平仄 / 押韵 / 字数
   └────────────┬───────────┘
                ▼
            ✦ 中文七律 ✦
```

### 关键设计

| 模块 | 作用 | 参数 | 状态 |
|------|------|------|------|
| `SemanticEncoder` (XLM-R-base) | 多语言语义编码 | ~280M | ❄ 冻结 |
| `ProjectionMLP` | 跨模型空间对齐 768→1536 | ~1.5M | 🔥 训练 |
| `CultureEmbedding` | 可学习文化风格向量表 | 极少 | 🔥 训练 |
| `Qwen2.5-1.5B` (LoRA) | 中文七律生成 | ~1.5B / LoRA ~10M | 🔥 LoRA |
| `scorer_qilu` | 平仄韵脚打分，候选重排 | — | 规则 |

**为什么训练只用中文自重建却能跨语言推理？**
XLM-R 的多语言空间是天然对齐的——「秋风」与 «осенний ветер»、«가을바람» 在嵌入空间中近邻。中文自重建训练后，模型已经学会从该空间的任意一点生成七律，于是**俄语 / 韩语推理零样本可用**。

---

## 快速开始

### 1. 环境准备

```bash
# Python 端（建议在 WSL / Linux 下创建 venv）
cd research
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **推荐显存**：训练 ≥ 12 GB（fp16 + LoRA r=16），推理 ≥ 6 GB。
> 显存吃紧时可在 `configs/train_trinity_config.yaml` 中开启 `load_in_4bit: true`（需 bitsandbytes）。

### 2. 准备语料

```bash
# 拉取唐诗七律语料（约几千首）
python src/data/collect_corpus.py

# 构建训练 / 验证 / 测试集
python src/data/build_dataset_trinity.py
```

### 3. 训练

```bash
python src/train_trinity.py --config configs/train_trinity_config.yaml
```

训练产物结构：

```
outputs/trinity/
├── best/                   # 验证集最优 checkpoint
│   ├── projection.pt
│   ├── culture_embedding.pt
│   └── lora_adapter/
├── final/                  # 训练结束最终 checkpoint
└── checkpoint-{step}/      # 每 200 步保存
```

### 4. 推理

```bash
# 单条
python src/generate_trinity.py --input-text "秋风萧瑟，思乡情切"

# 批量（JSONL）
python src/generate_trinity.py --input-file data/raw/russian_samples.jsonl

# 交互模式
python src/generate_trinity.py --interactive
```

### 5. 启动 Web Demo（可选）

```bash
# 后端 (Spring Boot)
cd web/poem
./mvnw spring-boot:run

# 前端 (Vue 3 + Element Plus)
cd web/vue-poem-project
npm install
npm run serve
```

---

## 目录结构

```
Cross-Cultural-Poetry-Rewriting-Model/
├── research/                       # 🧠 ML 训练与推理（Python）
│   ├── configs/
│   │   ├── train_config.yaml             # baseline 配置
│   │   └── train_trinity_config.yaml     # 三位一体配置
│   ├── data/
│   │   ├── raw/                          # 原始语料
│   │   │   ├── qilu_corpus.jsonl
│   │   │   ├── russian_samples.jsonl
│   │   │   └── korean_samples.jsonl
│   │   └── processed/trinity/            # 训练数据集
│   ├── src/
│   │   ├── models/                       #   三位一体模型
│   │   │   ├── semantic_encoder.py       #   冻结 XLM-R
│   │   │   ├── projection.py             #   768→1536 投影
│   │   │   ├── culture_embedding.py      #   文化向量表
│   │   │   └── rewriter.py               #   TrinityRewriter 主体
│   │   ├── constraints/                  # 平仄/押韵/打分
│   │   │   ├── meter_qilu.py
│   │   │   ├── rhyme_qilu.py
│   │   │   └── scorer_qilu.py
│   │   ├── data/
│   │   │   ├── collect_corpus.py
│   │   │   └── build_dataset_trinity.py
│   │   ├── train_trinity.py              # 训练入口
│   │   ├── generate_trinity.py           # 推理入口
│   │   └── evaluate.py                   # 批量评估
│   └── outputs/trinity/                  # 模型权重产物
│
├── web/                            # Web 端展示
│   ├── poem/                             # Spring Boot 后端 (Java)
│   │   └── src/main/java/com/example/demo/
│   │       ├── controller/PoemController.java
│   │       ├── service/PoemService.java
│   │       └── model/Poem.java
│   └── vue-poem-project/                 # Vue 3 前端
│       └── src/
│           ├── views/GenerateView.vue
│           └── components/
│               ├── InputBox.vue
│               ├── ControlPanel.vue
│               └── PoemCard.vue
│
├── docs/                                 # 文档
│   ├── model_card.md                     # 模型卡
│   ├── api_spec.md                       # API 规范
│   ├── data_format.md                    # 数据格式
│   └── spec_qijue.md                     # 七绝/七律规范
│
└── README.md
```

---

## 示例

<table>
<tr>
<td width="50%">

**输入（俄语 · 叶赛宁《白桦》节选）**

```
Белая берёза
Под моим окном
Принакрылась снегом,
Точно серебром.
```

</td>
<td width="50%">

**输出（中文七律）**

```
窗前白桦影离离，
夜雪轻披似玉衣。
冷月浸枝寒不语，
霜风过叶静成诗。
银钩点点凝晨露，
素练丝丝挂晚晖。
独立庭中谁与共，
故园千里梦依稀。
```

</td>
</tr>
</table>

> 示例为说明性输出，实际效果取决于训练轮次与候选重排策略。

---

## 许可声明

本项目为**南京大学大学生创新训练计划**学生作品，仅限**教学与科研用途**：

- ✅ 欢迎学习、研究、复现实验、引用本项目思路
- ✅ 欢迎在论文 / 课程报告 / 学位论文中引用（请注明出处）
- ❌ 未经作者同意，请勿用于任何商业用途
- ❌ 训练数据中的唐诗语料版权归原整理者所有，仅用于学术研究

如需合作或其他用途，请通过 Issue 或邮件联系作者。

---

## 致谢

- **南京大学大学生创新训练计划** —— 项目立项与资助
- **Qwen Team** —— 优秀的开源中文基座模型
- **Hugging Face & Meta AI** —— XLM-RoBERTa 多语言对齐能力
- 所有为唐诗整理工作付出心血的研究者们

---

<div align="center">

**🌸 让每一首诗都能找到属于它的另一种语言。 🌸**

*If you find this project interesting, please consider giving it a ⭐!*

</div>