/**
 * 在线影城订票系统 - 前端交互逻辑
 * 强制安全防范，多维度联动筛选，非阻塞 Toast 提示
 */

// API 路由常量注入与自适应自愈逻辑
// 1. 优先使用 Bun 编译构建时从 .env 文件或 --define 注入的 process.env.API_URL 常量
// 2. 若无构建注入（如直接用浏览器打开静态文件开发），则自动启用零配置智能端口自适应解析
const API_BASE_URL = (typeof process !== "undefined" && process.env && process.env.API_URL)
    ? process.env.API_URL
    : ((window.location.port && window.location.port !== "8000")
        ? `${window.location.protocol}//${window.location.hostname}:8000/api`
        : "/api");
let currentToken = sessionStorage.getItem("token") || null;
let currentRole = sessionStorage.getItem("role") || "user";

// 全局 Fetch 拦截器：统一处理 401 越权与单点登录被踢下线逻辑，阻断无限自愈重试
const originalFetch = window.fetch;
window.fetch = async function (...args) {
    const response = await originalFetch(...args);
    if (response.status === 401 && currentToken) {
        let errMsg = "您的登录会话已失效，请重新登录！";
        try {
            const clone = response.clone();
            const data = await clone.json();
            const detail = data.detail || "";
            if (detail.includes("elsewhere")) {
                errMsg = "您的账号已在其他终端登录，当前会话已失效，请重新登录！";
            }
        } catch (e) { }

        handleLogout();
        showToast(errMsg, "danger");
        throw new Error("Session expired or logged in elsewhere");
    }
    return response;
};
let selectedShowtimeId = null;
let selectedSeatId = null;
let signatureSecret = "";
let sm4Key = "";
let currentUserProfile = null; // 全局缓存用户 profile 信息



// 全局场次与座位缓存，供多维度智能联动筛选
let allShowtimes = [];
let currentSeats = [];

// 分页状态控制 (测算大表深度分页压测效率的黄金底座)
let currentPage = 1;
const pageSize = 6; // 每页精致呈现 6 场排片卡片
let totalCount = 0;

// 已购选票滚动加载控制 (高频物理分页滚动自愈机制)
let myTicketsPage = 1;
const myTicketsLimit = 10;
let myTicketsHasMore = true;
let isMyTicketsLoading = false;
let loadedTickets = [];
let ticketObserver = null;

// ==================== 0. 优雅非阻塞 Toast 提示组件 ====================

/**
 * 优雅非阻塞 Toast 消息提示
 * @param {string} message 提示文本
 * @param {string} type 提示类型 ('success' | 'danger' | 'warning' | 'info')
 */
function showToast(message, type = "info") {
    const toastEl = document.getElementById("status-toast");
    const bodyEl = document.getElementById("toast-message-body");
    const iconContainer = document.getElementById("toast-icon-container");

    // 清理既往背景样式，采用高品质毛玻璃黑灰底色，仅以发光图标和微弱阴影区分配色
    toastEl.classList.remove("border-success", "border-danger", "border-warning", "border-info");

    // 动态绑定精致微光图标与边框微弱辉光
    let iconHtml = "";
    let borderClass = "border-info";

    if (type === "success") {
        iconHtml = `<i class="fa-solid fa-circle-check text-success fs-5 animate-pulse" style="text-shadow: 0 0 8px rgba(16, 185, 129, 0.4);"></i>`;
        borderClass = "border-success";
    } else if (type === "danger") {
        iconHtml = `<i class="fa-solid fa-circle-xmark text-danger fs-5 animate-pulse" style="text-shadow: 0 0 8px rgba(239, 68, 68, 0.4);"></i>`;
        borderClass = "border-danger";
    } else if (type === "warning") {
        iconHtml = `<i class="fa-solid fa-triangle-exclamation text-warning fs-5 animate-pulse" style="text-shadow: 0 0 8px rgba(245, 158, 11, 0.4);"></i>`;
        borderClass = "border-warning";
    } else {
        iconHtml = `<i class="fa-solid fa-circle-info text-info fs-5 animate-pulse" style="text-shadow: 0 0 8px rgba(56, 189, 248, 0.4);"></i>`;
        borderClass = "border-info";
    }

    toastEl.classList.add(borderClass);
    toastEl.style.borderWidth = "1.5px";
    iconContainer.innerHTML = iconHtml;
    bodyEl.textContent = message;

    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
}

/**
 * 初始化管理端配置说明 Popover，挂载到 body 避免被卡片容器裁剪
 */
function initAdminTipPopovers() {
    document.querySelectorAll('[data-bs-toggle="popover"]').forEach((triggerEl) => {
        triggerEl.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            triggerEl.focus();
        });

        new bootstrap.Popover(triggerEl, {
            container: "body",
            html: true,
            sanitize: false,
            fallbackPlacements: ["bottom", "right", "left"],
        });
    });
}

// ==================== 1. 原生安全签名与UUID正则防御 ====================

/**
 * 客户端 SHA-256 签名计算引擎
 */
async function computeSignature(showtimeId, seatId, timestamp, nonce) {
    const payload = `${showtimeId}${seatId}${timestamp}${nonce}${signatureSecret}`;

    return CryptoJS.SHA256(payload).toString(CryptoJS.enc.Hex);
}


/**
 * 严格防范非法参数注入：API请求前进行 UUID 强校验
 */
function isValidUUID(uuidStr) {
    const regex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return regex.test(uuidStr);
}

// ==================== 2. 页面加载初始化 ====================
document.addEventListener("DOMContentLoaded", () => {
    // 初始化管理端配置说明悬浮卡片
    initAdminTipPopovers();

    // 动态初始化未来30天日期筛选器的 min 与 max 范围
    initFilterDateBounds();

    if (currentToken) {
        updateUIState(true);
        // 静默获取用户 profile 缓存，不阻塞排片
        fetchUserProfile(false);
        loadShowtimes();
        if (currentRole === "admin") {
            loadCinemaConfig();
        } else {
            loadMyTickets();
            // 读取本地缓存的视图状态并还原，实现无缝刷新保持
            const savedView = sessionStorage.getItem("current_view");
            if (savedView === "profile") {
                toggleProfile("profile");
            }
        }
    } else {
        updateUIState(false);
    }

    // 绑定多维度联合检索监听器 (任何检索项的改变都会重置页码并向后端发起远程联合检索)
    document.getElementById("filter-search-name").addEventListener("input", resetPageAndFilter);
    document.getElementById("filter-date").addEventListener("change", resetPageAndFilter);
    document.getElementById("filter-movie").addEventListener("change", resetPageAndFilter);
    document.getElementById("filter-room").addEventListener("change", resetPageAndFilter);
    document.getElementById("filter-time-range").addEventListener("change", resetPageAndFilter);

    // 修复 Bootstrap Modal aria-hidden 焦点警告 (WAI-ARIA)
    // Bootstrap 在 Modal 关闭时先设置 aria-hidden="true"，再将焦点转移出去，
    // 导致短暂出现"Blocked aria-hidden on a focused element"控制台警告。
    // 在 hide.bs.modal 事件触发时（aria-hidden 写入前）主动 blur，彻底消除警告。
    document.querySelectorAll('.modal').forEach(modalEl => {
        modalEl.addEventListener('hide.bs.modal', () => {
            if (document.activeElement instanceof HTMLElement) {
                document.activeElement.blur();
            }
        });
    });
});


/**
 * 重置页码并联动筛选
 */
function resetPageAndFilter() {
    currentPage = 1;
    filterShowtimes();
}

/**
 * 初始化日期筛选范围：起止为 [今天, 30天后]
 */
function initFilterDateBounds() {
    const dateInput = document.getElementById("filter-date");
    const today = new Date();

    // 转化为 YYYY-MM-DD
    const formatDate = (d) => {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    const minDateStr = formatDate(today);

    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 30);
    const maxDateStr = formatDate(maxDate);

    dateInput.min = minDateStr;
    dateInput.max = maxDateStr;
    dateInput.value = minDateStr; // 默认选中今天以呈现今日排片
}

