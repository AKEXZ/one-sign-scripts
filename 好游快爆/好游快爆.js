/**
 * 好游快爆每日任务
 * 三大任务系统：爆友等级任务、爆米花任务（玉米庄园）、游戏签到任务
 * 抓包：好游快爆 app → 个人中心/任务页面 → 抓包获取 scookie
 * 变量：ONESIGN_HYKB_COOKIE（scookie 值，多账号用 @ 分隔）
 *
 * cron: 0 8,12,18 * * *
 * new Env('好游快爆');
 */

const https = require("https");
const zlib = require("zlib");
const crypto = require("crypto");
const SCRIPT_NAME = "好游快爆";

const UA_WEBVIEW = "Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/151.0.7922.170 Mobile Safari/537.36Androidkb/1.5.8.107(android;RMX5062;15;1280x2612;);@4399_sykb_android_activity@";
const UA_APP = "Androidkb/1.5.8.107(android;RMX5062;15;1280x2612;)";
const DEVICE = "kbFB304A0B340B5324E02D42A0F8D049BB";

// ==================== HTTP 工具 ====================

function decompressResponse(buf, encoding) {
    return new Promise((resolve) => {
        if (encoding === "gzip") {
            zlib.gunzip(buf, (err, decoded) => resolve(err ? buf.toString() : decoded.toString()));
        } else if (encoding === "deflate") {
            zlib.inflate(buf, (err, decoded) => resolve(err ? buf.toString() : decoded.toString()));
        } else if (encoding === "br") {
            zlib.brotliDecompress(buf, (err, decoded) => resolve(err ? buf.toString() : decoded.toString()));
        } else {
            resolve(buf.toString());
        }
    });
}

function httpGet(url, headers = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const options = {
            hostname: urlObj.hostname,
            port: 443,
            path: urlObj.pathname + urlObj.search,
            headers: {
                "User-Agent": UA_WEBVIEW,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "com.xmcy.hykb",
                ...headers
            }
        };
        https.get(options, (res) => {
            const chunks = [];
            res.on("data", (chunk) => chunks.push(chunk));
            res.on("end", async () => {
                const buf = Buffer.concat(chunks);
                resolve(await decompressResponse(buf, res.headers["content-encoding"]));
            });
        }).on("error", reject);
    });
}

function httpPost(url, body, headers = {}) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const options = {
            hostname: urlObj.hostname,
            port: 443,
            path: urlObj.pathname + urlObj.search,
            method: "POST",
            headers: {
                "User-Agent": UA_WEBVIEW,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate, br",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Content-Length": Buffer.byteLength(body),
                ...headers
            }
        };
        const req = https.request(options, (res) => {
            const chunks = [];
            res.on("data", (chunk) => chunks.push(chunk));
            res.on("end", async () => {
                const buf = Buffer.concat(chunks);
                resolve(await decompressResponse(buf, res.headers["content-encoding"]));
            });
        });
        req.on("error", reject);
        req.write(body);
        req.end();
    });
}

// ==================== 配置读取 ====================

const { getConfig } = (() => {
    const fs = require("fs");
    const path = require("path");
    function getConfig(key, envName) {
        if (process.env[envName]) return process.env[envName];
        try {
            const configPath = path.join(__dirname, "..", "..", "config.yml");
            if (fs.existsSync(configPath)) {
                const yaml = require("js-yaml");
                const config = yaml.load(fs.readFileSync(configPath, "utf8"));
                const keys = key.split(".");
                let val = config;
                for (const k of keys) {
                    if (val && typeof val === "object") val = val[k];
                    else return undefined;
                }
                return val;
            }
        } catch (e) {}
        return undefined;
    }
    return { getConfig };
})();

