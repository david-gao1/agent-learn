# Context Engineering

## 解决什么问题

模型本身只看到当前输入窗口。Context Engineering 解决的是：在一次调用里，应该把哪些目标、历史、工具结果、约束、知识和状态交给模型，哪些应该压缩、延迟或丢弃。

## 核心机制

把上下文当成工程对象管理：选择信息、组织顺序、控制长度、压缩历史、按需加载 Skill 或资料，并让每次模型调用都服务于当前决策。

## 最小例子

让 Agent 分析代码仓库时，不把整个仓库塞进提示词，而是先给任务目标和目录结构，再按需要读取关键文件，最后把中间观察压缩成摘要。

## 和相近概念的区别

Prompt Engineering 主要优化单次指令表达。Context Engineering 设计的是信息供应链：什么信息进入上下文、何时进入、以什么形态进入、何时退出。

## 在 Harness Agent 原型中的位置

`HarnessAgent` 组织任务、Skill、工具观察和消息历史；`compact_messages` 负责压缩旧上下文，`LocalSkillLoader` 负责按需加载专家上下文。