// ==================== 3. 会员登录/退出流程 ====================
async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    let sendPassword = password;
    try {
        const configResp = await fetch(`${API_BASE_URL}/cinema/config?_=${Date.now()}`, { cache: "no-store" });
        if (configResp.ok) {
            const configRes = await configResp.json();
            if (configRes.data && configRes.data.sm4_password_encrypt) {
                const keyStr = configRes.data.sm4_key || sm4Key;
                let hexKey = "";
                for (let i = 0; i < keyStr.length; i++) {
                    hexKey += keyStr.charCodeAt(i).toString(16).padStart(2, "0");
                }

                // 1. 生成 16 字节高随机 IV
                let ivHex = "";
                for (let i = 0; i < 16; i++) {
                    ivHex += Math.floor(Math.random() * 256).toString(16).padStart(2, "0");
                }

                // 2. 组装内嵌 13 位高精度时间戳的明文负载
                const timestamp = Date.now().toString();
                const plainPayload = `${timestamp}:${password}`;

                // 3. SM4 CBC 加密，并头部附带 IV 进行融合拼接
                const cipherTextHex = sm4.encrypt(plainPayload, hexKey, {
                    mode: "cbc",
                    iv: ivHex
                });
                sendPassword = ivHex + cipherTextHex;
            }
        }
    } catch (e) {
        console.warn("拉取国密密码配置失败，使用明文传输", e);
    }

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", sendPassword);

    try {
        const response = await fetch(`${API_BASE_URL}/auth/token`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "邮箱或密码错误，登录失败");
        }

        const data = await response.json();
        currentToken = data.access_token;
        sessionStorage.setItem("token", currentToken);

        // 登录成功后，立刻获取用户角色 Profile
        await fetchUserProfile(true);
    } catch (error) {
        showToast(error.message, "danger");
    }
}

async function fetchUserProfile(isLoginTrigger = false) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/profile`, {
            headers: {
                "Authorization": `Bearer ${currentToken}`
            }
        });

        if (!response.ok) throw new Error("获取用户信息失败");
        const res = await response.json();
        const user = res.data;
        currentUserProfile = user; // 缓存用户 profile 信息

        // 根据邮箱判定身份级别
        if (user.email === "admin@cinema.com") {
            currentRole = "admin";
        } else {
            currentRole = "user";
        }
        sessionStorage.setItem("role", currentRole);

        if (isLoginTrigger) {
            showToast(`登录成功！欢迎您，${user.full_name || "会员观众"}`, "success");
            updateUIState(true);
            loadShowtimes();
            if (currentRole === "admin") {
                await loadCinemaConfig();
            } else {
                await loadMyTickets();
                renderUserProfileCard(); // 自动渲染个人 Profile 卡片
            }
        } else {
            if (currentRole === "user") {
                renderUserProfileCard();
            }
        }
    } catch (error) {
        handleLogout();
    }
}

function handleLogout() {
    currentToken = null;
    currentRole = "user";
    selectedShowtimeId = null;
    selectedSeatId = null;
    allShowtimes = [];
    currentSeats = [];
    currentPage = 1;
    totalCount = 0;
    currentUserProfile = null;
    sessionStorage.clear();
    updateUIState(false);

    // 清理已购选票缓存显示
    const countBadge = document.getElementById("ticket-count-badge");
    const container = document.getElementById("tickets-list-container");
    if (countBadge) countBadge.textContent = "0 张";
    if (container) container.innerHTML = `<div class="col-12 text-center text-secondary py-3 small">暂无已购选票记录</div>`;

    // 重置个人中心按钮文字和样式
    const profileBtn = document.getElementById("profile-btn");
    if (profileBtn) {
        profileBtn.innerHTML = `<i class="fa-solid fa-user me-1"></i>个人中心`;
        profileBtn.className = "btn btn-outline-info btn-sm me-2";
    }

    showToast("已成功退出登录，在线影城期待您的下次光临！", "info");
}

// 刷新 UI 显示自适应状态 (特权管理员与普通会员物理强隔离)
function updateUIState(isLoggedIn) {
    const loginContainer = document.getElementById("login-container");
    const mainPanel = document.getElementById("main-panel");
    const logoutBtn = document.getElementById("logout-btn");
    const userInfoText = document.getElementById("user-info-text");
    const bookingSection = document.getElementById("cinema-booking-section");
    const adminSection = document.getElementById("admin-control-section");
    const profileSection = document.getElementById("profile-section");
    const profileBtn = document.getElementById("profile-btn");

    if (isLoggedIn) {
        loginContainer.classList.add("d-none");
        mainPanel.classList.remove("d-none");
        logoutBtn.classList.remove("d-none");

        if (currentRole === "admin") {
            const adminName = currentUserProfile ? ` (${currentUserProfile.full_name || '管理员'})` : "";
            userInfoText.textContent = `当前身份: 影城值班经理${adminName}`;
            adminSection.classList.remove("d-none");
            bookingSection.classList.add("d-none"); // 管理员彻底物理隐藏购票中心
            profileSection.classList.add("d-none");
            profileBtn.classList.add("d-none");
        } else {
            const userName = currentUserProfile ? ` (${currentUserProfile.full_name || '会员观众'})` : "";
            userInfoText.textContent = `当前身份: 影城尊贵会员${userName}`;
            bookingSection.classList.remove("d-none"); // 会员可见购票中心
            profileSection.classList.add("d-none"); // 默认隐藏个人中心
            adminSection.classList.add("d-none"); // 会员物理强行隐藏系统维护面板
            profileBtn.classList.remove("d-none"); // 显示个人中心按钮
        }
    } else {
        loginContainer.classList.remove("d-none");
        mainPanel.classList.add("d-none");
        logoutBtn.classList.add("d-none");
        bookingSection.classList.add("d-none");
        adminSection.classList.add("d-none");
        profileSection.classList.add("d-none");
        profileBtn.classList.add("d-none");
        userInfoText.textContent = "未登录";
    }
}

// ==================== 4. 业务数据获取与联合智能检索 ====================

// 首次物理拉取：从极简字典接口获取电影与影厅并填充下拉，避免加载 1000 条排片带来的巨大网络及 CPU 瓶颈
async function loadShowtimes() {
    if (currentRole === "admin") return;
    const container = document.getElementById("showtime-list-container");
    container.innerHTML = `<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin text-info fs-3"></i><p class="mt-2 text-muted">正在获取排片计划...</p></div>`;

    try {
        // 并行拉取极简上映电影与影厅字典
        const [moviesResp, roomsResp] = await Promise.all([
            fetch(`${API_BASE_URL}/cinema/movies`, { headers: { "Authorization": `Bearer ${currentToken}` } }),
            fetch(`${API_BASE_URL}/cinema/rooms`, { headers: { "Authorization": `Bearer ${currentToken}` } })
        ]);

        if (!moviesResp.ok || !roomsResp.ok) throw new Error("初始化上映信息字典失败");

        const [moviesRes, roomsRes] = await Promise.all([moviesResp.json(), roomsResp.json()]);

        // 直接动态渲染电影与影厅的检索下拉框
        populateFilterDropdowns(moviesRes.data, roomsRes.data);

        // 联动执行第一轮上映联合检索 (加载今日第一页分页卡片，单页 limit=6，极速响应)
        currentPage = 1;
        await filterShowtimes();

    } catch (error) {
        container.innerHTML = `<div class="col-12 text-center text-danger py-4"><i class="fa-solid fa-triangle-exclamation me-1"></i>${error.message}</div>`;
    }
}

/**
 * 动态加载并渲染电影与影厅的检索下拉框
 */
