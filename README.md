# 影城在线票务性能靶场

[![CI](https://github.com/z417/helloFastAPI/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/z417/helloFastAPI/actions/workflows/ci.yml)

> [!IMPORTANT]
> ### 🤖 AI 智能体开发规范与上岗指南 (AI Onboarding Protocol)
> 本项目采取“职责单一，动静分离”的**四维文档架构**。AI 在着手任务前，必须以本 `README.md` 为唯一网关，严格执行以下按需精读下移路由与行为红线。

---

## 一、 📖 文档按需解析与路由协议 (On-Demand Document Resolution)

项目采用“技术规格、领域业务、系统状态”分层解耦的文档架构。AI 执行任务时必须严格遵循以下检索路由：

1. **README.md 入口路由**：AI 必须以根目录 `README.md` 作为唯一引导网关，读取 Documentation Hub 获取本项目特定的技术规格说明书、领域业务约束、运行部署指南及状态文档的最新物理路径。
2. **按需精读下移机制**：
   - **架构设计约束 (SPEC.md)**：涉及底层数据库设计、并发锁控制、核心 API 契约、核心类与数据流设计等架构调整时，必须先精读系统架构规格，且在设计锁解除前严禁改动业务代码。
   - **领域业务规则 (BUSINESS.md)**：涉及特定行业/领域的业务核心逻辑、安全风控、计算/交易结算、状态转移拦截等规则时，必须精读领域业务约束文档。
   - **部署运行验证 (QUICKSTART.md)**：涉及本地运行调试、服务拉起、容器化编排、反向代理、构建编译及系统内核性能调优时，必须参考部署手册。
   - **状态接力恢复 (STATE.md)**：新会话初始化、任务接力或调试现场恢复时，必须精读最新的状态快照。

---

## 二、 🏗️ 项目核心技术栈

1. **环境与包管理器**：
   - **Python 端**：强制使用 **`uv`**（依赖同步：`uv add <pkg>`，执行指令：`uv run <cmd>`）。绝对禁止使用 `pip`、`conda`、`poetry`、`pipenv`。
   - **前端/JS 编译**：强制使用 **`bun`**（依赖同步：`bun install`，执行指令：`bun run <cmd>`）。绝对禁止使用 `npm`、`yarn`、`pnpm`。
2. **后端 API 服务**：FastAPI | Uvicorn | Loguru 结构化日志
3. **异步 ORM 引擎**：SQLAlchemy 2.0+ 异步体系 | `aiosqlite` (SQLite)
4. **前端 UI 界面**：Bootstrap (5.3.0) | FontAwesome (6.4.0) | Vanilla JS

---

## 三、 📂 系统文档导航系统 (Documentation Hub)

* 👉 **[快速开始与部署指南 (QUICKSTART.md)](QUICKSTART.md)**：收录本地与生产环境中关于运行、编译及部署的具体操作指令与脚本配置。
* 👉 **[系统架构与开发规格书 (.gsd/SPEC.md)](.gsd/SPEC.md)**：收录系统核心技术设计方案、高并发数据一致性实现规格。
* 👉 **[领域业务规格说明书 (.gsd/BUSINESS.md)](.gsd/BUSINESS.md)**：收录影院售票特定领域业务逻辑约束、防刷票安全窗口限制及数据播种逻辑。
* 👉 **[系统当前状态与优化波次记录 (.gsd/STATE.md)](.gsd/STATE.md)**：作为会话接力“Save Point”，动态记录系统敏捷迭代快照及测试验证实证。

---

## 四、 ⚠️ AI 智能体开发红线与特定工具约束 (AI Safety Redlines & Tooling Specs)

为确保本项目开发的安全与规范，AI 智能体在处理本仓库任务时必须无条件遵守以下项目特定红线：

1. **三方验证包禁用**：在执行 UI 或自动化验证时，严禁安装、引入或运行任何未经授权的第三方浏览器自动化控制包（如 Playwright、Puppeteer、Selenium 等）。
2. **向下兼容与职责聚焦**：不得以重构为名，在未获授权前破坏或改动任何无关的既有功能与业务逻辑。
3. **高精度计算防溢出**：速率、金额等精度敏感计算，强制使用当前语言推荐的高精度数值计算类型（如 Python 的 `Decimal`），绝对禁止使用标准浮点数直接运算。
4. **版本控制规范 (VCS)**：本项目采用 **Git** 进行版本管理。严禁在 Shell 中执行任何 Git 写入命令（如 `git commit/push/branch`）。所有提交建议必须以 `type(scope): description` 的语义化 Commit 格式在对话末尾呈递。
5. **零占位符完整交付**：禁止输出任何含有占位符（如 `// TODO`、`# ...`）的伪代码。所有生成的代码必须是生产可用、逻辑完整的 Drop-in 交付物。
6. **静态强类型与范式**：
   - **Python**：强制执行严格静态类型提示 (Strict Type Hinting)。优先采用**函数式编程范式 (Zero-Class Design)** 与依赖注入，保持模块职责高内聚、低耦合。
   - **JavaScript**：遵循现代 ES6+ 语法，保持状态单向流与精准的异常捕获。
7. **UI 自动化验证约束**：本项目前端含有 UI 交互。若任务涉及 UI/样式变动，必须强制且唯一使用 IDE 挂载的内置 **Chrome DevTools (CDP) 协议**进行多端响应式视觉走查验证与截屏归档。非 UI 变更或后端修改自动豁免此项。
8. **标准输出与日志规范**：严禁使用原生标准输出打印调试信息，必须统一使用项目结构化日志（如 Loguru）。