# 从上下文工程到 Harness Agent：一个工程师视角的系统理解

这篇文章要回答一个问题：一个 Agent 为什么不能只靠更好的 Prompt，而需要一个 Harness。

我的结论是：Prompt 决定一次模型调用怎么说话，Harness 决定一个系统如何持续行动。真正的 Agent 工程，不是把提示词写长，而是把上下文、工具、循环、记忆、技能、子任务和任务状态组织成一个可运行、可恢复、可审计的系统。

## Prompt 不够，因为任务不是单轮发生的

Prompt Engineering 解决的是一次输入的表达问题。它关心怎么描述角色、目标、格式、约束，让模型在当前这一轮给出更好的回答。

但工程任务通常不是一轮完成的。分析一个仓库时，Agent 要先看目录，再读 README，再运行测试，再根据结果修正判断。每一步都会产生新观察，新观察又会改变下一步行动。

这时问题已经不是“怎么问模型”，而是“模型在每一步应该看到什么”。这就是 Context Engineering 的位置。

Context Engineering 管的不是一句提示词，而是一条信息供应链：目标、历史、工具结果、任务状态、约束、技能和记忆，哪些进入当前上下文，哪些压缩，哪些持久化，哪些延迟加载。

如果一个系统只是在用户输入前拼接一段长模板，它还停留在 Prompt 层。如果它能根据任务状态选择信息、调用工具、沉淀观察，并把下一次模型调用建立在这些观察上，它才进入上下文工程。

## Harness 是模型之外的行动系统

可以把 Agent 简化成：

```text
Agent = Model + Harness
```

Model 负责生成判断、计划、代码或自然语言。Harness 负责把这些输出放进一个受控系统里执行。

这个区分很重要。模型可以说“我应该读取文件”，但真正读取文件的是 Harness。模型可以生成一段代码，但决定代码是否安全、是否能执行、执行结果如何回写上下文的，也是 Harness。

因此，Harness 不是模型的附属提示词，而是模型之外的工程外壳。它至少要回答六个问题：

- 当前任务是什么，状态在哪里。
- 模型这一步需要哪些上下文。
- 它可以使用哪些工具。
- 工具结果如何进入下一轮。
- 失败、阻塞、审批和重试如何处理。
- 上下文太长或任务中断时如何恢复。

一旦这些问题出现，Agent 就不再是一个聊天界面，而是一个持续行动系统。

## 一个最小 Harness Agent 包含什么

我现在会用一个最小结构说明 Harness Agent 的组成：

```text
User
  -> Channel
  -> Agent Loop
  -> Context
  -> Tools / Skills / Memory / SubAgent
  -> Task State
  -> Trace / Report
```

**Agent Loop** 是持续行动的核心。它让系统从“回答一次”变成“观察、行动、再观察、再行动”。没有 Loop，工具调用只是一次函数调用，不是 Agent。

**Tools** 是模型和外部世界的接口。文件读取、命令执行、代码执行都属于工具。工具必须有边界：参数、权限、超时、输出限制和错误处理。

**Context** 是当前模型调用能看到的信息。上下文工程的关键不是塞更多内容，而是把当前决策最需要的信息放进来，把旧观察压缩或沉淀出去。

**Skills** 是可复用专家经验包。它们不是普通 Prompt 模板，而是按需加载的工作方法。系统先看到 Skill 标签，任务匹配后才加载完整说明。

**Memory** 保存跨任务可复用的信息。短期记忆服务当前窗口，长期记忆保存经验、偏好、事实或历史任务结论。记忆的价值不在“存下来”，而在合适时机能被取回。

**SubAgent** 解决上下文隔离。复杂子任务会产生大量中间观察，主 Agent 不应该全部背上。SubAgent 在独立上下文里工作，只把摘要或结果交回主线。

**Task System** 让任务可恢复、可审计。长任务不能只存在聊天历史里，它需要结构化状态、执行记录、错误原因和恢复入口。

**Compact** 处理上下文膨胀。它把旧 trace 和观察压缩进状态，保留最近关键事件，避免 Agent 长时间运行后被噪声淹没。

这些组件合在一起，才构成一个 Harness Agent。少一个组件不一定不能运行，但系统的某种工程能力会缺失。

## 五种基础模式如何进入 Harness

Agent 模式不是抽象分类，它们对应具体的工程风险。

**意图识别** 解决入口分流问题。用户是在问知识、请求读文件、运行测试，还是要求执行高风险动作？入口判断错了，后面的工具和上下文都会错。

**Plan-Act** 解决多步任务失控问题。先生成计划，再逐步执行，可以让任务边界更清楚，也更容易在中途恢复。

**Reflection** 解决结果质量不稳定问题。执行后检查缺口，必要时重试。它的价值不是“让模型自我反省”，而是给失败设置一个反馈回路。

**CodeAct** 解决行动表达力不足问题。有些任务用自然语言描述步骤很笨，用代码更直接。但代码执行必须由 Harness 校验和限制。

**Human-in-the-loop** 解决风险转移问题。不是所有动作都应该自动执行。高影响工具调用、危险命令、不确定修改，都应该进入审批或接管流程。