function populateFilterDropdowns(movies, rooms) {
    const movieSelect = document.getElementById("filter-movie");
    const roomSelect = document.getElementById("filter-room");

    // 填充电影下拉框
    movieSelect.innerHTML = `<option value="all">全部上映电影</option>`;
    movies.forEach(m => {
        const option = document.createElement("option");
        option.value = m.uid;
        option.textContent = m.title;
        movieSelect.appendChild(option);
    });

    // 填充影厅下拉框
    roomSelect.innerHTML = `<option value="all">全部上映影厅</option>`;
    rooms.forEach(r => {
        const option = document.createElement("option");
        option.value = r.uid;
        option.textContent = r.name;
        roomSelect.appendChild(option);
    });
}

/**
 * 核心联合检索机制：将“模糊搜索、日期筛选、电影筛选、影厅筛选、时间段筛选” 5 大参数合并拼装，
 * 每次都实时向后端 API 发起联合检索网络请求，在后端数据库 SQL 层完成高并发交集联合过滤！
 * 以此验证高并发下由于慢 SQL 带来的线程池瓶颈及数据库真实的查询效率！
 */
async function filterShowtimes() {
    const searchName = document.getElementById("filter-search-name").value.trim();
    const selectedDateStr = document.getElementById("filter-date").value; // "YYYY-MM-DD"，允许为空(不限日期)
    const selectedMovieUid = document.getElementById("filter-movie").value;
    const selectedRoomUid = document.getElementById("filter-room").value;
    const selectedTimeRange = document.getElementById("filter-time-range").value;
    const container = document.getElementById("showtime-list-container");

    // 【强防残留误导自愈】：发起新一轮的主动检索时，自动清空并物理隐藏上一场残留的选座，杜绝用户买错票的幻觉！
    selectedShowtimeId = null;
    selectedSeatId = null;
    const seatingSec = document.getElementById("seating-section");
    if (seatingSec) {
        seatingSec.classList.add("d-none");
    }

    // 【弹性自适应防抖高度锁】：抓取当前排片容器实际物理高度并锁定为 min-height，完美防范 loading 时高度缩水产生的滚动条崩塌抖动，适配一切终端设备！
    const currentHeight = container.getBoundingClientRect().height;
    if (currentHeight > 0) {
        container.style.minHeight = `${currentHeight}px`;
    } else {
        container.style.minHeight = "320px"; // 冷启动首载优雅兜底
    }

    container.innerHTML = `<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin text-info fs-3"></i><p class="mt-2 text-muted">正在检索影城排片...</p></div>`;

    // 动态拼装 URL Query String，包含 limit/offset 物理层分页
    const offset = (currentPage - 1) * pageSize;
    const params = new URLSearchParams();
    params.append("limit", pageSize);
    params.append("offset", offset);
    if (searchName) params.append("search_name", searchName);
    if (selectedDateStr) params.append("date", selectedDateStr);
    if (selectedMovieUid !== "all") params.append("movie_id", selectedMovieUid);
    if (selectedRoomUid !== "all") params.append("room_id", selectedRoomUid);
    if (selectedTimeRange !== "all") params.append("time_range", selectedTimeRange);

    try {
        const response = await fetch(`${API_BASE_URL}/cinema/showtimes?${params.toString()}`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });

        if (!response.ok) throw new Error("联合检索失败，请确认系统状态");
        const res = await response.json();

        // 存储总数
        totalCount = res.data.total;

        // 直接交给物理渲染器渲染后端返回的过滤列表
        renderShowtimes(res.data.showtimes);

        // 释放弹性高度锁
        container.style.minHeight = "auto";

        // 渲染高保真分页条状态
        renderPaginationBar();

        // 【平滑滚动翻页对齐】：若为用户主动翻页或联合检索切换，重绘完成后平滑将视口对齐到排片舱顶部，优雅不抖动
        const bookingSec = document.getElementById("cinema-booking-section");
        if (bookingSec && currentHeight > 0) {
            bookingSec.scrollIntoView({ behavior: "smooth", block: "start" });
        }

    } catch (error) {
        container.style.minHeight = "auto"; // 异常时也必须释放锁
        container.innerHTML = `<div class="col-12 text-center text-danger py-4"><i class="fa-solid fa-triangle-exclamation me-1"></i>${error.message}</div>`;
        document.getElementById("pagination-container").classList.add("d-none");
    }
}

/**
 * 物理渲染符合联合检索条件的场次卡片流
 * Bug 修复：在卡片上以 "YYYY-MM-DD HH:MM" 完美且时区绝对免疫展示放映时间
 */
function renderShowtimes(showtimes) {
    const container = document.getElementById("showtime-list-container");
    container.innerHTML = "";

    if (showtimes.length === 0) {
        container.innerHTML = `<div class="col-12 text-center text-secondary py-5"><i class="fa-solid fa-compass me-2 text-info animate-pulse"></i>未找到匹配的排片，请调整检索条件。</div>`;
        return;
    }

    // 【动态高度物理锁】：若检索结果只有 1 部电影，取消 min-height: 100% 强制拉伸，自适应收缩内容。
    // 多部电影时则保持 100% 保证视觉对齐等高！
    const minHeightStyle = showtimes.length === 1 ? "min-height: auto;" : "min-height: 100%;";

    showtimes.forEach(s => {
        // 绝对时区免疫的时间与日期提取 (基于 start_time 字符串进行切割，彻底杜绝北京时间跨天 Bug，并在卡片上完整显示)
        const sDateStr = s.start_time.split('T')[0]; // "YYYY-MM-DD"
        const timePart = s.start_time.split('T')[1];
        const startTimeStr = timePart ? timePart.substring(0, 5) : "00:00"; // 获取 "17:26"
        const fullShowTimeStr = `${sDateStr} ${startTimeStr}`; // 合体为: "2026-05-28 17:26"

        const ratingVal = s.movie.rating ? parseFloat(s.movie.rating).toFixed(1) : "9.0";
        const genresVal = s.movie.genres || "经典";
        const summaryVal = s.movie.summary || "殿堂级光影佳作，倾情推荐。";

        const col = document.createElement("div");
        col.className = "col-md-6 col-lg-4";
        col.innerHTML = `
            <div id="showtime-card-${s.uid}" class="card p-3 movie-card ${selectedShowtimeId === s.uid ? 'active' : ''}" style="height: auto; ${minHeightStyle} cursor:pointer; border: 1px solid #334155;" onclick="selectShowtime('${s.uid}', '${s.room.name}', '${s.movie.title}')">
                <div class="d-flex justify-content-between align-items-start">
                    <h6 class="fw-bold text-info text-truncate mb-0" style="max-width:70%;"><i class="fa-solid fa-clapperboard me-1"></i>${s.movie.title}</h6>
                    <span class="badge bg-secondary" style="font-size: 10px;">${s.movie.duration}m</span>
                </div>
                
                <div class="d-flex align-items-center gap-2 mt-1" style="font-size: 11px;">
                    <span class="text-warning fw-bold"><i class="fa-solid fa-star me-1"></i>${ratingVal}</span>
                    <span class="text-secondary">/</span>
                    <span class="text-secondary text-truncate" style="max-width: 150px;">${genresVal}</span>
                </div>

                <p class="small text-secondary mb-2 mt-2" style="font-size: 12px;"><i class="fa-solid fa-clock me-1"></i>放映时间：<strong class="text-white">${fullShowTimeStr}</strong></p>
                
                <div class="d-flex justify-content-between align-items-center mt-2" style="font-size: 12px;">
                    <span class="small text-secondary">放映影厅：<strong class="text-white">${s.room.name}</strong></span>
                    <span id="showtime-inventory-${s.uid}" class="badge bg-primary text-white" style="font-size: 10px; letter-spacing: 0.5px;">席位余量: ${s.remaining_inventory} / ${s.room.total_seats}</span>
                </div>

                <div class="mt-2 pt-2 border-top border-secondary-subtle text-secondary small fst-italic text-truncate" title="${summaryVal}" style="font-size: 11px;">
                    “ ${summaryVal} ”
                </div>

                <div class="text-end mt-2">
                    <strong class="text-warning fs-5">￥${s.price}</strong>
                </div>
            </div>
        `;
        container.appendChild(col);
    });
}

