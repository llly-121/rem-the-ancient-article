/* 离线缓存：装到主屏后没网也能刷。
 *
 * 为什么需要它：这个 App 的全部内容就是 index.html + data.js（1.2 MB）。
 * 没有 Service Worker 的话，地铁里、飞行模式下打开就是白屏——
 * 而「通勤时背两个词」恰恰是这类工具最典型的使用场景。
 *
 * 策略是 stale-while-revalidate（先给缓存，后台悄悄更新）：
 *   命中缓存 → 立刻返回，同时发一次网络请求刷新缓存
 *   没命中   → 走网络，成功则写缓存
 *   断网且没缓存 → 返回缓存里的 index.html，至少不是浏览器报错页
 */

const CACHE = "guwen-v6";   // 数据版本变了就改这里，旧缓存会在 activate 时清掉

const ASSETS = [
  "./index.html",
  "./data.js",
  "./manifest.webmanifest",
  "./icons/icon-180.png",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // 逐个加而不是 addAll：任何一个 404 都不会让整轮安装失败
    await Promise.all(ASSETS.map(async (url) => {
      try {
        const res = await fetch(url, { cache: "reload" });
        // 只存正常响应。站点带 sharecode 校验，异常时返回的是 403 的 HTML 页，
        // 万一被存进去，App 就永久白屏了 —— 这是最需要防的一种失败。
        if (res.ok) await cache.put(url, res);
      } catch (e) {
        /* 单个资源失败不影响其余 */
      }
    }));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    // ignoreSearch：请求可能带 ?sharecode=xxx，缓存键里没有，不能因此判为未命中
    const hit = await cache.match(req, { ignoreSearch: true });

    const network = fetch(req)
      .then((res) => {
        if (res.ok) cache.put(req, res.clone());
        return res;
      })
      .catch(() => null);

    if (hit) return hit;                  // 先给缓存，网络在后台更新
    const fresh = await network;
    if (fresh) return fresh;

    // 彻底断网且没缓存：退回首页，别让用户看到浏览器的报错页
    return (await cache.match("./index.html", { ignoreSearch: true })) || Response.error();
  })());
});
