/**
 * 好游快爆爆米花商城抢兑
 * 抓包：好游快爆 app → 爆米花商城 → 选择商品 → 分享给好友
 *      链接如 https://huodong3.3839.com/n/hykb/bmhstore2/inc/libao/index.php?gid=6237
 *      gid=6237 → 填 ONESIGN_HYKB_GID，key=libao → 填 ONESIGN_HYKB_KEY
 *      scookie 同好游快爆.js
 * 变量：ONESIGN_HYKB_COOKIE / ONESIGN_HYKB_GID / ONESIGN_HYKB_KEY
 *
 * cron: 59 12 * * *
 * new Env('好游快爆抢兑');
 */

const https = require("https");
const zlib = require("zlib");
const SCRIPT_NAME = "好游快爆抢兑";

const UA_WEBVIEW = "Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/151.0.7922.170 Mobile Safari/537.36Androidkb/1.5.8.107(android;RMX5062;15;1280x2612;);@4399_sykb_android_activity@";
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

// ==================== 抢兑 ====================

const SCRIPT_TAG = "【好游快爆抢兑】";

const hyck = getConfig("", "ONESIGN_HYKB_COOKIE");
const gid = getConfig("", "ONESIGN_HYKB_GID");
const key = getConfig("", "ONESIGN_HYKB_KEY");
const scookie = hyck ? hyck.trim() : hyck;

async function post(ac, extra, keyValue) {
    const encodedKey = encodeURIComponent(keyValue);
    const capitalizedKey = encodeURIComponent(keyValue.slice(0, 1).toUpperCase() + keyValue.slice(1));
    const url = `https://huodong3.3839.com/n/hykb/bmhstore2/inc/${encodedKey}/ajax${capitalizedKey}.php`;

    const params = new URLSearchParams();
    params.append("ac", ac);
    params.append("r", rand());
    params.append("scookie", scookie);
    params.append("device", DEVICE);
    for (const [k, v] of Object.entries(extra)) {
        params.append(k, v);
    }
    const body = params.toString();

    const res = await httpPost(url, body, {
        Referer: `https://huodong3.3839.com/n/hykb/bmhstore2/inc/${encodedKey}/index.php?gid=${gid}`
    });
    try {
        return JSON.parse(res);
    } catch (e) {
        console.log(`${SCRIPT_TAG} 响应解析失败: ${res?.substring(0, 100)}`);
        return null;
    }
}

async function exchange() {
    let success = true;
    console.log(`${SCRIPT_TAG} 开始抢兑...`);

    if (!hyck) {
        console.log(`${SCRIPT_TAG} 未配置 ONESIGN_HYKB_COOKIE 变量`);
        success = false;
    } else if (!gid) {
        console.log(`${SCRIPT_TAG} 未配置 ONESIGN_HYKB_GID 变量`);
        success = false;
    } else if (!key) {
        console.log(`${SCRIPT_TAG} 未配置 ONESIGN_HYKB_KEY 变量`);
        success = false;
    } else {
        let done = false;
        await post("checkExchange", { gid }, key);
        for (let i = 0; i < 100; i++) {
            const res = await post("exchange", { goodsid: gid }, key);
            if (res && res.key === "ok") {
                console.log(`${SCRIPT_TAG} 抢兑成功！`);
                done = true;
                break;
            }
        }
        if (!done) {
            console.log(`${SCRIPT_TAG} 抢兑失败，未抢到商品`);
            success = false;
        }
    }

    if (!success) { process.exit(1); }
}

exchange();