function rand() {
    return "0." + (Math.round(Math.random() * 8999999999999999) + 1000000000000000);
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

// ==================== 爆友等级任务系统 (baoyoudiantang2026) ====================

const BAOYOU_URL = "https://huodong3.3839.com/n/hykb/baoyoudiantang2026/ajax.php";
const BAOYOU_REFERER = "https://huodong3.3839.com/n/hykb/baoyoudiantang2026/index.php?imm=0";

async function baoyouAjax(ac, scookie, extra = {}) {
    const params = new URLSearchParams();
    params.append("ac", ac);
    params.append("r", rand());
    params.append("scookie", scookie);
    params.append("device", DEVICE);
    for (const [key, value] of Object.entries(extra)) {
        params.append(key, value);
    }
    const body = params.toString();
    const res = await httpPost(BAOYOU_URL, body, { Referer: BAOYOU_REFERER });
    try {
        return JSON.parse(res);
    } catch (e) {
        return null;
    }
}

async function baoyouLogin(scookie, gzuids) {
    const extra = {};
    if (gzuids) extra.gzuids = gzuids;
    return await baoyouAjax("login", scookie, extra);
}

async function baoyouLoadRenWu(scookie, pid) {
    return await baoyouAjax("loadRenWu", scookie, { pid: pid.toString() });
}

async function baoyouLingQuRenWu(scookie, id, type = 0) {
    return await baoyouAjax("lingQuRenWu", scookie, { id: id.toString(), type: type.toString() });
}

// 已知的每日任务 ID 列表（从 HTML 分析）
const DAILY_TASK_IDS = [1, 2, 6, 7, 8, 71, 121];
// 已知的成长/火花任务 ID
const GROWTH_TASK_IDS = [10, 11, 13, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27, 28, 62, 72, 73, 74, 75, 76];
// 任务名称映射
const TASK_NAME_MAP = {
    1: "签到", 2: "每日浇灌", 6: "发掘小游戏", 7: "玩点新游戏",
    8: "阅读游戏情报", 10: "火花任务10", 11: "火花任务11", 13: "火花任务13",
    15: "火花任务15", 16: "火花任务16", 20: "成长任务20", 21: "成长任务21",
    22: "成长任务22", 23: "成长任务23", 24: "成长任务24", 25: "成长任务25",
    26: "成长任务26", 27: "成长任务27", 28: "成长任务28", 62: "成长任务62",
    71: "群聊有我", 72: "成长任务72", 73: "成长任务73", 74: "成长任务74",
    75: "成长任务75", 76: "成长任务76", 121: "讨论点赞"
};

// 尝试领取指定任务
async function tryClaimTask(scookie, taskId, taskName) {
    const res = await baoyouLingQuRenWu(scookie, taskId);
    if (!res) return;
    if (res.key === "ok") {
        const byf = res.this_byf || 0;
        console.log(`    ${taskName || "任务" + taskId}: 领取成功 +${byf}爆友分`);
    }
    // 静默处理其他状态（未完成、已领取等）
}

// 执行爆友等级任务
async function runBaoyouTasks(scookie) {
    console.log("【爆友等级任务】");

    // 登录
    const loginData = await baoyouLogin(scookie);
    if (!loginData || loginData.key !== "ok") {
        console.log(`  登录失败: ${JSON.stringify(loginData)?.substring(0, 100)}`);
        return;
    }
    const config = loginData.config || {};
    console.log(`  用户: ${config.name || "未知"} 等级: Lv${config.level || 0} 爆友分: ${config.byf || 0}`);
    console.log(`  今日任务: ${config.daily_renwu_success || 0}/${config.daily_renwu_total || 0} 已完成, 获得爆友分: ${config.daily_byf_earned || 0}/${config.daily_byf_total || 0}`);

    // 先尝试签到（任务1）
    await tryClaimTask(scookie, 1, "签到");
    await sleep(300);

    // 遍历所有任务分类 (pid 1-8)，领取已完成的任务
    let totalClaimed = 0;
    const taskNames = {
        1: "每日任务", 2: "进阶任务", 3: "互动任务", 4: "特殊任务",
        5: "限定任务", 6: "活动任务", 7: "成长任务", 8: "其他任务"
    };

    for (let pid = 1; pid <= 8; pid++) {
        await sleep(300);
        const data = await baoyouLoadRenWu(scookie, pid);
        if (!data || data.key !== "ok") continue;

        const taskData = data.data || {};
        const readyIds = taskData.renwu_dacheng || [];
        const claimedIds = taskData.renwu_yiling || [];
        const catName = taskNames[pid] || `分类${pid}`;

        if (claimedIds.length > 0) {
            console.log(`  ${catName}: ${claimedIds.length}个任务已领取`);
        }

        if (readyIds.length > 0) {
            console.log(`  ${catName}: ${readyIds.length}个任务待领取`);
            for (const taskId of readyIds) {
                await sleep(200);
                const claimRes = await baoyouLingQuRenWu(scookie, taskId);
                if (claimRes && claimRes.key === "ok") {
                    totalClaimed++;
                    const byf = claimRes.this_byf || 0;
                    console.log(`    任务${taskId}: 领取成功 +${byf}爆友分`);
                } else if (claimRes?.info) {
                    console.log(`    任务${taskId}: ${claimRes.info}`);
                }
            }
        }
    }

    // 尝试领取所有已知任务 ID（包括未在 renwu_dacheng 中出现的）
    for (const taskId of [...DAILY_TASK_IDS, ...GROWTH_TASK_IDS]) {
        await sleep(200);
        await tryClaimTask(scookie, taskId, TASK_NAME_MAP[taskId]);
    }

    console.log(`  爆友任务完成: 本次领取${totalClaimed}个`);
}

// ==================== 游戏签到任务系统 (qdjh) ====================

const QDJH_AJAX_URL = "https://huodong3.3839.com/n/hykb/qdjh/ajax.php";
const QDJH_REFERER = "https://huodong3.3839.com/n/hykb/qdjh/index.php?imm=0";

async function qdjhAjax(ac, scookie, extra = {}) {
    const params = new URLSearchParams();
    params.append("ac", ac);
    params.append("r", rand());
    params.append("scookie", scookie);
    params.append("device", DEVICE);
    for (const [key, value] of Object.entries(extra)) {
        params.append(key, value);
    }
    const body = params.toString();
    const res = await httpPost(QDJH_AJAX_URL, body, { Referer: QDJH_REFERER });
    try {
        return JSON.parse(res);
    } catch (e) {
        return null;
    }
}

// 获取游戏签到列表（从 qdjh 页面 HTML 解析）
async function getGameSignIds(scookie) {
    const items = [];
    const seen = new Set();
    try {
        // 先登录 qdjh 系统
        await qdjhAjax("login", scookie);
        await sleep(300);

        // 获取 qdjh 页面 HTML，提取所有游戏签到活动
        const url = "https://huodong3.3839.com/n/hykb/qdjh/index.php?imm=0";
        const html = await httpGet(url, {
            "Cookie": `cornfarm_iback_v5=ok; cornfarm_moren_btn_v1=ok; cornfarm_iback_mark_v2=ok`
        });

        // 解析 ACT.GoUrl('...hd_id=XXXX','标题'); ACT.setCookie(YYYY) 模式
        const regex = /ACT\.GoUrl\(['"]([^'"]*hd_id=(\d+)[^'"]*)['"]\s*,\s*['"]([^'"]+)['"]\)\s*;\s*ACT\.setCookie\((\d+)\)/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            const hdId = match[2];
            const title = match[3];
            const gameId = match[4];
            if (!seen.has(gameId)) {
                seen.add(gameId);
                items.push({ id: gameId, hdId, title });
            }
        }

        // 如果 HTML 解析没结果，回退到 getYouWant
        if (items.length === 0) {
            const data = await qdjhAjax("getYouWant", scookie);
            if (data && data.key === "ok" && data.list) {
                for (const gameId of data.list) {
                    items.push({ id: gameId.toString(), title: `游戏${gameId}` });
                }
            }
        }
    } catch (err) {
        console.log(`  获取游戏签到列表失败: ${err.message}`);
    }
    return items;
}

