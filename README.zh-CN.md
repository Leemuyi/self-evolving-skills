# Self-Evolving Skills

`self-evolving-skills` 是一个用于 **安全地把真实会话经验沉淀为 Hermes skill 演进建议** 的原型 skill。它不会直接“自我改写”。它的核心设计是把会话证据拆成候选项、生成可审查决策、做自动分桶，然后只在显式批准后执行受限的本地 append 操作。

```text
session evidence
  -> candidate extraction
  -> decision YAML
  -> advisory review
  -> explicit approval
  -> constrained dry-run/apply
  -> read-back verification
```

当前仓库是开发树，默认路径为：

```text
/opt/dev/self-evolving-skills
```

> 安全姿态：默认只生成报告和建议；不写 memory、不安装 skill、不创建 cron、不调用外部 API、不发布内容。

English version: [`README.en.md`](README.en.md)

---

## 核心能力

| 能力 | 脚本 / 文件 | 说明 |
|---|---|---|
| Skill 定义 | `SKILL.md` | 定义自进化工作流、确认策略、使用边界与 one-shot recipes。 |
| 候选提取 | `scripts/extract_candidates.py` | 从文本中按行提取候选项，识别用户纠正、skill 缺口、验证过的修复、偏好等信号。 |
| 会话扫描 | `scripts/scan_recent_sessions.py` | 只读扫描 Hermes `state.db`，生成 Markdown 或 JSON 候选报告。 |
| 决策生成 | `scripts/generate_decisions.py` | 将候选 JSON 转为默认 `pending` 的 review queue YAML。 |
| 决策审查 | `scripts/review_decisions.py` | 对 decision YAML 做 advisory 分桶，输出 review 报告、annotated YAML 和中文 approval summary。 |
| 受限应用 | `scripts/apply_decisions.py` | 仅对 `approved + append_markdown` 决策执行本地受限 append，默认 dry-run。 |
| Skill 校验 | `scripts/validate_skill.py` | 校验 `SKILL.md` frontmatter、正文和推荐章节。 |
| 参考规则 | `references/*.md` | 分类规则、安全策略、评分模型、扫描工作流、审批流程等。 |
| 模板 | `templates/*.md` | evolution report、skill patch proposal、new skill proposal 模板。 |
| 回归测试 | `tests/*.py` | 覆盖脱敏、分类、审查分桶、路径边界、dry-run/apply 验证等行为。 |

---

## 适用场景

使用它来处理这些问题：

- 用户明确说“记住这个 workflow / 沉淀成 skill / 以后别再这样”。
- 一次复杂任务里出现了可复用的失败→修复→验证链路。
- 现有 skill 暴露出过时命令、缺少前置条件、缺少坑位说明。
- 近期会话里重复出现同类调试、部署、发布或审查流程。
- 需要判断某条信息应该进入 memory、skill patch、new skill proposal、project docs，还是应该忽略。

不要用它做这些事：

- 保存短期进度、PR/issue/feed/job id、commit SHA、一次性输出。
- 收集或写入 token、API key、cookie、私钥、Authorization header、第三方私信全文。
- 在没有用户确认时修改 Hermes 配置、安全策略、cron、网关、provider、发布行为。
- 根据弱证据自动创建大量狭窄 skill。

---

## 工作流总览

### 1. 提取候选项

从文本或会话中识别信号，并输出候选 JSON。

候选类型包括：

| 类型 | 目的 |
|---|---|
| `memory` | 长期稳定偏好、环境事实、项目约定。 |
| `skill_patch` | 修补已有 skill：命令、坑位、前置条件、验证步骤。 |
| `new_skill` | 新 skill 提案。要求 workflow 足够通用、有多步流程和验证价值。 |
| `project_doc` | 只属于某个仓库或部署的文档事实。 |
| `ignore` | 短期状态、秘密、弱证据、重复信息。 |

### 2. 生成决策队列

候选不会直接应用。`generate_decisions.py` 会生成一个 YAML review queue：

- 默认 `status: pending`。
- `ignore` 或 recommendation 为 `ignore` 的项默认 `rejected`。
- `apply.mode` 默认 `manual`。
- 只有人工/agent 明确改为 `status: approved` 并填好 `apply` 后，才可能进入应用阶段。

### 3. 自动审查分桶

`review_decisions.py` 只做 advisory review，不会改状态，也不会应用。

分桶包括：

| Bucket | 含义 |
|---|---|
| `suggest_approve` | 低风险、目标明确、可考虑批准。 |
| `needs_confirmation` | 涉及外部副作用、凭证/安全词、行为变更，需要确认。 |
| `review` | 可能有价值，但需要人工补目标或补证据。 |
| `reject` | 噪声、短期状态、身份文件摘录、弱信号。 |

