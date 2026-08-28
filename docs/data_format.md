# 数据格式与风格标签规范（V1）

> 更新日期：2026-08-23
> 适用范围：`research/` 下的中文古典诗训练语料、风格标注、Dataset 构建与后续可控生成模型。
> 当前状态：**V1 冻结草案**。在第一轮唐诗数据集构建前，如无明确理由，不再随意新增标签。

---

## 1. 设计目标

本项目的核心不是把所有控制信息都混成一个笼统的 `CultureEmbedding`，而是明确区分：

1. **Semantic（语义）**：源诗“在说什么”。由多语言语义编码器提取，不依赖人工标签。
2. **Form（诗体）**：目标诗“要写成什么形式”。对应可验证的硬约束。
3. **Style（语言风格）**：目标诗“要呈现什么审美与表达特征”。这是第一阶段主要学习的显式控制标签。
4. **Culture（文化适配）**：跨文化转写时保留多少源文化、采用多少目标文化表达。V1 预留接口，但不参与第一轮纯唐诗训练。

因此，一条训练样本的逻辑结构是：

```text
source / text
   │
   ├── semantic representation      ← 模型自动学习
   ├── form                         ← 硬约束控制
   ├── style                        ← 显式风格控制
   └── culture_adaptation           ← 跨文化阶段控制，V1 预留
```

### 1.1 一个重要原则：硬约束不是风格标签

例如七律的：

- 8 句；
- 每句 7 字；
- 第 2 / 4 / 6 / 8 句押韵；
- 颔联、颈联对仗；
- 后续加入的平仄规范；

这些属于 **Form / Hard Constraints**，不重复编码到 Style 中。

`form = "qilv7"` 后，应由约束模块自动加载对应规则。

---

## 2. 顶层样本结构

V1 推荐每条中文训练语料使用如下 JSON 结构：

```json
{
  "id": "tang-000001",
  "text": "昔人已乘黄鹤去……",
  "form": "qilv7",
  "style": {
    "emotion": ["melancholic"],
    "imagery": [
      "landscape",
      "celestial",
      "travel",
      "human_culture"
    ],
    "diction": "refined",
    "expression": "balanced",
    "energy": "gentle",
    "density": "medium"
  },
  "culture": {
    "adaptation": null
  },
  "metadata": {
    "title": "黄鹤楼",
    "author": "崔颢",
    "dynasty": "唐",
    "source": null
  }
}
```

### 2.1 字段职责


| 字段       | 类型   | 是否必需 | 是否直接进入 V1 模型 | 说明                         |
| ------------ | -------- | ---------: | ---------------------: | ------------------------------ |
| `id`       | string |       是 |                   否 | 样本唯一标识                 |
| `text`     | string |       是 |                   是 | 目标中文古诗正文             |
| `form`     | enum   |       是 |                   是 | 目标诗体                     |
| `style`    | object |       是 |                   是 | 目标语言风格标签             |
| `culture`  | object |       是 |             **暂否** | 跨文化适配控制，V1 预留      |
| `metadata` | object |     建议 |                   否 | 研究分析、数据划分与溯源信息 |

`metadata` 不作为第一阶段风格控制输入，避免模型通过作者名、标题等捷径“记忆作者”而非学习风格。

---

## 3. Form：目标诗体

V1 只支持现有约束代码已经覆盖、且最适合第一阶段实验的两种诗体。


| 标签     | 中文名   | 基本硬约束                                         |
| ---------- | ---------- | ---------------------------------------------------- |
| `qijue7` | 七言绝句 | 4 句 × 7 字；第 2、4 句押韵                       |
| `qilv7`  | 七言律诗 | 8 句 × 7 字；第 2、4、6、8 句押韵；颔联、颈联对仗 |

### 3.1 暂不纳入 V1

以下诗体并非项目永远不做，而是为了避免第一轮数据与模型过度扩张，暂缓：

- 五言绝句；
- 五言律诗；
- 宋词；
- 元曲；
- 现代诗。

后续增加诗体时，应同时增加对应的约束检查与数据量，而不是只增加一个字符串标签。

---

## 4. Style：显式语言风格标签

V1 的 Style 由六个维度组成：