// 游戏签到（使用 qdjh/ac=setCookie）
async function gameSignIn(scookie, items) {
    let successCount = 0;
    for (const item of items) {
        try {
            const signRes = await qdjhAjax("setCookie", scookie, { id: item.id });
            if (signRes && signRes.key === "ok") {
                successCount++;
                console.log(`  ${item.title}: 签到成功`);
            } else {
                console.log(`  ${item.title}: ${signRes?.info || signRes?.key || "请求失败"}`);
            }
        } catch (err) {
            console.log(`  ${item.title}: ${err.message}`);
        }
        await sleep(300);
    }
    console.log(`游戏签到完成: ${successCount}个`);
}

// ==================== 爆米花任务系统 (cornfarm) ====================

const CORNFARM_URL = "https://huodong3.3839.com/n/hykb/cornfarm/ajax.php";
const CORNFARM_REFERER = "https://huodong3.3839.com/n/hykb/cornfarm/index.php?imm=0";

function dealVisitSign(str) {
    return crypto.createHash("md5").update(str).digest("hex").substring(0, 10);
}

async function cornfarmAjax(ac, scookie, tokens, extra = {}) {
    const now = Date.now();
    const tokenTime = now.toString();
    const signSrc = tokens.pageToken + '|' + tokens.pageRandomStr + '|' + tokenTime + tokens.visitSalt;
    const tokenSign = dealVisitSign(signSrc);

    const params = new URLSearchParams();
    params.append("ac", ac);
    params.append("r", rand());
    params.append("token", tokens.tokenValue || "default");
    params.append("token_version", "v2");
    params.append("page_token", tokens.pageToken);
    params.append("enter_time", tokens.enterTime);
    params.append("token_time", tokenTime);
    params.append("token_time2", now.toString());
    params.append("serverTimeInfo[enter_set_time]", tokens.enterSetTime);
    params.append("serverTimeInfo[time_diff]", "0");
    params.append("random_str", tokens.pageRandomStr);
    params.append("token_sign", tokenSign);
    params.append("scookie", scookie);
    params.append("device", DEVICE);
    for (const [key, value] of Object.entries(extra)) {
        params.append(key, value);
    }
    const body = params.toString();
    const res = await httpPost(CORNFARM_URL, body, { Referer: CORNFARM_REFERER });
    try {
        return JSON.parse(res);
    } catch (e) {
        return null;
    }
}