/**
 * 物理渲染高品质微动分页导航栏
 */
function renderPaginationBar() {
    const bar = document.getElementById("pagination-container");
    const pageInfo = document.getElementById("page-info-text");
    const prevBtn = document.getElementById("prev-page-btn");
    const nextBtn = document.getElementById("next-page-btn");

    if (totalCount === 0) {
        bar.classList.add("d-none");
        return;
    }

    bar.classList.remove("d-none");
    const totalPages = Math.ceil(totalCount / pageSize);
    pageInfo.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页 (共 ${totalCount} 场排片)`;

    // 禁用/解锁上一页按钮
    if (currentPage === 1) {
        prevBtn.disabled = true;
        prevBtn.classList.add("opacity-50");
    } else {
        prevBtn.disabled = false;
        prevBtn.classList.remove("opacity-50");
    }

    // 禁用/解锁下一页按钮
    if (currentPage >= totalPages) {
        nextBtn.disabled = true;
        nextBtn.classList.add("opacity-50");
    } else {
        nextBtn.disabled = false;
        nextBtn.classList.remove("opacity-50");
    }
}

/**
 * 分页切换动作
 */
function changePage(direction) {
    const totalPages = Math.ceil(totalCount / pageSize);
    const newPage = currentPage + direction;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        filterShowtimes();
    }
}

// 选中某个放映场次以加载座位占用图 (防范非法 UUID)
async function selectShowtime(showtimeId, roomName, movieTitle) {
    if (!isValidUUID(showtimeId)) {
        showToast("非法的场次ID格式，安全拦截！", "danger");
        return;
    }

    // 视觉激活高亮
    if (selectedShowtimeId) {
        const prevCard = document.getElementById(`showtime-card-${selectedShowtimeId}`);
        if (prevCard) prevCard.classList.remove("active");
    }
    selectedShowtimeId = showtimeId;
    const currentCard = document.getElementById(`showtime-card-${showtimeId}`);
    if (currentCard) currentCard.classList.add("active");

    selectedSeatId = null;
    const seatingSec = document.getElementById("seating-section");
    seatingSec.classList.remove("d-none");
    seatingSec.classList.add("fade-in-up");
    document.getElementById("seating-title").textContent = `《${movieTitle}》 - ${roomName} 在线座位选择`;

    // 视觉归位并获取最新座位
    document.getElementById("book-ticket-btn").disabled = true;
    document.getElementById("random-book-btn").disabled = true;

    await loadSeats(showtimeId);
}

async function loadSeats(showtimeId) {
    const grid = document.getElementById("seat-grid-container");
    // 【零抖动虚化占位加载】不预先清空容器以免高度塌陷，只虚化半透明以示加载，保持布局绝对稳定
    grid.style.opacity = "0.5";

    try {
        const response = await fetch(`${API_BASE_URL}/cinema/showtimes/${showtimeId}/seats`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (!response.ok) throw new Error("获取座位占用图失败");
        const res = await response.json();

        // 全局缓存
        currentSeats = res.data;

        // 弹性自适应列数：提取所有座位的最大列号，若数据为空则默认为8 (5x8小厅)
        const colsCount = currentSeats.length > 0 ? Math.max(...currentSeats.map(s => s.col_num)) : 8;
        grid.style.gridTemplateColumns = `repeat(${colsCount}, minmax(0, 1fr))`;

        // 数据准备妥当后再行秒级刷新 DOM
        grid.innerHTML = "";
        grid.style.opacity = "1";

        currentSeats.forEach(seat => {
            const item = document.createElement("div");
            item.id = `seat-${seat.uid}`;

            if (seat.status === 1) {
                item.className = "seat-item seat-sold";
                item.innerHTML = `<i class="fa-solid fa-user"></i>`;
                item.title = `${seat.row_num}排${seat.col_num}列 (已售出)`;
            } else {
                item.className = "seat-item seat-available";
                item.textContent = `${seat.row_num}-${seat.col_num}`;
                item.title = `${seat.row_num}排${seat.col_num}列 (可选)`;
                item.onclick = () => selectSeat(seat.uid);
            }
            grid.appendChild(item);
        });

        // 加载完座位后，若本场次未售罄，则解锁随机选座按钮
        const isSoldOut = currentSeats.every(s => s.status === 1);
        document.getElementById("random-book-btn").disabled = isSoldOut;

    } catch (error) {
        grid.style.opacity = "1";
        grid.innerHTML = `<div class="text-danger py-3 text-center">${error.message}</div>`;
    }
}

// 选中单个可用座位 (UI 隔离逻辑)
function selectSeat(seatId) {
    if (!isValidUUID(seatId)) {
        showToast("非法的座位ID格式，安全拦截！", "danger");
        return;
    }

    // 移除之前的选中状态
    if (selectedSeatId) {
        const prev = document.getElementById(`seat-${selectedSeatId}`);
        if (prev && prev.classList.contains("seat-selected")) {
            prev.classList.remove("seat-selected");
            prev.classList.add("seat-available");
        }
    }

    selectedSeatId = seatId;
    const current = document.getElementById(`seat-${seatId}`);
    if (current) {
        current.classList.remove("seat-available");
        current.classList.add("seat-selected");
    }

    document.getElementById("book-ticket-btn").disabled = false;
}

// ==================== 5. 实时静默余票更新与刷新 ====================
async function refreshCurrentSeats() {
    if (!selectedShowtimeId) {
        showToast("请先在场次列表中选择一个排片场次！", "warning");
        return;
    }

    const refreshIcon = document.getElementById("refresh-seats-icon");
    refreshIcon.classList.add("fa-spin"); // 加入动感旋转

    try {
        // 1. 同步刷新座位图
        await loadSeats(selectedShowtimeId);

        // 2. 刷新当前页面的排片列表 (展示最新的余票状态，局部静默刷新)
        await filterShowtimes();

        // 3. 重置大缓冲池以保证下一次“幸运出票”拉取最新数据
        allShowtimes = [];

        showToast("系统座位及余票库存状态同步更新完成！", "success");
    } catch (error) {
        showToast("同步失败: " + error.message, "danger");
    } finally {
        refreshIcon.classList.remove("fa-spin");
    }
}

// ==================== 6. 并发下单抢票 (安全签名防篡改验证) ====================
async function handleBookTicket() {
    if (!selectedShowtimeId || !selectedSeatId) {
        showToast("请先选择排片场次和具体的观影位置！", "warning");
        return;
    }

    if (!isValidUUID(selectedShowtimeId) || !isValidUUID(selectedSeatId)) {
        showToast("检测到非法的业务参数，安全防御机制成功拦截！", "danger");
        return;
    }

    // 提前从内存缓存中获取选中场次排片的电影、放映大厅及座位号，供温暖的 Toast 提示使用！
    const currentShowtime = allShowtimes.find(s => s.uid === selectedShowtimeId);
    const currentSeat = currentSeats.find(s => s.uid === selectedSeatId);
    const movieTitle = currentShowtime ? currentShowtime.movie.title : "热映影片";
    const roomName = currentShowtime ? currentShowtime.room.name : "放映大厅";
    const seatInfo = currentSeat ? `${currentSeat.row_num}排${currentSeat.col_num}列` : "专属席位";

    const btn = document.getElementById("book-ticket-btn");
    const randBtn = document.getElementById("random-book-btn");

    // 【物理 CLS 防抖锁】：动态抓取当前两个按钮在屏幕上的物理实际宽度并硬编码锁定 style.width！
    // 保证在 loading 期间，文案字符长度缩减绝对不会引发按钮拉伸和横向推挤抖动！
    const originalBtnWidth = btn.getBoundingClientRect().width;
    const originalRandWidth = randBtn.getBoundingClientRect().width;
    btn.style.width = `${originalBtnWidth}px`;
    randBtn.style.width = `${originalRandWidth}px`;

    btn.disabled = true;
    randBtn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i>正在签发...`;

    try {
        // 1. 查询后台是否开启了数字安全签名
        const configResp = await fetch(`${API_BASE_URL}/cinema/config?_=${Date.now()}`, { cache: "no-store" });
        const configRes = await configResp.json();
        const isSigCheckEnabled = configRes.data.signature_check;
        const isSigSm3CheckEnabled = configRes.data.signature_sm3_check;
        if (configRes.data.signature_secret) {
            signatureSecret = configRes.data.signature_secret;
        }

        const requestHeaders = {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${currentToken}`
        };

        const bookingBody = {
            showtime_id: selectedShowtimeId,
            seat_id: selectedSeatId
        };

        // 2. 若开启任一校验，前端准备一次性盐与时间戳
        if (isSigCheckEnabled || isSigSm3CheckEnabled) {
            const timestamp = Date.now().toString();
            const nonce = Math.random().toString(36).substring(2, 10) + Math.random().toString(36).substring(2, 10);

            requestHeaders["X-Timestamp"] = timestamp;
            requestHeaders["X-Nonce"] = nonce;

            // 常规 SHA-256 签名挪入 Body 的 signature 字段中
            if (isSigCheckEnabled) {
                const signature = await computeSignature(selectedShowtimeId, selectedSeatId, timestamp, nonce);
                bookingBody.signature = signature;
            }

            // 国密 SM3 签名继续使用 Header 的 X-Signature 字段
            if (isSigSm3CheckEnabled) {
                const payload = `${selectedShowtimeId}${selectedSeatId}${timestamp}${nonce}${signatureSecret}`;
                const signatureSm3 = sm3(payload);
                requestHeaders["X-Signature"] = signatureSm3;
            }
        }

        const response = await fetch(`${API_BASE_URL}/cinema/order`, {
            method: "POST",
            headers: requestHeaders,
            body: JSON.stringify(bookingBody)
        });

        const res = await response.json();

        if (!response.ok) {
            throw new Error(res.error_info || "订票请求未通过，请重新选座");
        }

        showToast(`购票成功！您已成功购买《${movieTitle}》 ${roomName} ${seatInfo} 观影票，请准时入场观影。`, "success");

        // 彻底清空临时选座
        selectedSeatId = null;

        // 【零闪烁局部DOM刷新】不全量重新拉取排片列表，只定向更新当前卡片的余票数据
        const inventoryBadge = document.getElementById(`showtime-inventory-${selectedShowtimeId}`);
        if (inventoryBadge) {
            const parts = inventoryBadge.textContent.replace("席位余量: ", "").split(" / ");
            if (parts.length === 2) {
                const current = parseInt(parts[0]);
                const total = parseInt(parts[1]);
                if (current > 0) {
                    inventoryBadge.textContent = `席位余量: ${current - 1} / ${total}`;
                }
            }
        }
        // 同时同步更新本地内存缓存数据，防止分页或本地检索引起状态不对齐
        const showtimeObj = allShowtimes.find(s => s.uid === selectedShowtimeId);
        if (showtimeObj && showtimeObj.remaining_inventory > 0) {
            showtimeObj.remaining_inventory -= 1;
        }

        await loadSeats(selectedShowtimeId);
        await loadMyTickets();
    } catch (error) {
        showToast(error.message, "danger");
    } finally {
        // 无论成功与否均还原订票按钮文本及状态，并彻底释放物理 CLS 防抖锁
        btn.innerHTML = `<i class="fa-solid fa-ticket me-1"></i>立即购票 (一键出票)`;
        btn.disabled = !selectedSeatId;

        btn.style.width = "";
        randBtn.style.width = "";

        // random-book-btn 的启用状态由 loadSeats 或座位状态动态决定
        if (currentSeats && currentSeats.length > 0) {
            const isSoldOut = currentSeats.every(s => s.status === 1);
            randBtn.disabled = isSoldOut;
        } else {
            randBtn.disabled = true;
        }
    }
}

// ==================== 7. 随机购票与幸运出票 ====================

/**
 * 场次内快速随机选座购票
 */
function handleRandomBookTicket() {
    if (!selectedShowtimeId || currentSeats.length === 0) {
        showToast("请先选择放映场次！", "warning");
        return;
    }

    // 过滤出未售出的空闲座位
    const available = currentSeats.filter(s => s.status === 0);
    if (available.length === 0) {
        showToast("本放映场次已全部售罄，请选择其他场次！", "warning");
        return;
    }

    // 随机抽取一个
    const luckySeat = available[Math.floor(Math.random() * available.length)];

    // UI 高亮选中
    selectSeat(luckySeat.uid);
    showToast(`系统已为您快速锁定了 [${luckySeat.row_num}排${luckySeat.col_num}列] 黄金座位，正在飞速出票中...`, "info");

    // 快速出票下单
    handleBookTicket();
}

/**
 * 终极特性：“幸运选票” 全局随机购票
 * 业务场景：随机挑选未来 30 天内有余票的日期、电影、场次，完成一键极速选座购票！
 */
async function handleLuckyDrawBookTicket() {
    // 实时瞬时拉取：每次点击均拉取最新的系统排片状况，彻底防止高并发下的数据过期与超卖冲突
    showToast("正在快速获取最新影城排片，准备幸运选票...", "info");
    try {
        const response = await fetch(`${API_BASE_URL}/cinema/showtimes?limit=1000`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (!response.ok) throw new Error("获取最新排片场次失败，请确认系统已重置就绪");
        const res = await response.json();
        allShowtimes = res.data.showtimes;
    } catch (error) {
        showToast("出票失败: " + error.message, "danger");
        return;
    }

    // 1. 自动从缓存的全量有效场次中筛选出仍有库存余票的场次
    const luckyShowtimes = allShowtimes.filter(s => s.remaining_inventory > 0);
    if (luckyShowtimes.length === 0) {
        showToast("十分抱歉，影城未来 30 天内的所有排片均已全部售罄！", "danger");
        return;
    }

    // 2. 随机挑选一个幸运场次
    const luckyShowtime = luckyShowtimes[Math.floor(Math.random() * luckyShowtimes.length)];

    showToast(`幸运出票中！已为您选定：《${luckyShowtime.movie.title}》（${luckyShowtime.room.name}），正在挑选座位...`, "info");

    try {
        // 3. 异步获取该幸运场次的全部座位占用数据
        const response = await fetch(`${API_BASE_URL}/cinema/showtimes/${luckyShowtime.uid}/seats`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (!response.ok) throw new Error("获取幸运座位失败");
        const res = await response.json();
        const seats = res.data;

        // 4. 筛选出可购空闲座位
        const available = seats.filter(s => s.status === 0);
        if (available.length === 0) {
            showToast("该幸运场次刚好售罄，正在重新为您寻找...", "warning");
            setTimeout(handleLuckyDrawBookTicket, 1000); // 递归重试
            return;
        }

        // 5. 随机抽取黄金座位
        const luckySeat = available[Math.floor(Math.random() * available.length)];

        // 6. 将联动日期选择器、下拉电影及场次高亮绑定，绝对时区隔离
        const sDateStr = luckyShowtime.start_time.split('T')[0]; // "YYYY-MM-DD"

        // 联动更新检索栏组件
        document.getElementById("filter-date").value = sDateStr;
        document.getElementById("filter-movie").value = luckyShowtime.movie.uid;
        document.getElementById("filter-room").value = "all";
        document.getElementById("filter-time-range").value = "all";
        document.getElementById("filter-search-name").value = "";

        // 分页重置为 1 并发起远程数据带参筛选
        currentPage = 1;
        await filterShowtimes();

        // 加载选中场次及座位图
        selectedShowtimeId = luckyShowtime.uid;
        const seatingSec = document.getElementById("seating-section");
        seatingSec.classList.remove("d-none");
        seatingSec.classList.add("fade-in-up");
        document.getElementById("seating-title").textContent = `《${luckyShowtime.movie.title}》 - ${luckyShowtime.room.name} 在线座位选择`;

        // 渲染座位图状态并绑定选中
        currentSeats = seats;
        const grid = document.getElementById("seat-grid-container");
        // 弹性自适应列数：提取所有座位的最大列号，若数据为空则默认为8 (5x8小厅)
        const colsCount = currentSeats.length > 0 ? Math.max(...currentSeats.map(s => s.col_num)) : 8;
        grid.style.gridTemplateColumns = `repeat(${colsCount}, minmax(0, 1fr))`;
        grid.innerHTML = "";

        currentSeats.forEach(seat => {
            const item = document.createElement("div");
            item.id = `seat-${seat.uid}`;

            if (seat.status === 1) {
                item.className = "seat-item seat-sold";
                item.innerHTML = `<i class="fa-solid fa-user"></i>`;
            } else {
                item.className = "seat-item seat-available";
                item.textContent = `${seat.row_num}-${seat.col_num}`;
                item.onclick = () => selectSeat(seat.uid);
            }
            grid.appendChild(item);
        });

        // 触发 UI 选中
        selectSeat(luckySeat.uid);

        // 滚动视口到座位区，带来震撼顺滑体验
        document.getElementById("seating-section").scrollIntoView({ behavior: 'smooth' });

        // 7. 发起购票下单
        showToast(`幸运出票中！已为您选定《${luckyShowtime.movie.title}》 ${luckyShowtime.room.name} [${luckySeat.row_num}排${luckySeat.col_num}列]，正在出票...`, "success");
        await handleBookTicket();

    } catch (error) {
        showToast("幸运出票出故障了: " + error.message, "danger");
    }
}

// ==================== 8. 管理员专属模块 (系统热控制与归档重置) ====================

// 获取系统参数配置
async function loadCinemaConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/cinema/config?_=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) throw new Error("拉取系统配置参数失败");
        const res = await response.json();
        const conf = res.data;

        // 设置 Switch 及 select 状态
        document.getElementById("config-pool").value = conf.pool_mode;

        const poolBadge = document.getElementById("pool-badge");
        if (conf.pool_mode === "queue") {
            poolBadge.textContent = "高并发长连接池 (QueuePool)";
            poolBadge.className = "badge rounded-pill badge-active";
        } else {
            poolBadge.textContent = "传统售票通道 (NullPool)";
            poolBadge.className = "badge rounded-pill badge-inactive";
        }

        // 设置 Radio 锁状态
        document.getElementById(`lock-${conf.lock_mode}`).checked = true;

        // 设置 Switch 慢查询和签名状态
        document.getElementById("config-slow-query").checked = conf.slow_query;
        document.getElementById("config-signature").checked = conf.signature_check;
        document.getElementById("config-signature-sm3").checked = conf.signature_sm3_check;
        document.getElementById("config-sm4-password").checked = conf.sm4_password_encrypt;
        if (conf.signature_secret) {
            signatureSecret = conf.signature_secret;
        }
        if (conf.sm4_key) {
            sm4Key = conf.sm4_key;
        }
    } catch (error) {
        showToast(error.message, "danger");
    }

}

// 保存热配置修改 (仅限管理员，同步覆盖 .env)
async function handleSaveConfig(event) {
    event.preventDefault();
    if (currentRole !== "admin") {
        showToast("越权警告：仅系统值班经理允许调整系统维护参数！", "danger");
        return;
    }

    const pool = document.getElementById("config-pool").value;
    const lock = document.querySelector('input[name="lockMode"]:checked').value;
    const slowQuery = document.getElementById("config-slow-query").checked;
    const signature = document.getElementById("config-signature").checked;
    const signatureSm3 = document.getElementById("config-signature-sm3").checked;
    const sm4Password = document.getElementById("config-sm4-password").checked;

    try {
        const response = await fetch(`${API_BASE_URL}/cinema/config`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${currentToken}`
            },
            body: JSON.stringify({
                pool_mode: pool,
                lock_mode: lock,
                slow_query: slowQuery,
                signature_check: signature,
                signature_sm3_check: signatureSm3,
                sm4_password_encrypt: sm4Password
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error_info || "参数保存失败");
        }

        showToast("系统维护配置已成功生效，并已同步覆写本地 .env 持久化配置文件！", "success");
        await loadCinemaConfig();
    } catch (error) {
        showToast(error.message, "danger");
    }
}