这些模式最终都要落到 Harness 里。只讲模式名字没有意义，关键是它们如何改变状态、trace、工具边界和恢复路径。

## MiniClaw 原型复盘

为了把这些概念落地，我在仓库里实现了一个本地原型：`prototypes/miniclaw_harness/`。

它不是完整产品，但已经具备一个 Claw 类 Harness 的核心骨架：

- CLI Channel 接收消息。
- SQLite Store 保存消息、任务、trace、state、memory、approval。
- Orchestrator 从队列取消息并调用 runtime。
- SubAgentRuntime 隔离子任务。
- FileTool、BashTool、CodeTool 提供受控工具。
- Skill Loader 渐进加载专家上下文。
- Memory 保存并召回仓库分析经验。
- Task System 支持后台任务、阻塞恢复、审批恢复。
- Compact 支持长 trace 压缩。
- task-report 导出执行证据。

一次 CodeAct 任务的真实报告如下：

```text
Task: subagent: codeact count files
Decision: codeact -> restricted python
Code:
files = list_files()
result = len(files)
print(result)
Observation:
{"result": 1, "status": "ok", "stdout": "1\n"}
State:
kind=codeact
code_source=rule
result=1
status=completed
```

这段报告说明了 Harness 的几个关键点。

第一，模型或规则没有直接接触文件系统，而是通过 `CodeTool` 暴露的 `list_files()`。工具边界属于 Harness。

第二，CodeAct 不是随便执行 Python。模型生成代码时，Harness 会用 AST 白名单验证，拒绝 import、任意函数调用和不安全能力。

第三，执行结果没有只返回给用户，而是同时写入 trace 和 task state。后续可以恢复、审计，也可以导出报告用于复盘。

第四，SubAgent 的中间细节不会污染主上下文。主线只看到任务完成摘要，具体观察保存在后台任务和 trace 中。

这就是 Harness Agent 和普通聊天机器人的差异：它不仅回答“数到了 1 个文件”，而是留下了为什么这么做、做了什么、结果是什么、以后如何检查的证据链。

如果要自己复现这个链路，可以先运行一个 CodeAct 子任务，再导出报告：

```bash
python3 prototypes/miniclaw_harness/main.py \
  --runtime subagent \
  --workspace . \
  send "subagent-background: codeact count files"

python3 prototypes/miniclaw_harness/main.py \
  --runtime subagent \
  --workspace . \
  run-once

python3 prototypes/miniclaw_harness/main.py background-list
python3 prototypes/miniclaw_harness/main.py task-report <task-id>
```

这四步对应 Harness 的最小闭环：接收任务、执行循环、持久化状态、导出证据。读者不需要先理解所有源码，也能看到 Agent 行动链如何被记录下来。

## MiniClaw 里几个工程取舍

MiniClaw 故意保持本地优先。它用 SQLite，而不是一开始接云数据库；用本地 CLI，而不是先接 IM；用受限工具，而不是开放 shell。这些选择降低了学习噪声。

它的 BashTool 只允许少量命令。这样做牺牲了自由度，但换来安全边界清晰。学习 Harness 时，知道什么不能做，和知道能做什么一样重要。

它的 Memory 先做结构化记忆，而不是直接上向量库。因为当前阶段要理解的是“任务经验如何沉淀和召回”，不是优化语义检索效果。

它的 CodeAct 支持模型生成代码，但模型代码必须先过 Harness 校验。模型负责提出候选行动，Harness 负责决定行动是否可以执行。

它的审批门很小，只覆盖显式需要 approval 的测试任务。但这个最小闭环已经说明 Human-in-the-loop 的本质：高风险动作应该暂停、记录原因、等待确认、再恢复执行。

这些取舍共同指向一个原则：学习 Harness，不要先追求能力最大化，而要先让每个能力的边界可见。

## 如何判断一个系统是否进入 Harness Agent

可以用五个问题判断。

第一，它是否有持续行动循环？如果系统只能单轮回答，没有计划、观察、再行动，就还不是 Harness Agent。

第二，它是否通过工具观察和改变环境？如果所有信息都来自用户输入，它只是聊天系统。

第三，它是否管理上下文生命周期？如果历史只是不停追加，没有压缩、选择、技能加载和记忆召回，长任务会很快失控。

第四，它是否持久化任务状态？如果中断后无法恢复，失败后无法解释，审批后无法继续，就缺少工程可用性。

第五，它是否能审计行动证据？真正的 Harness Agent 应该能回答：为什么选这个工具，执行了什么，观察到什么，状态如何变化。

这五个问题比“用了什么模型”更重要。模型能力会变化，但 Harness 的工程问题长期存在。

## 最终理解

Prompt Engineering 让模型在一次调用中表现更好。

Context Engineering 让模型在每次调用时看到正确的信息。

Harness Agent 则让模型进入一个可行动、可恢复、可审计的工程系统。

如果只看模型输出，会以为 Agent 的关键是“更聪明”。但真正写过原型后会发现，Agent 能不能工作，更多取决于模型之外的部分：Loop、Tools、Skills、Memory、SubAgent、Task System、Compact、Approval 和 Trace。

这也是学习 Harness 工程最重要的转变：不要只问模型能不能回答，而要问系统能不能把一次回答变成一条可靠的行动链。