```text
style
├── emotion       情感基调
├── imagery       意象系统
├── diction       辞藻风格
├── expression    表达方式
├── energy        语言气势
└── density       意象 / 信息密度
```

其中：

- `emotion`：多标签，建议 1–2 个；
- `imagery`：多标签，建议 1–4 个；
- 其他四个维度：单标签。

---

## 5. emotion：情感基调

`emotion` 描述诗歌整体情绪与精神气质，不描述具体题材。


| 标签          | 中文含义    | 判断提示                       |
| --------------- | ------------- | -------------------------------- |
| `serene`      | 清宁 / 平和 | 宁静、淡泊、从容、澄明         |
| `joyful`      | 欢愉 / 明朗 | 喜悦、轻快、欣欣向荣           |
| `melancholic` | 感伤 / 惆怅 | 哀愁、怀旧、惜别、伤逝         |
| `lonely`      | 孤寂 / 凄清 | 孤独、空寂、冷清、独处感强     |
| `heroic`      | 豪迈 / 昂扬 | 自信、旷达、激越、进取         |
| `indignant`   | 悲愤 / 沉郁 | 忧患、压抑、不平、强烈现实悲慨 |

### 5.1 标注规则

- 至少 1 个，最多建议 2 个。
- 例如“思乡”不是 emotion 标签；它是主题。思乡诗可以同时是 `melancholic`、`lonely`，也可能是 `heroic`。
- 只有当两个情绪都对全诗有明显支配作用时才双标，避免“什么都算”。

示例：

```json
"emotion": ["melancholic", "lonely"]
```

---

## 6. imagery：意象系统

`imagery` 描述诗中承担审美和文化表达功能的主要意象类别。它是多标签字段。


| 标签             | 中文含义   | 典型内容                                   |
| ------------------ | ------------ | -------------------------------------------- |
| `landscape`      | 山水自然   | 山、江、河、湖、溪、峰、沙洲等             |
| `celestial`      | 天象       | 月、星、日、银河、天宇、云等               |
| `season_weather` | 时令与气候 | 春秋、风、雨、雪、霜、寒暑等               |
| `flora`          | 植物       | 梅、兰、竹、菊、柳、桃、荷等               |
| `fauna`          | 动物       | 雁、鹤、猿、鸟、马、蝉等                   |
| `travel`         | 行旅       | 舟、帆、驿、关、道路、羁旅等               |
| `frontier`       | 边塞军旅   | 塞外、烽火、军营、征战、戍边等             |
| `human_culture`  | 人文文化   | 城郭、楼阁、酒、琴、宫阙、典故、历史人物等 |

### 6.1 标注规则

- 建议 1–4 个主要类别。
- 标签代表“具有显著表达功能的意象”，不是简单统计是否出现某个词。
- 如果某意象只偶然出现、不影响全诗审美结构，不强制打标签。

示例：

```json
"imagery": ["landscape", "celestial", "travel"]
```

---

## 7. diction：辞藻风格

`diction` 描述语言材料本身的华朴程度。


| 标签      | 中文含义 | 判断提示                           |
| ----------- | ---------- | ------------------------------------ |
| `plain`   | 质朴     | 自然、浅近、少雕饰、口吻朴素       |
| `refined` | 典雅     | 凝练、工稳、有修辞但不过度繁复     |
| `ornate`  | 绮丽     | 华美、密集、色彩浓、典故或修饰较多 |

该维度必须单选。

---

## 8. expression：表达方式

`expression` 描述诗歌如何传递情感与意义。


| 标签       | 中文含义 | 判断提示                             |
| ------------ | ---------- | -------------------------------------- |
| `direct`   | 直抒     | 情感、态度、判断直接说出             |
| `balanced` | 情景交融 | 景物与抒情相互支撑，显隐较均衡       |
| `implicit` | 含蓄     | 借景、象征、暗示、典故等间接表达较强 |

该维度必须单选。

---

## 9. energy：语言气势

`energy` 描述诗歌在节奏、语势与情感推动上的强弱，而不是情绪类别。


