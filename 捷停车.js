/**
 * 抓包：捷停车小程序 我的 → 停车币 → 抓包获取 userId 和 token
 * 变量：ONESIGN_JTC_TOKEN（格式：userId,token，多账号用 @ 或换行分隔）
 *
 * cron: 15 9 * * *
 * new Env('捷停车签到');
 */

const axios = require("axios");
const SCRIPT_NAME = "捷停车";
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

async function httpRequest(options) {
    try {
        const response = await axios(options);
        return response.data;
    } catch (e) {
        if (e.response) return e.response.data;
        return null;
    }
}

async function jtc() {
    let success = true;
    console.log("【捷停车】：开始签到...");

    const token = getConfig("", "ONESIGN_JTC_TOKEN");
    if (!token) {
        console.log("【捷停车】：未配置 ONESIGN_JTC_TOKEN 变量");
        success = false;
    } else {
        const tokens = token.split(/[@\n]/).filter(t => t.trim());

        for (let i = 0; i < tokens.length; i++) {
            const idx = i + 1;
            const parts = tokens[i].trim().split(',');
            if (parts.length < 2) {
                console.log(`账号[${idx}] 格式错误，需要 userId,token`);
                success = false;
                continue;
            }
            const userId = parts[0];
            const userToken = parts[1];

            console.log(`----- 账号[${idx}]开始执行 -----`);

            const headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15',
            };

            try {
                // 签到
                const signResult = await httpRequest({
                    method: 'POST',
                    url: 'https://sytgate.jslife.com.cn/base-gateway/integral/v2/task/receive',
                    headers,
                    data: { userId, reqSource: "APP_JTC", taskNo: "T00", token: userToken },
                });

                if (signResult && signResult.success) {
                    console.log(`签到成功，获得 ${signResult.data} 停车币`);
                } else {
                    console.log(`签到: ${signResult?.message || '已签到或失败'}`);
                }

                // 浏览任务
                await httpRequest({
                    method: 'POST',
                    url: 'https://sytgate.jslife.com.cn/base-gateway/integral/v2/task/complete',
                    headers,
                    data: { userId, reqSource: "APP_JTC", taskNo: "T01", token: userToken },
                });

                await new Promise(r => setTimeout(r, 10000));

                // 领取浏览奖励
                const browseResult = await httpRequest({
                    method: 'POST',
                    url: 'https://sytgate.jslife.com.cn/base-gateway/integral/v2/task/receive',
                    headers,
                    data: { userId, reqSource: "APP_JTC", taskNo: "T01", token: userToken },
                });

                if (browseResult && browseResult.success) {
                    console.log(`浏览任务完成，获得 ${browseResult.data} 停车币`);
                } else {
                    console.log(`浏览任务: ${browseResult?.message || '已完成或失败'}`);
                }

                // 获取用户信息
                const userResult = await httpRequest({
                    method: 'POST',
                    url: 'https://sytgate.jslife.com.cn/base-gateway/member/queryMbrCityBaseInfo',
                    headers,
                    data: { userId, reqSource: "APP_JTC", token: userToken },
                });

                if (userResult && userResult.success) {
                    const integralValue = userResult.data?.integralValue || 0;
                    console.log(`停车币余额: ${integralValue} 可抵扣: ${(integralValue / 1000).toFixed(2)} 元`);
                } else {
                    console.log(`账号[${idx}] 获取用户信息失败`);
                    success = false;
                }
            } catch (e) {
                console.log(`账号[${idx}] 请求异常: ${e.message}`);
                success = false;
            }

            await new Promise(r => setTimeout(r, 3000));
        }
    }

    if (!success) { process.exit(1); }
}

jtc();