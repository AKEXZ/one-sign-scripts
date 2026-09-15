/*
抓包：浏览器打开 bbs.binmt.cc 登录后，F12 → Network → 任意请求
      找到 Request Headers 中的 Cookie 字段，整段复制
变量：ONESIGN_MT_COOKIE

cron: 15 8 * * *
new Env('MT论坛签到');
*/

const { spawn } = require("child_process");
const SCRIPT_NAME = "MT论坛";
const { getConfig } = (() => {
    const fs = require("fs");
    const path = require("path");
    function getConfig(key, envName) {
        if (process.env[envName]) return process.env[envName];
        try {
            const configPath = path.join(__dirname, "..", "config.yml");
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

const cookie = getConfig("mt.cookie", "ONESIGN_MT_COOKIE");
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15";

function curlGet(url, referer) {
    return new Promise((resolve) => {
        let args = ["-s", "-w", "\n%{http_code}", "-H", "Cookie: " + cookie, "-H", "User-Agent: " + UA, "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"];
        if (referer) {
            args.push("-H", "Referer: " + referer);
        }
        args.push(url);
        let stdout = "";
        let child = spawn("curl", args, { timeout: 15000 });
        child.stdout.on("data", (d) => stdout += d);
        child.on("close", () => {
            let lines = stdout.trim().split("\n");
            let status = parseInt(lines.pop()) || 0;
            let data = lines.join("\n");
            resolve({ status, data });
        });
        child.on("error", () => {
            resolve({ status: 0, data: "" });
        });
    });
}

async function mt() {
    let success = true;
    console.log("【MT论坛】：开始签到...");
    if (!cookie) {
        console.log("未配置 ONESIGN_MT_COOKIE 变量或 config.yml 中 mt.cookie");
        process.exit(1);
    }
    try {
        let res = await curlGet("https://bbs.binmt.cc/k_misign-sign.html", "https://bbs.binmt.cc/forum.php");
        if (res.status !== 200) {
            console.log("请求失败，状态码:", res.status);
            success = false;
        } else {
            let formhash = res.data.match(/formhash=([a-f0-9]+)/);
            if (formhash && !res.data.match(/登录/)) {
                let signurl = "https://bbs.binmt.cc/plugin.php?id=k_misign:sign&operation=qiandao&formhash=" + formhash[1] + "&format=empty&inajax=1&ajaxtarget=";
                let res2 = await curlGet(signurl, "https://bbs.binmt.cc/k_misign-sign.html");
                if (res2.data.match(/今日已签/)) {
                    console.log("今天已经签到过啦");
                } else if (res2.data.match(/签到成功/)) {
                    let msg1 = res2.data.match(/获得随机奖励.+?金币/);
                    let msg2 = res2.data.match(/已累计签到 \d+ 天/);
                    console.log("签到成功\n" + (msg1 || "") + "\n" + (msg2 || ""));
                } else if (res2.data.match(/CDATA/)) {
                    console.log("签到成功！");
                } else {
                    console.log("签到失败!原因未知");
                    console.log(res2.data.substring(0, 500));
                    success = false;
                }
            } else {
                console.log("cookie失效，请重新抓包获取");
                success = false;
            }
        }
    } catch (err) {
        console.log("请求出错:", err.message);
        success = false;
    }
    if (!success) { process.exit(1); }
}

mt().catch(async err => { console.log("未捕获错误:", err.message); process.exit(1); });