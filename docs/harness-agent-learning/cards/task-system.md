# Task System

## 解决什么问题

长任务如果只存在聊天上下文里，容易丢进度、难恢复、难审计。Task System 解决的是工作状态持久化和可恢复执行问题。

## 核心机制

把任务拆成结构化记录：目标、状态、步骤、观察、结果、错误。Agent 每完成关键动作就更新任务状态。

## 最小例子

仓库分析任务有状态 `created -> running -> done`，并记录已经读取了哪些文件、最终报告在哪里。

## 和相近概念的区别

Memory 保存信息，Task System 保存工作进度。计划是未来步骤，Task System 还要记录执行状态和结果。

## 在 Harness Agent 原型中的位置

`TaskStore` 把任务保存到 JSON。Demo 运行后会留下任务状态，说明 Agent 工作可以被恢复和审计。
