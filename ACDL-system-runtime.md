# ACDL 系统运行方式

## 1. 总体运行模型

ACDL 运行在每个项目仓库内。

它不是一个一开始就需要中心化部署的大平台，而是一个项目级协作操作系统：

```text
项目仓库
→ acdl CLI
→ 共享状态源
→ agent 开发流程
→ preflight / CI 检查
→ 合并后继续维护
```

每个 coding agent 在开发前、中、后都通过 `acdl` 命令读取、更新和校验共享状态源。

## 2. 项目第一次接入

已有项目第一次接入时运行：

```bash
acdl retrofit
```

执行流程：

```text
扫描项目
→ 识别技术栈、命令、架构、API、schema、docs
→ 生成 AGENTS.md 和 docs/
→ 标记 open questions
→ 生成改造摘要
→ 交给负责人审核
```

输出：

```text
AGENTS.md
docs/architecture.md
docs/contracts.md
docs/workflows.md
docs/active-work.md
docs/open-questions.md
```

责任分工：

- agent 负责扫描、归纳、生成。
- 人类负责人只审核业务意图、架构边界、高风险区域和不确定项。

## 3. 每次任务开始前

agent 开始任务前运行：

```bash
acdl bootstrap
```

系统读取：

```text
AGENTS.md
docs/architecture.md
docs/contracts.md
docs/workflows.md
docs/active-work.md
近期 git 变更
当前任务描述
```

输出：

```text
.acdl/context.md
.acdl/project-state.json
```

目标：

- 统一上下文。
- 避免 agent 在缺少项目背景时直接改代码。
- 让不同 agent 看到一致的项目事实。

## 4. 任务启动时

agent 运行：

```bash
acdl contract
```

生成：

```text
.acdl/task-contract.json
```

内容包括：

```text
任务目标
允许修改范围
禁止修改范围
验收标准
可能影响的契约
需要同步更新的文档
需要运行的检查命令
```

目标：

- 防止 agent 越界修改。
- 防止顺手重构无关代码。
- 让任务完成标准可检查。

## 5. 开发过程中

agent 正常开发，但必须遵守 task contract。

如果发现契约外问题：

```text
发现另一个 bug
想重构其他模块
发现架构问题
发现文档陈旧
```

默认行为是记录为 follow-up，而不是直接修改。

只有当任务契约允许，或负责人明确授权时，agent 才能扩大修改范围。

## 6. 代码变更后

agent 运行：

```bash
acdl sync
```

系统根据 git diff 判断：

```text
API 是否变化
schema 是否变化
配置项是否变化
权限规则是否变化
架构边界是否变化
用户可见行为是否变化
```

如果发生变化，系统生成事实源更新建议。

典型规则：

```text
改了 API route → 更新 docs/contracts.md
改了数据库 schema → 更新 contracts 和 migration notes
改了启动命令 → 更新 AGENTS.md 或 workflows
改了模块边界 → 更新 architecture
改了用户可见行为 → 更新 release notes
```

## 7. 提交前检查

agent 或 CI 运行：

```bash
acdl preflight
```

检查内容：

```text
测试是否通过
构建是否通过
lint 是否通过
task contract 是否存在
是否改到禁止区域
代码变更和事实源是否一致
是否存在未解决 open questions
是否存在多人并行冲突风险
```

结果：

- 通过：允许进入 PR/MR review。
- 失败：agent 修复问题，或标记需要人工确认。

## 8. 任务结束或交接

agent 运行：

```bash
acdl handoff
```

生成：

```text
.acdl/handoff-pack.md
```

内容包括：

```text
本次完成了什么
还没完成什么
风险点
最近决策
下一位 agent 应该先看什么
推荐下一步
```

目标：

- 降低接力成本。
- 让下一个成员或 agent 不需要重新猜项目状态。
- 保证协作连续性。

## 9. 长期维护

定期运行：

```bash
acdl maintain
```

检查内容：

```text
文档是否过期
事实源是否互相冲突
open questions 是否长期未处理
architecture/contracts 是否和代码漂移
active-work 是否已经失效
```

运行频率：

- 小团队：每周一次。
- 高频协作项目：每天一次。
- 关键项目：合并后自动运行。

## 10. 最小闭环

ACDL 的最小运行闭环是：

```bash
acdl retrofit    # 项目接入
acdl bootstrap   # 任务启动上下文
acdl contract    # 任务边界
acdl sync        # 变更同步
acdl preflight   # 提交前检查
acdl handoff     # 任务交接
```

一句话总结：

> ACDL 运行在每个项目仓库里，agent 用 CLI 读取和更新共享状态源，CI 用 preflight 阻止不一致的变更合并。