// 获取玉米庄园页面 token
async function getCornfarmTokens() {
    try {
        const url = "https://huodong3.3839.com/n/hykb/cornfarm/index.php?imm=0";
        const html = await httpGet(url);

        const pageTokenMatch = html.match(/var\s+pageToken\s*=\s*["']([^"']+)["']/);
        const pageToken = pageTokenMatch ? pageTokenMatch[1] : "";

        const randomStrMatch = html.match(/var\s+pageRandomStr\s*=\s*["']([^"']+)["']/);
        const pageRandomStr = randomStrMatch ? randomStrMatch[1] : "";

        const getsetTimeMatch = html.match(/var\s+getsetTime\s*=\s*(\d+)/);
        const getsetTime = getsetTimeMatch ? parseInt(getsetTimeMatch[1]) : 0;
        const enterTime = (getsetTime * 1000).toString();

        const saltMatch = html.match(/var\s+visitSalt\s*=\s*["']([^"']+)["']/);
        const visitSalt = saltMatch ? saltMatch[1] : "|visitV2";

        return { pageToken, pageRandomStr, enterTime, enterSetTime: enterTime, visitSalt, tokenValue: "default" };
    } catch (e) {
        return null;
    }
}

// 爆米花签到
async function cornfarmSign(scookie, tokens) {
    const signAjaxUrl = "https://huodong3.3839.com/n/hykb/cornfarm/ajax_sign.php";
    const now = Date.now();
    const tokenTime = now.toString();
    const signSrc = tokens.pageToken + '|' + tokens.pageRandomStr + '|' + tokenTime + tokens.visitSalt;
    const tokenSign = dealVisitSign(signSrc);

    const params = new URLSearchParams();
    params.append("ac", "Sign");
    params.append("r", rand());
    params.append("token", tokens.tokenValue || "default");
    params.append("token_version", "v2");
    params.append("page_token", tokens.pageToken);
    params.append("enter_time", tokens.enterTime);
    params.append("token_time", tokenTime);
    params.append("token_time2", now.toString());
    params.append("serverTimeInfo[enter_set_time]", tokens.enterSetTime);
    params.append("serverTimeInfo[time_diff]", "0");
    params.append("random_str", tokens.pageRandomStr);
    params.append("token_sign", tokenSign);
    params.append("scookie", scookie);
    params.append("device", DEVICE);
    params.append("smdeviceid", "");
    params.append("verison", "1.5.8.107");
    params.append("OpenAutoSign", "close");

    const body = params.toString();
    const res = await httpPost(signAjaxUrl, body, { Referer: CORNFARM_REFERER });
    try {
        return JSON.parse(res);
    } catch (e) {
        return null;
    }
}

