## ALYMPICS · Platform Dual-Mode Playground

LLM agents staged inside **Alympics** now reproduce the interaction structure from the RAND Journal paper _“Should platforms be allowed to sell on their own marketplaces?”_ while keeping the legacy water-allocation and k-level reasoning examples.  
Every run is a dialogue between a platform agent `M` and an innovative seller `S`, following the paper’s timing: mode selection → commission setting → innovation choice → pricing → optional imitation/self-preferencing.

---

### 1. 环境配置

1. **Python 3.10+**，安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. **DeepSeek API**：设置环境变量或 `.env`。
   ```bash
   export DEEPSEEK_API_KEY="sk-xxxxx"
   export DEEPSEEK_MODEL="deepseek-chat"   # 可选
   ```
3. （可选）设定 `MPLCONFIGDIR` 为可写目录以加速 matplotlib：
   ```bash
   export MPLCONFIGDIR="$PWD/.mplcache"
   ```

---

### 2. 快速体验

默认参数对应论文基线：`v=100, b=10, σ=5, Δ_l=5` 等。

```bash
cd src
python run.py --round 3 \
  --base-value 100 --sigma 5 --convenience 10 \
  --min-innovation 5 --max-innovation 60
```

命令行参数映射论文符号：

| Flag | Meaning |
| --- | --- |
| `--base-value` | 消费者对普通产品的估值 \(v\) |
| `--convenience` | 平台便利性 \(b\) |
| `--sigma` | 平台自营优势/劣势 \(σ\) |
| `--min-innovation` / `--max-innovation` | 创新区间 \([\Delta_l,\Delta_{\max}]\) |
| `--innovation-cost-scale` | 创新成本 \(K(\Delta)=c(\Delta-\Delta_l)^2\) 的系数 |
| `--outside-scale` | 外部机会分布 \(G(\cdot)\) 的线性尺度 |
| `--ban-dual`, `--ban-imitation`, `--ban-self-preferencing` | 各种政策情景 |

运行时日志会打印每阶段的 LLM 对话，并在 `PlatformGame.round_records` 中记录：

```json
{
  "round": 1,
  "mode": "dual",
  "commission": 5.0,
  "innovation": 15.0,
  "imitation": true,
  "display_share": 0.3,
  "price_M": 20.0,
  "price_S_platform": 20.0,
  "price_S_direct": 15.0,
  "profit_M": 17500.0,
  "profit_S": -8.0
}
```

---

### 3. 多场景实验与可视化

`src/run_experiments.py` 会串行运行多个情景，汇总原始数据和利润曲线。

```bash
cd src
python run_experiments.py \
  --rounds 2 \
  --scenarios baseline,ban_self_pref \
  --output-data ../exp/platform_game_results.json \
  --output-plot ../exp/platform_game_results.png
```

- `baseline`：无约束。
- `ban_self_pref`：禁止 M 隐藏 S（展示比例固定为 1）。
- `ban_dual_mode`：只允许 marketplace / seller 模式。

输出：

* `exp/platform_game_results.json`：合并的逐轮数据。
* `exp/platform_game_results.png`：上下两个子图分别绘制平台利润 \(\Pi_M\) 与卖家利润 \(\pi_S\)。

若需自定义情景，可在 `DEFAULT_SCENARIOS` 中增加条目并传入 `--scenarios my_case`.

---

### 4. 其它示例

| 模块 | 描述 / 入口 |
| --- | --- |
| 水资源博弈 | `src/waterAllocation.py` 中的 `waterAllocation` 类，可在外部脚本调用 `run_multi_round`。 |
| K-level 推理 | `k-reasoning/G08A`、`k-reasoning/SAG`，分别包含 `run.sh`、`evaluate.py` 等脚本。 |

这些示例保持与原 Alympics 论文一致，没有耦合新的平台游戏代码。

---

### 5. 项目结构（节选）

```
Alympics/
├── src/
│   ├── Alympics.py            # Playground、Player、LLM 基类
│   ├── run.py                 # 平台双模式 CLI
│   ├── platform_game.py       # 核心仿真逻辑 (配置 + 循环 + 结算)
│   ├── run_experiments.py     # 多情景批量实验 & 绘图
│   ├── waterAllocation.py     # 水资源博弈示例
│   └── ...                    # 其它实验
├── k-reasoning/               # k-level reasoning 子项目
├── exp/                       # 运行产生的 JSON/PNG 等结果
├── 10-Should ... .pdf         # 参考论文
└── requirements.txt
```

---

### 6. 常见问题

1. **API 调用超时**：DeepSeek 返回较慢时可重试，或减少 `--rounds`；脚本会维持对话上下文自动接续。
2. **Matplotlib 缓存不可写**：在 macOS 上可 `mkdir .mplcache && export MPLCONFIGDIR="$PWD/.mplcache"`。
3. **LLM 回复格式不标准**：`platform_game.py` 中的 `_extract_*` 会 fallback，但建议在 Prompt 内提醒输出 JSON/键值对。

---

### 7. 致谢

本项目延续 **Alympics: Language Agents Meet Game Theory** 的框架，并基于 DeepSeek API 重写了平台双模式游戏，供研究多主体策略与监管政策使用。