| 标签       | 中文含义           | 判断提示                           |
| ------------ | -------------------- | ------------------------------------ |
| `gentle`   | 舒缓               | 平缓、舒展、低张力                 |
| `balanced` | 平稳               | 节奏和张力适中                     |
| `vigorous` | 强烈 / 顿挫 / 奔放 | 推进感强、节奏有力、语气激越或顿挫 |

例如：

- `emotion = melancholic` + `energy = gentle`：低回哀婉；
- `emotion = indignant` + `energy = vigorous`：沉郁而强烈。

该维度必须单选。

---

## 10. density：意象与信息密度

`density` 描述单位篇幅中意象、修辞、典故和语义信息的集中程度。


| 标签     | 中文含义 | 判断提示                           |
| ---------- | ---------- | ------------------------------------ |
| `sparse` | 疏朗     | 留白多，核心意象少，画面清洁       |
| `medium` | 适中     | 信息量与留白较均衡                 |
| `dense`  | 密集     | 意象、典故、修辞或语义层次高度集中 |

该维度必须单选。

---

## 11. Culture：文化适配接口

项目现有 Web Demo 使用韦努蒂“异化 ↔ 归化”的五档文化适配强度。该概念继续保留，但它与中文诗歌本身的 Style 必须分开。

字段：

```json
"culture": {
  "adaptation": 3
}
```

定义：


| 数值 | 含义                                     |
| -----: | ------------------------------------------ |
|  `1` | 极端异化：尽量保留源文化意象与表达异质性 |
|  `2` | 偏异化                                   |
|  `3` | 平衡：源文化与目标文化并置、互文         |
|  `4` | 偏归化                                   |
|  `5` | 极端归化：更多采用目标文化熟悉的表达体系 |

### 11.1 V1 训练策略

第一轮中文唐诗自重构数据本身没有“异化/归化”差异，因此：

```json
"culture": {
  "adaptation": null
}
```

V1 中该字段只作为接口预留，**暂不进入第一轮纯唐诗训练**。

后续若构建同一源诗的多档跨文化转写样本，例如：

```text
俄语原诗
├── adaptation = 1 的中文版本
├── adaptation = 3 的中文版本
└── adaptation = 5 的中文版本
```

才具备真正监督训练该维度的条件。

---

## 12. metadata：研究元数据

建议结构：

```json
"metadata": {
  "title": "黄鹤楼",
  "author": "崔颢",
  "dynasty": "唐",
  "source": "数据来源或 URL / 数据集名称"
}
```

可在后续扩展：

- `year`：创作年代；
- `collection`：诗集来源；
- `source_id`：上游数据集 ID；
- `annotation_method`：人工 / LLM / 规则；
- `annotator`：标注者匿名编号；
- `review_status`：是否复核。

### 12.1 防止数据泄漏

作者、标题、朝代等信息原则上只用于：

- 数据分析；
- 分层抽样；
- train / val / test 划分；
- 误差分析；
- 结果展示。

第一阶段不直接作为模型控制输入，避免模型通过作者名走捷径。

---

## 13. 推荐的 JSONL 完整样例

```json
{"id":"tang-000001","text":"昔人已乘黄鹤去，\n此地空余黄鹤楼。\n黄鹤一去不复返，\n白云千载空悠悠。\n晴川历历汉阳树，\n芳草萋萋鹦鹉洲。\n日暮乡关何处是，\n烟波江上使人愁。","form":"qilv7","style":{"emotion":["melancholic"],"imagery":["landscape","celestial","travel","human_culture"],"diction":"refined","expression":"balanced","energy":"gentle","density":"medium"},"culture":{"adaptation":null},"metadata":{"title":"黄鹤楼","author":"崔颢","dynasty":"唐","source":null}}
```

JSONL 文件要求：**一行一个完整 JSON 对象**。

---

## 14. 空白标注模板

采集到一首新唐诗后，可以先生成下面的模板，再进行人工或自动标注：

```json
{
  "id": "",
  "text": "",
  "form": "",
  "style": {
    "emotion": [],
    "imagery": [],
    "diction": "",
    "expression": "",
    "energy": "",
    "density": ""
  },
  "culture": {
    "adaptation": null
  },
  "metadata": {
    "title": "",
    "author": "",
    "dynasty": "唐",
    "source": ""
  }
}
```

