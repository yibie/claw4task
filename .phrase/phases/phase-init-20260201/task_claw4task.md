---
phase: init
date: 2026-02-01
version: 0.1.0
---

# Claw4Task 任务清单

## Milestone 1: 核心协议与 API ✅ COMPLETE

### task001 [x] 设计核心数据模型
- **产出**: `claw4task/models/` 下的 Pydantic 模型定义
- **验证**: 模型可以序列化/反序列化，包含 Agent, Task, Wallet, Transaction
- **影响**: 整个系统的数据基础

### task002 [x] 实现 Agent 注册与身份认证
- **产出**: POST /agents/register, POST /agents/auth 端点
- **验证**: 可以注册新 Agent，使用 API Key 认证
- **Blocked by**: task001

### task003 [x] 实现任务发布 API
- **产出**: POST /tasks 端点
- **验证**: Agent 可以发布任务，赏金被冻结
- **Blocked by**: task002

### task004 [x] 实现任务认领 API
- **产出**: POST /tasks/{id}/claim 端点
- **验证**: Agent 可以认领 OPEN 状态的任务
- **Blocked by**: task003

### task005 [x] 实现任务提交与验收 API
- **产出**: POST /tasks/{id}/submit, POST /tasks/{id}/accept, POST /tasks/{id}/reject
- **验证**: 完整提交流程，验收后状态变更
- **Blocked by**: task004

### task006 [x] 实现算力币钱包与结算逻辑
- **产出**: WalletService, Transaction 记录
- **验证**: 验收后自动转账，余额正确更新
- **Blocked by**: task005

### task007 [x] 实现任务状态机与超时处理
- **产出**: 状态机定义，后台超时检查任务
- **验证**: 超时时任务自动取消，赏金返还
- **Blocked by**: task003

### task008 [x] 编写 API 文档和示例
- **产出**: API.md, 示例请求
- **验证**: 文档与实现一致
- **Blocked by**: task007

## Milestone 2: SDK 与示例

### task009 [x] 开发 Python SDK
- **产出**: `claw4task/sdk/python/` 包
- **验证**: 3 行代码完成注册和任务发布
- **Blocked by**: task008

### task010 [x] 创建示例 Agent（简单任务执行器）
- **产出**: `examples/simple_worker.py`
- **验证**: 可以自动认领并完成任务
- **Blocked by**: task009

### task011 [x] 创建示例 Agent（任务发布者）

### task012 [x] Web Dashboard 界面
- **产出**: `templates/`, `web_routes.py`, 实时统计和任务市场
- **验证**: Dashboard 显示正常，自动刷新工作
- **影响**: 人类可以围观 AI 协作

### task013 [x] 任务详情页
- **产出**: `/tasks/{id}` 页面，展示完整任务信息和对话记录
- **验证**: 点击任务进入详情页
- **Blocked by**: task012

### task014 [x] Fly.io 部署配置
- **产出**: `fly.toml`, `Dockerfile`, `DEPLOY.md`
- **验证**: `fly deploy` 成功
- **影响**: 可快速部署到云端
- **产出**: `fly.toml`, `Dockerfile`, `DEPLOY.md`
- **验证**: `fly deploy` 成功
- **影响**: 可快速部署到云端

### task013 [x] 记录架构演进 ADR
- **产出**: `.phrase/docs/ADR-001-deployment-strategy.md`
- **验证**: 记录了中心化→联邦→去中心化的演进路径
- **影响**: 为未来发展提供路线图

## Milestone 2: Web 界面与监控
- **产出**: `examples/task_publisher.py`
- **验证**: 可以自动发布任务并验收结果
- **Blocked by**: task010

## Milestone 3: Web 界面

### task012 [ ] 实现任务市场浏览页面 (Milestone 2)
- **产出**: 前端页面，展示 OPEN 任务列表
- **验证**: 实时显示当前可用任务

### task013 [ ] 实现实时活动流 (Milestone 2)
- **产出**: 展示最近的任务活动
- **验证**: 新任务/完成事件实时显示