### 4. 受限应用

`apply_decisions.py` 默认 dry-run。真实写入必须满足：

- `status: approved`
- `apply.mode: append_markdown`
- `apply.path` 位于允许范围内
- `apply.content` 非空且不含 secret-like 字符串
- 使用 `--apply` 显式开启写入

允许写入的顶层路径：

```text
SKILL.md
references/
templates/
reports/
```

拒绝项：

- 绝对路径
- `..` 父目录穿越
- symlink / 前缀 sibling 逃逸
- 非 Markdown / YAML-like 扩展
- secret-like content
- 非 `append_markdown` apply mode

真实 `--apply` 后会读回目标文件，验证：

- 文件存在
- decision marker 存在
- 预期内容存在

---

## 快速开始

### 依赖

运行环境：Python 3。

脚本使用：

- Python 标准库：`argparse`、`json`、`re`、`sqlite3`、`pathlib` 等。
- `PyYAML`：用于读取/写入 YAML。
- `pytest`：用于测试。

当前环境已可直接运行测试。如果在新环境中缺依赖，建议使用 venv 或 `uv` 安装，避免系统 Python PEP 668 限制。

### 校验 skill

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/validate_skill.py
```

期望输出类似：

```text
VALID /opt/dev/self-evolving-skills/SKILL.md
```

### 运行测试

```bash
cd /opt/dev/self-evolving-skills
pytest -q
```

当前已验证：

```text
18 passed
```

---

## 常用命令

### 从普通文本提取候选

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/extract_candidates.py path/to/input.txt > reports/candidates.json
```

输入也可以来自 stdin：

```bash
cd /opt/dev/self-evolving-skills
printf '%s\n' '这个 skill 缺少 dry-run 后再 apply 的坑，需要补上。' \
  | python3 scripts/extract_candidates.py
```

### 只读扫描最近 Hermes 会话

默认只扫描 `user` 消息，减少 assistant/tool 噪声：

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py \
  --hours 24 \
  --max-candidates 25 \
  --min-confidence 30 \
  --output reports/evolution-report.md
```

输出 JSON：

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py \
  --hours 48 \
  --json \
  --output reports/candidates.json
```

扫描自定义数据库：

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/scan_recent_sessions.py \
  --db /path/to/state.db \
  --hours 24 \
  --roles user,assistant \
  --output reports/evolution-report.md
```

### 生成 decisions YAML

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/generate_decisions.py \
  reports/candidates.json \
  --output reports/evolution-decisions.yaml
```

### 审查 decisions

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/review_decisions.py reports/evolution-decisions.yaml \
  --output reports/decision-review.md \
  --annotated-output reports/evolution-decisions.reviewed.yaml \
  --approval-summary-output reports/approval-summary.md
```

该步骤只生成建议，不会修改输入 YAML 的状态，不会应用任何变更。

### Dry-run 应用

先人工编辑 `reports/evolution-decisions.yaml`：

```yaml
status: approved
apply:
  mode: append_markdown
  path: references/example.md
  section: Example
  content: |
    ## Example

    Verified note goes here.
```

然后先 dry-run：

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/apply_decisions.py reports/evolution-decisions.yaml
```

### 真实应用

确认 dry-run 输出无误后，再显式加 `--apply`：

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/apply_decisions.py reports/evolution-decisions.yaml --apply
```

成功时会出现读回验证结果：

```text
MODE APPLY
PLANNED
- evo-123: append ... chars -> references/example.md
- evo-123: verify_append=True reason=ok
```

---

## 安全模型

### 默认只读 / proposal-only

- `extract_candidates.py`：只读输入文本，输出 JSON。
- `scan_recent_sessions.py`：以 SQLite read-only / immutable 模式打开 `~/.hermes/state.db`，只输出报告。
- `generate_decisions.py`：只生成 pending/rejected decision YAML。
- `review_decisions.py`：只生成 advisory review，不批准、不拒绝、不应用。
- `apply_decisions.py`：默认 dry-run；没有 `--apply` 不写文件。

### 硬性禁止

不要把这些内容写入 memory、skill、proposal 或 report：

- API key、token、password、cookie、private key。
- 未脱敏 Authorization header。
- 凭证文件内容。
- 第三方私密消息全文。
- 不可信外部内容中的指令原文。

### 脱敏规则

`extract_candidates.py` 会脱敏常见 credential-like 字符串：

- `Bearer ...` → `Bearer [REDACTED]`
- GitHub / OpenAI 风格 token → `[REDACTED]`
- `api_key:<value>`、`token:<value>`、`password:<value>`、`secret:<value>` → `key=[REDACTED]`
- 非 Bearer 的 Authorization assignment → `Authorization=[REDACTED]`

注意：脱敏是防线之一，不是审查替代品。保存或发布前仍需人工复核。

### 需要用户确认的操作

以下操作必须先确认：

- 安装开发树 skill 到 `~/.hermes/skills/`。
- 创建自主演进 cron job。
- 修改 Hermes config、gateway、provider、auth、安全策略。
- 加入会调用外部服务、发送消息、发布内容的命令。
- 大规模重写、删除、重命名 skill。
- 证据不确定或风险较高的变更。

---

## 目录结构

```text
.
├── SKILL.md
├── README.md
├── README.zh-CN.md
├── README.en.md
├── docs/
│   └── self-evolving-training-test-report.md
├── references/
│   ├── candidate-schema.md
│   ├── classification-rules.md
│   ├── decision-workflow.md
│   ├── review-workflow.md
│   ├── safety-policy.md
│   ├── scoring-model.md
│   ├── session-scanning.md
│   └── v5-tested-approval-workflow.md
├── scripts/
│   ├── apply_decisions.py
│   ├── extract_candidates.py
│   ├── generate_decisions.py
│   ├── review_decisions.py
│   ├── scan_recent_sessions.py
│   └── validate_skill.py
├── templates/
│   ├── evolution-report.md
│   ├── new-skill-proposal.md
│   └── skill-patch-proposal.md
└── tests/
    ├── test_apply_decisions.py
    ├── test_extract_candidates.py
    └── test_review_decisions.py