// 爆米花每日任务 AJAX 请求
async function cornfarmDailyAjax(ac, scookie, tokens, extra = {}) {
    const dailyUrl = "https://huodong3.3839.com/n/hykb/cornfarm/ajax_daily.php";
    const now = Date.now();
    const tokenTime = now.toString();
    const signSrc = tokens.pageToken + '|' + tokens.pageRandomStr + '|' + tokenTime + tokens.visitSalt;
    const tokenSign = dealVisitSign(signSrc);

    const params = new URLSearchParams();
    params.append("ac", ac);
    params.append("r", rand());
    params.append("token", tokens.tokenValue || "default");
    params.append("token_version", "v2");
    params.append("page_token", tokens.pageToken);
    params.append("enter_time", tokens.enterTime);
    params.append("token_time", tokenTime);
    params.append("token_time2", now.toString());
    params.append("serverTimeInfo[enter_set_time]", tokens.enterSetTime);
    params.append("serverTimeInfo[time_diff]", "0");
    params.append("random_str", tokens.pageRandomStr);
    params.append("token_sign", tokenSign);
    params.append("scookie", scookie);
    params.append("device", DEVICE);
    for (const [key, value] of Object.entries(extra)) {
        params.append(key, value);
    }
    const body = params.toString();
    const res = await httpPost(dailyUrl, body, { Referer: CORNFARM_REFERER });
    try {
        return JSON.parse(res);
    } catch (e) {
        return null;
    }
}

// 领取爆米花每日任务奖励
async function claimCornfarmDailyReward(ac, taskId, scookie, tokens) {
    return await cornfarmDailyAjax(ac, scookie, tokens, {
        id: taskId.toString(),
        smdeviceid: "",
        verison: "158"
    });
}