// 唤醒日结归档一键重置二次确认弹窗
function handleResetDatabase() {
    if (currentRole !== "admin") {
        showToast("越权警告：您非值班经理身份，不允许重置系统营业数据！", "danger");
        return;
    }
    const myModal = new bootstrap.Modal(document.getElementById("confirmModal"));
    myModal.show();
}

// 物理执行一键清零还原重建
async function executeReset() {
    const modalEl = document.getElementById("confirmModal");
    const modal = bootstrap.Modal.getInstance(modalEl);
    modal.hide();

    try {
        const response = await fetch(`${API_BASE_URL}/cinema/reset`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${currentToken}`
            }
        });

        const res = await response.json();
        if (!response.ok) {
            throw new Error(res.error_info || "数据归档初始化失败");
        }

        showToast("影城系统数据重置归档成功！营业出票数据已清空，30天排片已重新就绪！", "success");

        // 彻底重设选中座位和场次状态
        selectedShowtimeId = null;
        selectedSeatId = null;
        allShowtimes = [];
        currentSeats = [];
        currentPage = 1;
        totalCount = 0;
        document.getElementById("seating-section").classList.add("d-none");

        await loadShowtimes();
    } catch (error) {
        showToast(error.message, "danger");
    }
}

function toggleProfile(forceView = null) {
    if (currentRole !== "user") return;
    const bookingSection = document.getElementById("cinema-booking-section");
    const profileSection = document.getElementById("profile-section");
    const profileBtn = document.getElementById("profile-btn");

    // 如果指定了强制视图状态
    let showProfile = false;
    if (forceView === "profile") {
        showProfile = true;
    } else if (forceView === "booking") {
        showProfile = false;
    } else {
        // 否则根据 d-none 动态切换
        showProfile = profileSection.classList.contains("d-none");
    }

    if (showProfile) {
        bookingSection.classList.add("d-none");
        profileSection.classList.remove("d-none");
        profileBtn.innerHTML = `<i class="fa-solid fa-chevron-left me-1"></i>返回购票中心`;
        profileBtn.className = "btn btn-outline-warning btn-sm me-2";
        sessionStorage.setItem("current_view", "profile");
        renderUserProfileCard();
        // 进入个人中心，冷启动加载订单
        loadMyTickets(false);
    } else {
        profileSection.classList.add("d-none");
        bookingSection.classList.remove("d-none");
        profileBtn.innerHTML = `<i class="fa-solid fa-user me-1"></i>个人中心`;
        profileBtn.className = "btn btn-outline-info btn-sm me-2";
        sessionStorage.setItem("current_view", "booking");
    }
}

// 已购选票滚动加载状态重置
function resetMyTicketsPagination() {
    myTicketsPage = 1;
    myTicketsHasMore = true;
    isMyTicketsLoading = false;
    loadedTickets = [];
    if (ticketObserver) {
        ticketObserver.disconnect();
        ticketObserver = null;
    }

    const activeContainer = document.getElementById("active-tickets-container");
    const refundedContainer = document.getElementById("refunded-tickets-container");
    const refundedSec = document.getElementById("refunded-tickets-section");
    const countBadge = document.getElementById("ticket-count-badge");
    const triggerEl = document.getElementById("tickets-loading-trigger");

    if (activeContainer) activeContainer.innerHTML = `<div class="col-12 text-center text-secondary py-3 small">暂无有效购票记录，快去挑选一场心动影片吧</div>`;
    if (refundedContainer) refundedContainer.innerHTML = "";
    if (refundedSec) refundedSec.classList.add("d-none");
    if (countBadge) countBadge.textContent = "0 张";
    if (triggerEl) triggerEl.classList.add("d-none");
}

async function renderUserProfileCard() {
    // 【刷新保持冷自愈】：若缓存为空但 Token 存在，说明是用户刷新了个人中心页面，自动触发 API 获取个人信息！
    if (!currentUserProfile) {
        if (currentToken) {
            await fetchUserProfile();
        }
        return;
    }

    const avatarImg = document.getElementById("profile-avatar");
    if (currentUserProfile.avatar) {
        avatarImg.src = currentUserProfile.avatar.startsWith("data:")
            ? currentUserProfile.avatar
            : `data:image/png;base64,${currentUserProfile.avatar}`;
    } else {
        avatarImg.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%23334155'/><path d='M25 80c0-15 10-20 25-20s25 5 25 20' fill='%2364748b'/><circle cx='50' cy='35' r='15' fill='%2364748b'/></svg>";
    }

    document.getElementById("profile-fullname").textContent = currentUserProfile.full_name || "-";
    document.getElementById("profile-email").textContent = currentUserProfile.email || "-";

    let genderText = "未知";
    if (currentUserProfile.gender === 0) genderText = "女";
    else if (currentUserProfile.gender === 1) genderText = "男";
    document.getElementById("profile-gender").textContent = genderText;

    document.getElementById("profile-birthday").textContent = currentUserProfile.birthday || "未填写";

    // 【顶栏尊贵会员名牌用户名物理回填】：将当前用户的真实姓名更新至右上角身份牌，杜绝硬编码！
    const userInfoText = document.getElementById("user-info-text");
    if (userInfoText) {
        if (currentUserProfile.email === "admin@cinema.com") {
            userInfoText.textContent = `当前身份: 影城值班经理 (${currentUserProfile.full_name || '管理员'})`;
        } else {
            userInfoText.textContent = `当前身份: 影城尊贵会员 (${currentUserProfile.full_name || '会员观众'})`;
        }
    }
}

// 滚动分页加载购票记录
async function loadMyTickets(isLoadMore = false) {
    if (!currentToken || currentRole !== "user") {
        return;
    }

    if (!isLoadMore) {
        resetMyTicketsPagination();
    }

    if (!myTicketsHasMore || isMyTicketsLoading) {
        return;
    }

    isMyTicketsLoading = true;
    const triggerEl = document.getElementById("tickets-loading-trigger");
    if (triggerEl) {
        triggerEl.classList.remove("d-none");
    }

    const offset = (myTicketsPage - 1) * myTicketsLimit;

    try {
        const response = await fetch(`${API_BASE_URL}/cinema/orders?limit=${myTicketsLimit}&offset=${offset}`, {
            headers: {
                "Authorization": `Bearer ${currentToken}`
            }
        });

        const res = await response.json();
        if (!response.ok) {
            throw new Error(res.error_info || "获取购票记录失败");
        }

        const newTickets = res.data || [];
        if (newTickets.length < myTicketsLimit) {
            myTicketsHasMore = false;
        }

        loadedTickets = loadedTickets.concat(newTickets);
        myTicketsPage++;

        renderMyTickets();

    } catch (error) {
        console.error("加载已购选票异常:", error);
        showToast(error.message, "danger");
    } finally {
        isMyTicketsLoading = false;
        if (triggerEl) {
            triggerEl.classList.add("d-none");
        }
        setupTicketScrollObserver();
    }
}

// 挂载 IntersectionObserver 滚动监听
function setupTicketScrollObserver() {
    if (ticketObserver) {
        ticketObserver.disconnect();
        ticketObserver = null;
    }

    if (!myTicketsHasMore) return;

    const triggerEl = document.getElementById("tickets-loading-trigger");
    if (!triggerEl) return;

    triggerEl.classList.remove("d-none");

    ticketObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadMyTickets(true);
        }
    }, {
        root: null,
        rootMargin: "100px",
        threshold: 0.1
    });

    ticketObserver.observe(triggerEl);
}

// 物理二分归档渲染订单列表
function renderMyTickets() {
    const activeContainer = document.getElementById("active-tickets-container");
    const refundedContainer = document.getElementById("refunded-tickets-container");
    const refundedSec = document.getElementById("refunded-tickets-section");
    const countBadge = document.getElementById("ticket-count-badge");

    if (!activeContainer || !refundedContainer || !refundedSec || !countBadge) return;

    const activeTickets = loadedTickets.filter(t => t.status === 1);
    const refundedTickets = loadedTickets.filter(t => t.status === 2);

    countBadge.textContent = `${activeTickets.length} 张`;

    if (activeTickets.length === 0) {
        activeContainer.innerHTML = `<div class="col-12 text-center text-secondary py-3 small">暂无有效购票记录，快去挑选一场心动影片吧</div>`;
    } else {
        activeContainer.innerHTML = buildTicketsHtmlGroup(activeTickets);
    }

    if (refundedTickets.length === 0) {
        refundedSec.classList.add("d-none");
        refundedContainer.innerHTML = "";
    } else {
        refundedSec.classList.remove("d-none");
        refundedContainer.innerHTML = buildTicketsHtmlList(refundedTickets);
    }
}

function buildTicketsHtmlGroup(tickets) {
    const groups = {};
    tickets.forEach(ticket => {
        const dateStr = ticket.start_time.split('T')[0];
        if (!groups[dateStr]) groups[dateStr] = [];
        groups[dateStr].push(ticket);
    });

    const sortedDates = Object.keys(groups).sort((a, b) => b.localeCompare(a));
    let html = "";
    const now = new Date();

    sortedDates.forEach(dateStr => {
        const ticketsInDate = groups[dateStr];
        const d = new Date(dateStr);
        const weekDays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
        const formattedDate = `${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日 ${weekDays[d.getDay()]}`;

        html += `
            <div class="date-group mb-3 border border-secondary border-opacity-35 rounded p-3 bg-dark bg-opacity-20">
                <div class="d-flex align-items-center mb-2 pb-2 border-bottom border-secondary border-opacity-25">
                    <i class="fa-solid fa-calendar-day text-info me-2"></i>
                    <span class="fw-bold text-white" style="font-size: 14px;">${formattedDate}</span>
                    <span class="badge bg-secondary ms-2" style="font-size: 10px;">${ticketsInDate.length}张</span>
                </div>
                <div class="d-flex flex-column gap-2">
        `;

        ticketsInDate.forEach(ticket => {
            const timePart = ticket.start_time.split('T')[1];
            const startTimeStr = timePart ? timePart.substring(0, 5) : "00:00";

            let endTimeStr = "";
            if (timePart) {
                const [h, m] = startTimeStr.split(':').map(Number);
                const totalMins = h * 60 + m + ticket.movie_duration;
                const endH = Math.floor(totalMins / 60) % 24;
                const endM = totalMins % 60;
                endTimeStr = ` - ${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
            }

            const showDateTime = new Date(ticket.start_time);
            const isExpired = showDateTime < now;

            let badgeHtml = "";
            let itemClass = "list-group-item bg-dark bg-opacity-40 text-white d-flex align-items-center justify-content-between p-2 rounded flex-wrap gap-2";
            let actionHtml = "";

            if (isExpired) {
                badgeHtml = `<span class="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-50" style="font-size: 10px;"><i class="fa-solid fa-clock-rotate-left me-1"></i>已放映</span>`;
                itemClass += " opacity-40";
                actionHtml = `<span class="text-secondary small" style="font-size: 11px;">不可退票</span>`;
            } else {
                badgeHtml = `<span class="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50" style="font-size: 10px;"><i class="fa-solid fa-circle-check me-1"></i>支付成功</span>`;
                actionHtml = `<button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="handleRefund('${ticket.uid}', '${ticket.showtime_id}')" style="font-size: 11px; height: 22px; line-height: 20px;">退票</button>`;
            }

            html += `
                <div class="${itemClass}" style="border: 1px solid rgba(255,255,255,0.05);">
                    <div class="d-flex align-items-center gap-2">
                        ${badgeHtml}
                        <div class="fw-bold text-white text-truncate" style="max-width: 140px; font-size: 13px;" title="${ticket.movie_title}">
                            ${ticket.movie_title}
                        </div>
                        <span class="text-secondary small" style="font-size: 10px;">${ticket.movie_duration}m</span>
                    </div>
                    
                    <div class="d-flex align-items-center gap-3 text-secondary small" style="font-size: 11px;">
                        <div><i class="fa-solid fa-location-dot me-1 text-info"></i>${ticket.room_name}</div>
                        <div><i class="fa-solid fa-chair me-1 text-warning"></i>${ticket.row_num}排${ticket.col_num}座</div>
                        <div><i class="fa-solid fa-clock me-1 text-primary"></i>${startTimeStr}${endTimeStr}</div>
                    </div>
                    
                    <div class="d-flex align-items-center gap-3">
                        <span class="fw-bold text-warning small" style="font-size: 12px;">¥${parseFloat(ticket.amount).toFixed(2)}</span>
                        ${actionHtml}
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    });
    return html;
}

function buildTicketsHtmlList(tickets) {
    let html = "";
    tickets.forEach(ticket => {
        const sDateStr = ticket.start_time.split('T')[0];
        const timePart = ticket.start_time.split('T')[1];
        const startTimeStr = timePart ? timePart.substring(0, 5) : "00:00";

        const badgeHtml = `<span class="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-50" style="font-size: 10px;"><i class="fa-solid fa-arrow-rotate-left me-1"></i>已退票</span>`;
        const itemClass = "list-group-item bg-dark bg-opacity-40 text-white d-flex align-items-center justify-content-between p-2 rounded flex-wrap gap-2 opacity-50";
        const actionHtml = `<span class="text-secondary small" style="font-size: 11px;">已退订退款</span>`;

        html += `
            <div class="${itemClass}" style="border: 1px solid rgba(255,255,255,0.05);">
                <div class="d-flex align-items-center gap-2">
                    ${badgeHtml}
                    <div class="fw-bold text-white text-truncate" style="max-width: 140px; font-size: 13px;" title="${ticket.movie_title}">
                        ${ticket.movie_title}
                    </div>
                    <span class="text-secondary small" style="font-size: 10px;">${ticket.movie_duration}m</span>
                </div>
                
                <div class="d-flex align-items-center gap-3 text-secondary small" style="font-size: 11px;">
                    <div><i class="fa-solid fa-location-dot me-1 text-info"></i>${ticket.room_name}</div>
                    <div><i class="fa-solid fa-chair me-1 text-warning"></i>${ticket.row_num}排${ticket.col_num}座</div>
                    <div><i class="fa-solid fa-clock me-1 text-primary"></i>${sDateStr} ${startTimeStr}</div>
                </div>
                
                <div class="d-flex align-items-center gap-3">
                    <span class="fw-bold text-warning small" style="font-size: 12px;">¥${parseFloat(ticket.amount).toFixed(2)}</span>
                    ${actionHtml}
                </div>
            </div>
        `;
    });
    return html;
}

async function handleRefund(orderId, showtimeId) {
    const confirmBtn = document.getElementById("execute-refund-btn");
    const refundModalEl = document.getElementById("refundConfirmModal");
    const refundModal = bootstrap.Modal.getOrCreateInstance(refundModalEl);

    // 每次打开弹窗时，确保按钮处于可点击状态，且文字复原
    confirmBtn.disabled = false;
    confirmBtn.textContent = "确认退票 (秒级退款)";

    confirmBtn.onclick = async () => {
        confirmBtn.disabled = true;
        confirmBtn.textContent = "正在退票...";
        refundModal.hide();
        await executeRefundRequest(orderId, showtimeId);
        // 恢复按钮状态以供下次打开时使用
        confirmBtn.disabled = false;
        confirmBtn.textContent = "确认退票 (秒级退款)";
    };

    refundModal.show();
}

async function executeRefundRequest(orderId, showtimeId) {
    const url = `${API_BASE_URL}/cinema/order/${orderId}/refund`;
    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${currentToken}`
            }
        });

        let res;
        try {
            res = await response.json();
        } catch (e) {
            throw new Error(`解析服务器JSON失败 (HTTP ${response.status}) \nURL: ${url}`);
        }


        if (!response.ok) {
            const errMsg = `${res.error_info || res.message || '退票失败'} (HTTP ${response.status}) \nURL: ${url}`;
            throw new Error(errMsg);
        }

        // 提前获取退票的电影名字和座位号，拼装 Toast 提示。
        const refundObj = loadedTickets.find(t => t.uid === orderId);
        let movieTitle = "影片";
        let seatInfo = "座位";
        if (refundObj) {
            movieTitle = refundObj.movie_title;
            seatInfo = `${refundObj.row_num}排${refundObj.col_num}列`;
        }

        showToast(`退票成功！已为您成功退订《${movieTitle}》 ${seatInfo} 观影票，票款将原路退回到您的账户。`, "success");

        // 【物理零损局部状态同步】：直接在本地 loadedTickets 里更新对应订单的状态！
        // 绝对不需要重新网络拉取，保持完美滚动加载的分页高度！
        if (refundObj) {
            refundObj.status = 2;
        }

        // 同步影厅余票
        if (showtimeId && showtimeId !== "undefined") {
            const inventoryBadge = document.getElementById(`showtime-inventory-${showtimeId}`);
            if (inventoryBadge) {
                const parts = inventoryBadge.textContent.replace("席位余量: ", "").split(" / ");
                if (parts.length === 2) {
                    const current = parseInt(parts[0]);
                    const total = parseInt(parts[1]);
                    if (current < total) {
                        inventoryBadge.textContent = `席位余量: ${current + 1} / ${total}`;
                    }
                }
            }

            const showtimeObj = allShowtimes.find(s => s.uid === showtimeId);
            if (showtimeObj && showtimeObj.remaining_inventory < 40) {
                showtimeObj.remaining_inventory += 1;
            }

            if (selectedShowtimeId === showtimeId) {
                await loadSeats(selectedShowtimeId);
            }
        }

        // 瞬间物理重绘已购列表，0 毫秒完美响应！
        renderMyTickets();
    } catch (error) {
        showToast(error.message, "danger");
    }
}

