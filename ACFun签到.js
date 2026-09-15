/**
 * 抓包：ACFun app → 登录 → 抓包获取 cookie
 * 变量：ONESIGN_ACFUN_COOKIE（cookie 值，多账号用 @ 或换行分隔）
 *
 * cron: 0 9 * * *
 * new Env('ACFun签到');
 */

const axios = require("axios");
const SCRIPT_NAME = "ACFun";
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

async function acfunPost(url, data, headers) {
    try {
        const response = await axios.post("https://www.acfun.cn/rest/pc-direct" + url, data, { headers });
        return response.data;
    } catch (e) {
        if (e.response) return e.response.data;
        return { result: -1 };
    }
}

async function acfun() {
    let success = true;
    console.log("【ACFun】：开始签到...");

    const cookie = getConfig("", "ONESIGN_ACFUN_COOKIE");
    if (!cookie) {
        console.log("【ACFun】：未配置 ONESIGN_ACFUN_COOKIE 变量");
        success = false;
    } else {
        const cookies = cookie.split(/[@\n]/).filter(t => t.trim());
        const headers = {
            "referer": "https://www.acfun.cn/",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Safari/537.36",
        };

        for (let i = 0; i < cookies.length; i++) {
            const idx = i + 1;
            const ck = cookies[i].trim();
            headers.cookie = ck;
            console.log(`----- 账号[${idx}]开始执行 -----`);

            try {
                // 签到
                const signResult = await acfunPost("/user/signIn", {}, headers);
                if (signResult.result === 0) {
                    console.log("签到成功！");
                } else if (signResult.result === 122) {
                    console.log("今天已经签到过啦！");
                } else {
                    console.log(`签到失败: ${JSON.stringify(signResult)}`);
                    success = false;
                }

                // 获取用户信息
                const infoResult = await acfunPost("/user/personalInfo", "", headers);
                if (infoResult.info) {
                    console.log(`香蕉: ${infoResult.info.banana}  金香蕉: ${infoResult.info.goldBanana}`);
                } else {
                    console.log(`账号[${idx}] 获取用户信息失败`);
                    success = false;
                }

                // 投蕉
                const tossResult = await acfunPost("/banana/throwBanana", `resourceId=${Math.round(Math.random() * 10000) + 14431808}&count=1&resourceType=2`, headers);
                if (tossResult.result === 0) {
                    console.log("投蕉成功！");
                }

                // 发送弹幕
                const danmuResult = await acfunPost("/new-danmaku/add", "mode=1&color=16777215&size=25&body=%E5%A5%BD%E8%80%B6&videoId=21772556&position=0&type=douga&id=26084622&subChannelId=60&subChannelName=%E5%A8%B1%E4%B9%90&roleId=", headers);
                if (danmuResult.result === 0) {
                    console.log("发送弹幕成功！");
                }
            } catch (e) {
                console.log(`账号[${idx}] 请求异常: ${e.message}`);
                success = false;
            }

            await new Promise(r => setTimeout(r, 2000));
        }
    }

    if (!success) { process.exit(1); }
}

acfun();