// 执行爆米花任务
async function runCornfarmTasks(scookie) {
    console.log("【爆米花任务】");

    const tokens = await getCornfarmTokens();
    if (!tokens || !tokens.pageToken) {
        console.log("  获取页面token失败，跳过");
        return;
    }

    // 登录
    const loginData = await cornfarmAjax("login", scookie, tokens);
    if (!loginData || loginData.key !== "ok") {
        console.log(`  登录失败: ${JSON.stringify(loginData)?.substring(0, 100)}`);
        return;
    }
    const config = loginData.config || {};
    console.log(`  用户: ${config.name || "未知"} 爆米花: ${config.baomihua || 0}`);

    if (config.token_value) {
        tokens.tokenValue = config.token_value;
    }

    // 签到
    const signData = await cornfarmSign(scookie, tokens);
    if (signData) {
        if (signData.key === "1001" || signData.key === "ok") {
            console.log("  签到成功");
        } else if (signData.key === "1002") {
            console.log("  未种下种子，先去播种");
        } else if (signData.key === "1003") {
            console.log("  成熟度已满，请先收割");
        } else {
            console.log(`  签到: key=${signData.key}`);
        }
    }

    await sleep(500);

    // 获取爆米花每日任务
    const dailyData = await cornfarmDailyAjax("dailyInit", scookie, tokens, { VersionCode: "158" });
    if (dailyData && dailyData.key === "ok") {
        const tasks = dailyData.user_daily_Task || {};
        const taskKeys = Object.keys(tasks);
        if (taskKeys.length > 0) {
            console.log(`  每日任务: ${taskKeys.length}个`);
            for (const idx of taskKeys) {
                const task = tasks[idx];
                if (!task) continue;
                const success = parseInt(task.success);
                const title = task.task_title || task.title || `任务${task.rwid}`;
                const rwid = task.rwid;
                const mode = task.mode;

                if (success === 2) {
                    console.log(`    ${title}: 已完成`);
                    continue;
                }

                // 根据 mode 选择领奖函数
                const lingMap = {
                    1: "DailyShareLing", 2: "DailyDatiLing", 3: "DailyDownGameLing",
                    4: "DailyJiaohuLing", 5: "DailyAppLing", 7: "DailyInteractiveLing",
                    9: "DailyYuyueLing", 11: "DailyGameCateLing", 12: "DailyTencentLing",
                    13: "DailyChangshangLing", 14: "DailyToWechatRemindLing",
                    15: "DailySmallGameLing", 16: "DailyToWeiboRemindLing",
                    17: "DailyToH5UrlLing", 18: "DailyKuaiwanGameLing", 20: "DailySmallGameLing"
                };
                const lingAc = lingMap[mode];
                if (!lingAc) continue;

                if (success === 1) {
                    // 可领取
                    const res = await claimCornfarmDailyReward(lingAc, rwid, scookie, tokens);
                    if (res?.key === "ok") {
                        const bmh = res.reward_bmh_num || 0;
                        const csd = res.reward_csd_num || 0;
                        console.log(`    ${title}: 领取成功 +${bmh}爆米花 +${csd}成熟度`);
                    } else {
                        console.log(`    ${title}: ${res?.key || "请求失败"}`);
                    }
                } else if (success === -1) {
                    // 需要先完成任务，尝试直接领取
                    const res = await claimCornfarmDailyReward(lingAc, rwid, scookie, tokens);
                    if (res?.key === "ok") {
                        const bmh = res.reward_bmh_num || 0;
                        console.log(`    ${title}: 领取成功 +${bmh}爆米花`);
                    }
                }
                await sleep(300);
            }
        } else {
            console.log("  每日任务: 无");
        }
    }

    await sleep(500);

    // 获取最终状态
    const reloadData = await cornfarmAjax("ReloadMyData", scookie, tokens);
    if (reloadData && reloadData.key === "ok") {
        console.log(`  种子: ${reloadData.seed || 0} 爆米花: ${reloadData.baomihua || 0} 成熟度: ${reloadData.chengshoudu || 0}`);

        // 成熟度满自动收割再播种
        if (reloadData.chengshoudu >= 100) {
            await cornfarmAjax("PlantRipe", scookie, tokens);
            await sleep(300);
            await cornfarmAjax("PlantSow", scookie, tokens);
            console.log("  自动收割并重新播种");
        }
    }
}

// ==================== 主流程 ====================

async function runOneAccount(scookie, idx) {
    console.log(`\n========== 账号[${idx}]开始执行 ==========`);

    // 爆友等级任务
    await runBaoyouTasks(scookie);
    await sleep(1000);

    // 爆米花任务
    await runCornfarmTasks(scookie);
    await sleep(1000);

    // 游戏签到任务
    console.log("【游戏签到任务】");
    const gameItems = await getGameSignIds(scookie);
    if (gameItems.length > 0) {
        console.log(`  找到${gameItems.length}个游戏签到活动`);
        await gameSignIn(scookie, gameItems);
    } else {
        console.log("  暂无游戏签到活动");
    }

    console.log(`========== 账号[${idx}]执行完成 ==========\n`);
    return true;
}

async function hykb() {
    let success = true;
    console.log("【好游快爆】：开始执行...");

    const cookie = getConfig("", "ONESIGN_HYKB_COOKIE");
    if (!cookie) {
        console.log("【好游快爆】：未配置 ONESIGN_HYKB_COOKIE 变量");
        success = false;
    } else {
        const cookies = cookie.split("@").filter(t => t.trim());
        for (let i = 0; i < cookies.length; i++) {
            let scookie = cookies[i].trim().replace(/\n/g, "");
            const ok = await runOneAccount(scookie, i + 1);
            if (!ok) success = false;
            if (i < cookies.length - 1) await sleep(3000);
        }
    }

    if (!success) process.exit(1);
}

hykb();
