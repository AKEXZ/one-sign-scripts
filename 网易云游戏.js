/*
抓包：浏览器打开 n.cg.163.com 登录后，F12 → Network → 任意 API 请求
      找到 Request Headers 中的 Authorization 字段，整段复制
变量：ONESIGN_CG163_AUTHORIZATION

cron: 30 8 * * *
new Env('网易云游戏签到');
*/

const axios = require("axios");
const SCRIPT_NAME = "网易云游戏";
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

const authorization = getConfig("cg163.Authorization", "ONESIGN_CG163_AUTHORIZATION");

const headers = {
    headers: {
        Authorization: authorization || " bearer xxxxx",
        "user-agent":
            "Mozilla/5.0 (Linux; Android 10; Redmi K30 Build/QKQ1.190825.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/85.0.4183.127 Mobile Safari/537.36",
    },
};

function check() {
    return new Promise(async (resolve) => {
        try {
            const url = "https://n.cg.163.com/api/v2/users/@me";
            await axios.get(url, headers);
            console.log("cookie未失效,即将开始签到...");
            resolve(1);
        } catch (err) {
            console.log(err);
            console.log("cookie已失效");
            resolve(0);
        }
    });
}

function sign() {
    return new Promise(async (resolve) => {
        try {
            const url = "https://n.cg.163.com/api/v2/sign-today";
            await axios.post(url, "", headers);
            console.log("签到成功");
            resolve("签到成功！！ ");
        } catch (err) {
            const msg = "签到失败,已签到过或其它未知原因！！ ";
            console.log(msg);
            resolve(msg);
        }
    });
}

async function cg163() {
    let success = true;
    console.log("【网易云游戏】：开始签到...");
    const ckstatus = await check();
    if (ckstatus === 1) {
        const msg = await sign();
        if (msg.match(/失败/)) success = false;
    } else {
        console.log("cookie失效,请重新抓取cookies...");
        success = false;
    }
    if (!success) { process.exit(1); }
}

cg163();