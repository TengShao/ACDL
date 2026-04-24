# ACDL 系统开发方案

## 1. 系统定位

ACDL，全称 **Agent Collaborative Development Lifecycle**，是一套用于多人、多项目、多 coding agent 协同开发的生命周期系统。

它的核心目标不是“维护文档”，而是维护一套：

- agent 可读取
- 人类可审核
- 机器可验证
- 可持续同步

的共享状态源。

文档、任务契约、交接包、检查脚本和 CI 门禁，都是共享状态源的不同表现形式。

## 2. 第一性原理

多 agent 协作开发的底层问题是：

> 多个智能体在不同时间、不同上下文下修改同一个复杂系统，如何保证它们对系统状态、任务边界和验收标准的理解一致。

ACDL 需要维护五个不变量：

1. **Context Invariant**
   agent 开始任务前，必须读取统一上下文。

2. **Boundary Invariant**
   每个任务必须有明确修改范围和禁止范围。

3. **Contract Invariant**
   API、schema、配置、权限、数据模型等契约变化必须被同步记录。

4. **Verification Invariant**
   关键规则必须能被自动检查，不能只靠人记。

5. **Continuity Invariant**
   每次交接后，下一个 agent 能恢复当前状态，而不是重新猜。

## 3. 生命周期模块

ACDL 由七个核心模块组成：

1. **Agent-led Project Retrofit**
   用于已有项目接入。
   agent 自动扫描项目，生成第一版协作事实源。

2. **Agent Context Bootstrap**
   用于每次任务开始前。
   agent 读取项目事实源，生成本次任务上下文。

3. **Agent Task Contract**
   用于任务启动。
   明确目标、范围、禁止区域、验收标准。

4. **Agent Development Guardrails**
   用于开发过程中。
   约束 agent 不越界、不顺手重构无关代码。

5. **Agent Change Sync**
   用于代码变更后。
   根据变更自动判断是否需要同步事实源。

6. **Agent Preflight Check**
   用于提交前或合并前。
   自动检查测试、构建、lint、契约漂移和文档缺失。

7. **Agent Handoff & Knowledge Maintenance**
   用于交接和长期维护。
   保证下一个 agent 可以继续工作，并防止事实源腐化。

## 4. 标准目录结构

```text
AGENTS.md
docs/
  architecture.md
  contracts.md
  workflows.md
  active-work.md
  open-questions.md
  decisions/
    0001-current-architecture.md
.acdl/
  project-state.json
  context.md
  task-contract.json
  change-impact.json
  handoff-pack.md
```

## 5. CLI 设计

系统提供平台无关 CLI：

```bash
acdl retrofit
acdl bootstrap
acdl contract
acdl sync
acdl preflight
acdl handoff
acdl maintain
```

## 6. 核心数据对象

### ProjectState

记录项目级共享状态：

- 项目目标
- 技术栈
- 常用命令
- 模块结构
- 架构边界
- API / schema / config 契约
- 高风险区域
- 当前负责人

### TaskContract

记录单次任务约束：

- 任务目标
- 允许修改范围
- 禁止修改范围
- 验收标准
- 相关事实源
- 需要运行的检查

### ChangeImpact

记录代码变更影响：

- API 变化
- schema 变化
- 配置变化
- 权限变化
- 架构变化
- 用户可见行为变化
- 需要同步的文档

### HandoffPack

记录交接信息：

- 已完成内容
- 未完成事项
- 风险点
- 最近决策
- 推荐下一步

## 7. MVP 开发阶段

### Phase 1: Retrofit

实现 `acdl retrofit`：

- 扫描 README、docs、配置文件、package manifest、schema、API、CI 文件。
- 生成 `AGENTS.md` 和基础 `docs/`。
- 不确定内容写入 `docs/open-questions.md`。
- 不修改业务代码。

### Phase 2: Task Loop

实现：

- `acdl bootstrap`
- `acdl contract`
- `acdl handoff`

形成任务启动、任务边界、任务交接闭环。

### Phase 3: Sync & Preflight

实现：

- `acdl sync`
- `acdl preflight`

根据 git diff 判断契约变化，并在提交前检查事实源一致性。

### Phase 4: Maintenance

实现 `acdl maintain`：

- 检查过期文档。
- 检查事实源冲突。
- 检查长期未处理的问题。
- 生成维护建议。

## 8. 验收标准

MVP 至少满足：

- 对已有项目运行 `acdl retrofit` 后，能生成可读的 `AGENTS.md` 和基础 docs。
- agent 无法确认的信息不会被编造，而是进入 `open-questions.md`。
- 新成员可通过生成文档理解项目运行方式、架构边界和协作规则。
- API/schema 变化后，`acdl sync` 能提示更新 contracts。
- 未同步事实源时，`acdl preflight` 能失败。
- 任务结束后，`acdl handoff` 能生成交接包。