if (typeof window !== "undefined") {
    window.handleLogin = handleLogin;
    window.handleLogout = handleLogout;
    window.changePage = changePage;
    window.selectShowtime = selectShowtime;
    window.selectSeat = selectSeat;
    window.refreshCurrentSeats = refreshCurrentSeats;
    window.handleBookTicket = handleBookTicket;
    window.handleRandomBookTicket = handleRandomBookTicket;
    window.handleLuckyDrawBookTicket = handleLuckyDrawBookTicket;
    window.loadCinemaConfig = loadCinemaConfig;
    window.handleSaveConfig = handleSaveConfig;
    window.handleResetDatabase = handleResetDatabase;
    window.executeReset = executeReset;
    window.loadMyTickets = loadMyTickets;
    window.toggleProfile = toggleProfile;
    window.renderUserProfileCard = renderUserProfileCard;
    window.handleRefund = handleRefund;
}

// 登录头像眼睛瞳孔平滑跟随鼠标运动
if (typeof document !== "undefined") {
    document.addEventListener("mousemove", (event) => {
        const avatar = document.querySelector(".login-avatar");
        if (!avatar) return;

        // 获取头像在当前视口中的实际物理几何中心
        const rect = avatar.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        // 鼠标相对于头像中心的相对坐标
        const deltaX = event.clientX - centerX;
        const deltaY = event.clientY - centerY;
        const angle = Math.atan2(deltaY, deltaX);

        // 限制瞳孔移动的物理最大半径为 1.8px (精细幅度，既传神又不穿帮)
        const maxOffset = 1.8;
        const offsetX = Math.cos(angle) * maxOffset;
        const offsetY = Math.sin(angle) * maxOffset;

        const pupilLeft = document.getElementById("avatar-pupil-left");
        const pupilRight = document.getElementById("avatar-pupil-right");

        if (pupilLeft) {
            pupilLeft.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
        }
        if (pupilRight) {
            pupilRight.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
        }
    });
}