---

## 15. V1 数据校验规则

后续 `build_dataset` 或专门 validator 应至少检查：

### 必需字段

- `id` 非空且唯一；
- `text` 非空；
- `form` 必须属于 schema 注册值；
- 六个 style 维度齐全。

### 标签合法性

- `emotion`：1–2 个合法标签；
- `imagery`：1–4 个合法标签；
- `diction / expression / energy / density`：必须各有一个合法枚举值；
- `culture.adaptation`：`null` 或整数 1–5。

### 诗体约束

- `qijue7` 调用现有 `constraints` 中的七绝检查；
- `qilv7` 调用现有 `constraints` 中的七律检查；
- 对不满足目标诗体基本结构的数据，应先清洗或单独标记，不能无提示进入训练集。

---

## 16. 关于“诗人风格”的处理

V1 不把：

```text
style = 李白
style = 杜甫
style = 王维
style = 李商隐
```

作为最底层训练标签。

原因是作者名不能解释“风格为什么成立”，也容易让模型学习身份捷径。

未来 UI 可以提供“李白式”“杜甫式”等预设，但底层应映射为一组 Style Vector 组合。例如：

```text
“李白式” preset
≈ heroic
+ landscape / celestial / human_culture
+ refined
+ direct
+ vigorous
+ medium
```

这类 preset 只是高层快捷控制，不改变底层标签定义。

---

## 17. V1 标签体系总览

```text
Target Control
│
├── FORM
│   ├── qijue7
│   └── qilv7
│
├── STYLE
│   ├── emotion
│   │   ├── serene
│   │   ├── joyful
│   │   ├── melancholic
│   │   ├── lonely
│   │   ├── heroic
│   │   └── indignant
│   │
│   ├── imagery
│   │   ├── landscape
│   │   ├── celestial
│   │   ├── season_weather
│   │   ├── flora
│   │   ├── fauna
│   │   ├── travel
│   │   ├── frontier
│   │   └── human_culture
│   │
│   ├── diction
│   │   ├── plain
│   │   ├── refined
│   │   └── ornate
│   │
│   ├── expression
│   │   ├── direct
│   │   ├── balanced
│   │   └── implicit
│   │
│   ├── energy
│   │   ├── gentle
│   │   ├── balanced
│   │   └── vigorous
│   │
│   └── density
│       ├── sparse
│       ├── medium
│       └── dense
│
└── CULTURE
    └── adaptation: 1–5 / null
        （V1 纯唐诗训练时为 null）
```

---

## 18. 后续开发顺序

在本规范冻结后，数据侧建议按以下顺序推进：

1. 编写唐诗语料收集脚本；
2. 根据 `form` 做七绝 / 七律初筛；
3. 去重、清洗、约束评分；
4. 为样本生成本规范中的空白标签模板；
5. 设计 Style 自动初标 + 人工抽查流程；
6. 编写 schema validator；
7. 划分 train / val / test；
8. 再开始真正的可控模型训练。

> **本文件是 V1 数据接口的单一事实来源（single source of truth）。** 训练代码、标注脚本与评估代码中的标签名称应与本文件及 `research/configs/style_schema.json` 保持一致。

---

## 19. V1 人工标注候选集抽样规范

### 19.1 为什么不直接随机抽 1000 首

当前结构候选集共有 18,312 首，其中不同作者的作品数量差异很大。若直接按诗歌等概率随机抽样，高产作者会被显著过度代表，人工金标集容易学习到“作者频率”而非覆盖尽可能多的风格现象。

因此 V1 人工标注候选集采用 **诗体均衡 + 作者均衡** 的抽样策略。

### 19.2 V1 固定参数

- 总样本数：1000；
- `qijue7`：500；
- `qilv7`：500；
- 随机种子：`20260823`；
- 同一作者在同一诗体中最多 1 首；
- 先均匀抽作者，再在该作者对应诗体的作品中均匀抽 1 首；
- 最终对 1000 首重新固定随机打乱，避免人工标注时产生诗体顺序效应。

实现脚本：

```bash
python -m src.data.sample_for_annotation
```

输出：

```text
data/processed/style_annotation/
├── annotation_sample_v1.jsonl
└── sampling_report_v1.json
```

