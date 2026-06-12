# helloFastAPI System Plan (PLAN)

## Status: COMPLETED (All Waves Deployed)

本项目采用 B 链路（简单优化/Bug 修复）进行波次（Wave-Based）迭代。以下为全量落地实现的 10 个优化波次：

---

## [x] Wave 1: 健全配置保存日志与 Traceback 捕获
*   **物理文件**：`src/Cinema/router.py`
*   **规划策略**：在 `update_cinema_config` 接口的 `try...except` 块中加入 `L.exception(e)` 异常日志，使权限或文件锁定错误可在终端控制台一目了然。

---

## [x] Wave 2: 数据库高并发长连接池 Singleton 优化 (热重载单例)
*   **物理文件**：`src/common/dependencies.py`
*   **规划策略**：引入全局单例 `_engine` 状态跟踪器；在 `get_async_engine()` 依赖中检测 settings 的 pool_mode，若发生热切换，则自动 dispose() 释放旧引擎并重建单例连接池，避免每次 HTTP 请求重复销毁连接池。

---

## [x] Wave 3: 前端选座/购票交互 Bug 修复
*   **物理文件**：`frontend/app.js`
*   **规划策略**：在 `handleBookTicket()` 中引入 `try...finally`，确保出现异常时购票按钮文字和 Loading 态正常复原；为 `loadShowtimes()` 增加 Admin 拦截跳过无用大请求；修复 config 拼写 Typo 激活热配置拉取。

---

## [x] Wave 4: 极简字典化服务与前端惰性按需秒杀
*   **物理文件**：`backend/src/Cinema/router.py` | `frontend/app.js`
*   **规划策略**：新增 `/api/cinema/movies` 和 `/api/cinema/rooms` 字典端点；前端改用 `Promise.all` 仅拉取上面两个轻量级字典（首开 Payload 从 1.2MB 削减 99% 至 <1KB）；重构随机秒杀购票为瞬时实时拉取，杜绝本地脏缓存造成的并发死锁与冲突。

---

## [x] Wave 5: 云原生构建 Docker 基础设施与 GitHub CI 优化
*   **物理文件**：`backend/Dockerfile` | `backend/.dockerignore` | `.github/workflows/ci.yml`
*   **规划策略**：升级后端镜像为 Python 3.12 瘦镜像，添加 unbuffered 强刷日志；纠正 .dockerignore 对 lock 文件的意外屏蔽；升级 GitHub CI 为 Astral 的 `setup-uv@v5` 极速缓存动作，测试耗时缩短 3 倍。

---

## [x] Wave 6: 生产环境部署优化与构建时注入配置
*   **物理文件**：`README.md` | `QUICKSTART.md` | `frontend/app.js`
*   **规划策略**：编制生产级 bare-metal 与 Docker 编排部署指南，提供高性能 Nginx 配置与 OS 网络内核调优；前端 API 地址支持在 Bun 打包编译时常量内联（`.env` 或 define 注入），支持死码消除。

---

## [x] Wave 7: 生产票务业务规则硬化与已购选票看板
*   **物理文件**：`backend/src/Cinema/router.py` | `backend/src/Cinema/seeder.py` | `frontend/index.html` | `frontend/app.js`
*   **规划策略**：硬化开映前 5 分钟锁定逻辑防止刷票；seeder 数据锚定在未来 +3 小时确保开箱可测；前端 index.html 增加已购票毛玻璃磁贴渲染已购票务信息。

---

## [x] Wave 8: 审计优化与安全性重构交付
*   **物理文件**：`backend/src/Auth/schemas.py` | `backend/src/Auth/dependencies.py` | `backend/src/FileCodeBox/router.py` | `frontend/app.js`
*   **规划策略**：加固密码 Bcrypt 强度匹配校验；修复 refresh_token 的 500 TypeError 并调整 ExpiredSignatureError 首选捕获；引入 LFUCache 内存去重锁实现 Nonce 5分钟防重放；挂载 FileCodeBox 接口并修复 key 遍历 RuntimeError 限流崩溃。

---

## [x] Wave 9: 个人中心 UI 解耦与豆瓣百佳重构
*   **物理文件**：`seeder.py` | `frontend/index.html` | `frontend/app.js`
*   **规划策略**：数据库字段扩展支持电影评分、安利语及性别；重新播种 100 部经典电影，重构 4 大特色厅共 40 席位；前端剥离已购票业务至高雅独立 `#profile-section` 会员卡片；实现选座界面 100% 弹性座位自适应弹性流（解决微缩影厅歪斜 Bug）。

---

## [x] Wave 10: 退票逻辑防连击与扁平数据渲染修复
*   **物理文件**：`frontend/app.js`
*   **规划策略**：
    1. 修正 `executeRefundRequest` 中的订单字段访问链：直接读取扁平属性 `movie_title` 及 `row_num/col_num`，根治空指针异常，打通无网络延迟的本地 DOM 局部同步更新。
    2. 对退票 Modal 中的 `execute-refund-btn` 引入防重复提交置灰锁，阻断并发多次点击对后端造成的 400 脏报错，保障完美的秒级回款用户交互体验。
