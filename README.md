# ACDL

[English](#acdl) | [中文](#中文说明)

ACDL (**Agent Collaborative Development Lifecycle**) is a CLI for stabilizing multi-agent software collaboration.

It is designed for teams where multiple people use different coding agents against the same projects. The goal is not to “write more docs”; the goal is to maintain a shared project state that agents can read, humans can review, machines can verify, and future agents can resume from.

## Core Model

ACDL treats each repository as a small collaboration operating system:

```text
project repository
→ acdl CLI
→ shared state source
→ agent task workflow
→ preflight / CI checks
→ maintained project knowledge
```

The shared state source is expressed through `AGENTS.md`, `docs/`, `.acdl/` task artifacts, preflight reports, and handoff packs.

ACDL protects five collaboration invariants:

- **Context**: agents start from the same project facts.
- **Boundary**: every task has an explicit allowed and forbidden scope.
- **Contract**: API, schema, config, permission, and data model changes are synchronized.
- **Verification**: critical rules are checked by commands, not memory.
- **Continuity**: the next agent can continue without rediscovering the project state.

## Lifecycle

ACDL maintains that shared state through a fixed lifecycle:

```bash
acdl retrofit
acdl bootstrap
acdl contract
acdl sync
acdl preflight
acdl handoff
acdl maintain
```

- `retrofit`: agent-led onboarding for existing projects. Scans the repository and generates the first `AGENTS.md` plus baseline docs.
- `bootstrap`: creates task context before an agent starts work.
- `contract`: defines task goal, allowed scope, forbidden scope, checks, and sync expectations.
- `sync`: analyzes changed files and reports which shared facts may need updates.
- `preflight`: runs required checks and detects missing fact-source updates before review.
- `handoff`: creates a continuation pack for the next agent or teammate.
- `maintain`: checks long-term knowledge drift and stale shared state.

The project is currently an MVP implemented with Python standard library only.

## Install

```bash
python3 -m pip install --user "https://github.com/TengShao/ACDL/releases/download/v0.1.0/acdl-0.1.0-py3-none-any.whl"
```

Verify:

```bash
acdl --help
```

If your shell cannot find `acdl`, make sure Python's user scripts directory is on `PATH`.

On macOS this is commonly:

```bash
$HOME/Library/Python/<python-version>/bin
```

For example:

```bash
export PATH="$HOME/Library/Python/3.14/bin:$PATH"
```

Uninstall:

```bash
python3 -m pip uninstall acdl
```

## Usage

After installation, run `acdl` from any project checkout.

First-time project onboarding:

```bash
acdl retrofit --root /path/to/project
```

This generates the baseline collaboration state:

```text
AGENTS.md
docs/architecture.md
docs/contracts.md
docs/workflows.md
docs/active-work.md
docs/open-questions.md
docs/decisions/0001-current-architecture.md
.acdl/project-state.json
```

Per-task flow:

```bash
acdl bootstrap --root /path/to/project --task "Implement login"
acdl contract --root /path/to/project --task "Implement login" --scope src/ --check "npm run test"
acdl sync --root /path/to/project
acdl preflight --root /path/to/project
acdl handoff --root /path/to/project
```

During development, agents should stay inside the task contract. Out-of-scope bugs, refactors, or architecture concerns should be recorded as follow-ups unless the task contract explicitly allows expanding scope.

Long-term maintenance:

```bash
acdl maintain --root /path/to/project
```

## Distribution

For the team, the intended distribution path is:

1. Maintainer tags a release, for example `v0.1.0`.
2. GitHub Actions builds `acdl-0.1.0-py3-none-any.whl`.
3. GitHub Release stores the wheel.
4. Team members install the wheel URL directly.

See [docs/distribution.md](docs/distribution.md) for install, upgrade, and release options.

## Development

```bash
python3 -m unittest discover -s tests
sh scripts/build.sh
```

---

# 中文说明

ACDL（**Agent Collaborative Development Lifecycle**）是一套用于稳定多人、多项目、多 coding agent 协同开发的 CLI。

它面向这样的团队场景：不同成员使用不同 coding agent，在同一个或多个项目中并行开发。ACDL 的目标不是“多写文档”，而是维护一套共享项目状态，让 agent 能读取、人类能审核、机器能验证，并让后续 agent 可以继续接手。

## 核心模型

ACDL 把每个项目仓库看作一个小型协作操作系统：

```text
项目仓库
→ acdl CLI
→ 共享状态源
→ agent 任务流程
→ preflight / CI 检查
→ 持续维护的项目知识
```

共享状态源由这些内容共同表达：

- `AGENTS.md`
- `docs/`
- `.acdl/` 任务产物
- preflight 报告
- handoff 交接包

ACDL 维护五个协作不变量：

- **Context 上下文一致**：agent 开始任务前读取同一套项目事实。
- **Boundary 边界清晰**：每个任务都有明确的允许范围和禁止范围。
- **Contract 契约同步**：API、schema、配置、权限和数据模型变化必须同步。
- **Verification 自动验证**：关键规则靠命令检查，而不是靠记忆。
- **Continuity 可连续交接**：下一个 agent 不需要重新猜项目状态。

## 生命周期

ACDL 用固定生命周期维护共享状态：

```bash
acdl retrofit
acdl bootstrap
acdl contract
acdl sync
acdl preflight
acdl handoff
acdl maintain
```

- `retrofit`：已有项目接入。由 agent 扫描仓库，生成第一版 `AGENTS.md` 和基础 docs。
- `bootstrap`：任务开始前生成上下文。
- `contract`：定义任务目标、允许范围、禁止范围、检查命令和同步要求。
- `sync`：分析代码变更，提示哪些共享事实源可能需要更新。
- `preflight`：提交前运行检查，并发现缺失的事实源更新。
- `handoff`：生成交接包，方便下一个 agent 或团队成员继续。
- `maintain`：检查长期知识漂移和过期共享状态。

当前项目仍是 MVP，使用 Python 标准库实现。

## 安装

```bash
python3 -m pip install --user "https://github.com/TengShao/ACDL/releases/download/v0.1.0/acdl-0.1.0-py3-none-any.whl"
```

验证：

```bash
acdl --help
```

如果终端找不到 `acdl`，请确认 Python 用户脚本目录在 `PATH` 中。

macOS 常见路径：

```bash
$HOME/Library/Python/<python-version>/bin
```

例如：

```bash
export PATH="$HOME/Library/Python/3.14/bin:$PATH"
```

卸载：

```bash
python3 -m pip uninstall acdl
```

## 使用

安装后，可以在任意项目仓库中运行 `acdl`。

已有项目首次接入：

```bash
acdl retrofit --root /path/to/project
```

它会生成基础协作状态：

```text
AGENTS.md
docs/architecture.md
docs/contracts.md
docs/workflows.md
docs/active-work.md
docs/open-questions.md
docs/decisions/0001-current-architecture.md
.acdl/project-state.json
```

每次任务开发流程：

```bash
acdl bootstrap --root /path/to/project --task "实现登录"
acdl contract --root /path/to/project --task "实现登录" --scope src/ --check "npm run test"
acdl sync --root /path/to/project
acdl preflight --root /path/to/project
acdl handoff --root /path/to/project
```

开发过程中，agent 应该遵守 task contract。契约外的 bug、重构想法或架构问题，默认记录为 follow-up，除非 task contract 明确允许扩大范围。

长期维护：

```bash
acdl maintain --root /path/to/project
```

## 分发

团队推荐分发方式：

1. 维护者创建版本标签，例如 `v0.1.0`。
2. GitHub Actions 构建 `acdl-0.1.0-py3-none-any.whl`。
3. GitHub Release 保存 wheel 文件。
4. 团队成员直接安装 wheel URL。

安装、升级和发布细节见 [docs/distribution.md](docs/distribution.md)。

## 开发

```bash
python3 -m unittest discover -s tests
sh scripts/build.sh
```