### 19.3 “候选集”与“Gold Dataset”的区别

`annotation_sample_v1.jsonl` 生成时六个 `style` 字段仍为空，`review_status` 为 `pending_annotation`。它只是 **Gold 候选标注集**，不能直接称为 Gold Dataset。

只有完成以下流程后才能升级为 Gold Dataset：

1. 自动预标注；
2. 人工逐条复核或双人复核；
3. 修正有争议标签；
4. 通过 schema validator；
5. 将 `review_status` 更新为已审核状态。

### 19.4 当前 V1 抽样结果

固定种子 `20260823` 下：

- 共 1000 首；
- 七绝 500，七律 500；
- 覆盖 873 位不同作者；
- 127 位作者同时贡献七绝与七律；
- 任一作者最多出现 2 首；
- 无重复 `id`；
- 1000 首的 Style 标签当前全部保持空白。

抽样过程及源语料 SHA-256 记录在 `sampling_report_v1.json` 中，用于后续复现实验。

---

## 20. V1 Hybrid Style Pre-Annotation：混合风格预标注

### 20.1 为什么预标注不能直接写入 `style`

自动规则与大语言模型都可能误判，因此 **弱标签（weak label）与最终训练标签必须分离**。

`style` 始终只保存经过人工确认后可用于训练的最终值；自动预标注写入独立的 `annotation.prelabel`：

```json
{
  "style": {
    "emotion": [],
    "imagery": [],
    "diction": "",
    "expression": "",
    "energy": "",
    "density": ""
  },
  "annotation": {
    "version": "v1",
    "prelabel": {
      "imagery": {
        "value": ["landscape", "celestial"],
        "confidence": 0.74,
        "evidence": {
          "landscape": ["山", "江"],
          "celestial": ["月"]
        },
        "method": "lexicon_heuristic_v1",
        "status": "prelabeled"
      },
      "emotion": {
        "value": null,
        "confidence": null,
        "evidence": [],
        "method": "deepseek_semantic_v1",
        "status": "pending_llm"
      }
    },
    "review": {
      "status": "pending_human_review",
      "reviewer": null,
      "notes": null
    }
  }
}
```

这样可以保证：

- 自动判断错误时不会污染训练集；
- 人工复核时能够看到机器的判断依据；
- 后续可以统计规则、LLM 与人工之间的一致率；
- 可以比较不同预标注方法，而不需要重新构建训练格式。

### 20.2 V1 两条预标注通道

V1 使用 Hybrid Annotation Pipeline：

```text
Gold 候选诗歌
    │
    ├── 规则 / 词表
    │      ├── imagery
    │      └── density（弱代理）
    │
    └── LLM 语义判断
           ├── emotion
           ├── diction
           ├── expression
           └── energy
                    ↓
            confidence + evidence
                    ↓
                人工复核
                    ↓
                 style
```

规则部分使用：

```text
configs/imagery_lexicon_v1.json
```

实现脚本：

```bash
python -m src.data.preannotate_style
```

默认命令 **只执行免费、确定性的规则阶段，不调用任何外部 LLM API**。

### 20.3 imagery 弱标注

`imagery` 通过版本化词表匹配得到候选标签：

- 支持繁体与常见简体/异体线索；
- 最多输出 4 个类别，与 V1 schema 一致；
- 保存实际命中的词作为 `evidence`；
- 使用“最长匹配优先”抑制明显的子串误判，例如 `銀河` 不应因为内部含 `河` 就自动额外产生 `landscape`；
- 高频、歧义过强的单字线索应保守删除，以提高弱标签精度而不是追求召回率。

这些结果只表示“词表证据支持该类别”，不能代替文学人工判断。

### 20.4 density 弱标注

`density` 的规则阶段只估计 **意象线索密度**：

```text
unique_imagery_terms_per_line
= 不重复意象词数量 / 诗句数量
```

V1 阈值：

- `< 0.75` → `sparse`
- `0.75 ~ 1.5` → `medium`
- `>= 1.5` → `dense`

该值没有声称完整刻画典故、句法或修辞复杂度，因此证据中必须保留：

