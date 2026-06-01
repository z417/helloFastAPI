#!/usr/bin/env bun
/**
 * Bun 原生超高性能静态 Web 服务器
 * 零第三方依赖，彻底规避传统 Node 库在现代运行时下的 readonly 异常
 */
const server = Bun.serve({
  port: 8080,
  fetch(req) {
    const url = new URL(req.url);
    let path = url.pathname;
    
    // 默认路由映射
    if (path === "/" || path === "") {
      path = "/index.html";
    }
    
    const file = Bun.file(`.${path}`);
    return new Response(file);
  },
});

console.log(`[Bun Serve] 极速静态服务器已正常拉起：http://127.0.0.1:${server.port}`);