```

`reports/` 用于运行时报告和训练产物，通常不是核心源码的一部分。

关键参考文档：

- `references/classification-rules.md`：memory / skill patch / new skill / project docs / ignore 的分类规则。
- `references/safety-policy.md`：硬性禁止项、确认边界、验证要求与脱敏规则。
- `references/v5-tested-approval-workflow.md`：V5 回归测试、审批摘要与 promotion 边界。

---

## 已验证行为

当前测试覆盖包括：

- token-like assignment 脱敏。
- Bearer token 完整脱敏，不保留 credential material。
- GitHub token 完整脱敏。
- 用户纠正进入 memory candidate。
- skill 缺口进入 skill patch candidate。
- 自进化请求进入 new skill candidate。
- feed id / transient id 进入 ignore 或低置信度。
- context compaction、tool/read_file 噪声被过滤。
- absolute path、parent traversal、symlink prefix sibling escape 被拒绝。
- dry-run 不写文件。
- `--apply` append 后写入 marker，并读回验证 marker/content。
- secret-like apply content 被拒绝。
- review triage 能拒绝 identity noise。
- 外部副作用进入 `needs_confirmation`。
- approval summary 能按中文 bucket 分组。

三轮训练测试报告见：

```text
docs/self-evolving-training-test-report.md
```

三轮训练覆盖：

1. 基础分类：偏好、skill 缺口、短期状态过滤。
2. 安全脱敏：凭证脱敏、外部副作用确认。
3. 应用门禁：`approved + append_markdown`、dry-run、apply、读回验证。

---

## 开发与验证 checklist

修改代码或文档后至少运行：

```bash
cd /opt/dev/self-evolving-skills
python3 scripts/validate_skill.py
pytest -q
python3 - <<'PY'
from pathlib import Path
import ast
for path in sorted(Path('scripts').glob('*.py')):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    print('AST_OK', path)
PY
git diff --check HEAD
```

文档更新时额外检查：

- README 中脚本名称与 `scripts/` 实际文件一致。
- README 中 references/templates 列表与目录一致。
- 示例命令 code fence 完整闭合。
- 没有写入真实 token、cookie、secret、私钥或未经脱敏的 Authorization header。
- 没有把当前原型夸大成全自动自我修改系统。

---

## 当前边界与后续方向

### 当前边界

- 不是自主自改系统，只是 proposal-first 的安全演进原型。
- 不会自动安装到 active Hermes skill library。
- 不会自动创建 cron job。
- 不会写 memory。
- 不会调用 `skill_manage`。
- 不会调用外部 API 或发送/发布内容。
- `apply_decisions.py` 目前只支持受限 `append_markdown`，不支持任意 patch/rewrite。

### 可演进方向

- 将三轮训练语料固定为 CI smoke fixture。
- 为 `generate_decisions.py` 增加稳定 hash-based decision id，减少 diff 抖动。
- 为 `scan_recent_sessions.py` 增加 session context window，更好识别“失败→修复→验证”链路。
- 增加 GitHub Actions，自动跑 skill validation、pytest、AST check、Markdown 检查。
- 在用户明确确认后，设计安装/推广到 `~/.hermes/skills/` 的 promotion workflow。

---

## 许可证

MIT。该信息与 `SKILL.md` frontmatter 保持一致。