```text
scope_note = weak proxy: all lexicon imagery-cue concentration only
```

最终 `density` 仍需人工确认。

### 20.5 LLM 语义预标注

以下维度需要更强的整体语义与审美判断：

- `emotion`；
- `diction`；
- `expression`；
- `energy`。

LLM 标注时有以下约束：

1. Prompt 只提供诗歌正文与诗体，不提供作者、标题，降低作者身份捷径；
2. 标签只能从 `style_schema.json` 的枚举中选择；
3. `emotion` 必须 1–2 个标签，其余维度单选；
4. 必须返回 0–1 `confidence`；
5. 每维最多给 3 个原文短语作为 `evidence`；
6. 程序会检查 evidence 必须原样存在于诗歌正文，减少模型编造依据；
7. LLM 结果仍只进入 `annotation.prelabel`，不会写入最终 `style`。

DeepSeek 调用是显式 opt-in：

```bash
# 默认最多只试 10 首，便于先人工检查标注质量
python -m src.data.preannotate_style --llm --llm-limit 10

# 确认质量后才允许全量
python -m src.data.preannotate_style --llm --llm-all --resume
```

需要环境变量：

```text
DEEPSEEK_API_KEY
```

没有该变量时不应尝试 LLM 阶段。

### 20.6 当前规则阶段结果

对 `annotation_sample_v1.jsonl` 的 1000 首 Gold 候选集运行规则 V1 后：

- 1000 首全部成功生成规则预标注；
- `imagery` 完全未命中的样本：13 首；
- imagery 弱标签命中数（多标签，因此总数可超过 1000）：
  - `celestial`: 629
  - `season_weather`: 605
  - `human_culture`: 569
  - `landscape`: 562
  - `flora`: 443
  - `travel`: 291
  - `fauna`: 204
  - `frontier`: 113
- density 弱标签：
  - `sparse`: 151
  - `medium`: 467
  - `dense`: 382
- 正式 `style` 字段被自动修改的样本数：**0**。

输出：

```text
data/processed/style_annotation/
├── preannotated_v1.jsonl
└── preannotation_report_v1.json
```

只有在人工复核并明确接受/修改这些候选标签后，才能将结果提交到最终 `style` 字段。

---

## 21. 训练入口校验与 Dataset（Model Baseline V1）

模型训练侧新增明确的数据阶段闸门：

```text
candidate
   ↓
preannotated
   ↓
human review
   ↓
gold
   ↓
PoetryTrainingDataset
   ↓
tokenizer / model
```

`research/src/data/validate_dataset.py` 支持三个 stage：

- `candidate`：最终 `style` 可以为空；
- `preannotated`：检查 `annotation.prelabel` 的结构与已有预测值是否合法；
- `gold`：六个最终 `style` 维度必须完整、合法，才允许进入训练。

例如：

```bash
python -m src.data.validate_dataset \
  data/processed/style_annotation/preannotated_v1.jsonl \
  --stage preannotated
```

当前 `preannotated_v1.jsonl` 在 `preannotated` 阶段为 **1000/1000 合法**；同一文件若按 `gold` 校验，则 **1000/1000 被拒绝**，因为人工确认的最终 Style 仍为空。这是预期行为，也是防止 weak label 被误当作训练真值的保护机制。

### 21.1 Gold-only Dataset Loader

`research/src/data/dataset.py` 中的 `PoetryTrainingDataset` 默认只接受通过 `gold` 校验的数据，不会自动把 `annotation.prelabel` 复制进 `style`。

Baseline B0 先把结构化 Style 转换为可读控制文本，例如：

```text
诗体：七言绝句
情感：感伤惆怅、孤寂凄清
意象：天象、行旅、时令气候
辞藻：典雅
表达：情景交融
气势：舒缓
密度：适中
```

然后严格分离：

```text
prompt_text  -> 模型输入
原诗正文     -> supervised target
```

作者、标题等 metadata 不进入 Prompt，以继续避免作者身份 shortcut。

这一阶段的 Dataset 暂时保持 framework-agnostic，不依赖 PyTorch。下一步接入 Qwen tokenizer 后，再把 `TrainingExample` 编码成 `input_ids / attention_mask / labels`。
