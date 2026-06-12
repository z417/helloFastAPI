# helloFastAPI System State (STATE)

## Status: COMPLETED & HEALTHY (Wave 10 Deployed)

本文件作为会话接力与现场恢复的“Save Point”，记录系统的当前物理状态及已落地波次快照。

---

## 1. 系统当前物理参数快照

- **环境**：Python 3.12 (slim) | Bun
- **包管理器**：`uv` (Backend) | `bun` (Frontend)
- **数据库**：SQLite (`sqlite+aiosqlite`)
- **热调参数快照**：
  - `DB_POOL_MODE` = `queue`
  - `BOOKING_LOCK_MODE` = `optimistic`
  - `CINEMA_SLOW_QUERY` = `False`
  - `BOOKING_SIGNATURE_CHECK` = `False`
  - `BOOKING_SM3_SIGNATURE_CHECK` = `False`
  - `BOOKING_SM4_PASSWORD_ENCRYPT` = `False`

---

## 2. 已落地实现的全部优化波次 (Wave Snapshots)

### Wave 1: 健全配置保存日志与 Traceback 捕获
- 在 `/api/cinema/config` 中补全 `L.exception(e)` 物理持久化日志。

### Wave 2: 数据库高并发长连接池 Singleton 优化
- 引入热重载 `AsyncEngine` 状态监听单例，实现长连接池全局复用。

### Wave 3: 前端交互 Bug 修复
- 修复 `handleBookTicket()` 加载卡死、Admin 登录冗余请求及配置拉取拼写错误。

### Wave 4: 极简字典化服务与前端惰性按需秒杀
- 新增 movies 与 rooms 极简字典 API；前端并行加载首开，随机秒杀改为瞬时按需拉取。

### Wave 5: 云原生 Docker 基础设施与 GitHub Actions CI 优化
- Dockerfile 升级为 slim 镜像；CI 流水线引入 `setup-uv@v5` 极速缓存，去除非必要长挂载进程。

### Wave 6: 生产环境部署优化与构建时注入配置
- 编制 Nginx 动静分离、内核参数调优指南；前端 API 引入 Bun 编译构建时常量内联。

### Wave 7: 生产票务业务规则硬化与已购选票看板
- 后端下单与排片硬化 5 分钟锁定；seeder 播种在未来 3 小时；前端新增已购票毛玻璃磁贴。

### Wave 8: 审计优化与安全性重构交付
- 增加密码 Bcrypt 哈希强度校验；修复 refresh_token 转换崩溃与过期 JWT 捕获顺序；引入 Nonce 去重去重防重放；自驱动 IP 限流并消除 Runtime 清理崩溃。

### Wave 9: 个人中心 UI 解耦与豆瓣百佳重构
- 数据库扩展电影评分等字段；seeder 重新播种 100 部电影与 4 大精品厅；前端个人信息与已购票剥离至 `#profile-section`；选座界面自适应弹性列。

### Wave 10: 退票逻辑防连击与扁平数据渲染修复
- **前端修复**：纠正 `executeRefundRequest` 对扁平订单 `refundObj` 的属性访问以消除空指针崩溃；对 `handleRefund` 确认按钮引入 `disabled` 状态锁防连击，消除高频双击导致的后端 400 脏报错拦截。
- **后端保证**：退票操作加悲观锁并保持状态机与库存/版本号的一致性变更。
