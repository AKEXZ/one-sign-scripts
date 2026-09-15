/**
 * 抓包：奇瑞汽车 app → 我的 → 签到 → 抓包获取 Authorization 值（去掉 Bearer 前缀）
 * 变量：ONESIGN_CHERY_TOKEN（Authorization 值，多账号用 @ 或换行分隔）
 *
 * cron: 9 7 * * *
 * new Env('奇瑞汽车签到');
 */

const axios = require("axios");
const SCRIPT_NAME = "奇瑞汽车";
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
        return { status: response.status, data: response.data };
    } catch (e) {
        if (e.response) {
            return { status: e.response.status, data: e.response.data };
        }
        return { status: 0, data: null, error: e.message };
    }
}

async function chery() {
    let success = true;
    console.log("【奇瑞汽车】：开始签到...");

    const token = getConfig("", "ONESIGN_CHERY_TOKEN");
    if (!token) {
        console.log("【奇瑞汽车】：未配置 ONESIGN_CHERY_TOKEN 变量");
        success = false;
    } else {
        const tokens = token.split(/[@\n]/).filter(t => t.trim());

        for (let i = 0; i < tokens.length; i++) {
            const ck = tokens[i].trim();
            const idx = i + 1;
            console.log(`----- 账号[${idx}]开始执行 -----`);

            const headers = {
                "Host": "mobile-consumer-sapp.chery.cn",
                "Authorization": "Bearer " + ck,
                "accept-language": "zh-CN,zh",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; MI 8 Lite Build/QKQ1.190910.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.138 Mobile Safari/537.36 android/1.0.0",
                "content-type": "application/json",
                "Accept": "*/*",
                "Origin": "https://hybrid-sapp.chery.cn",
                "Referer": "https://hybrid-sapp.chery.cn/package-mine/pages/sign-in/sign-in",
            };

            try {
                // 获取用户信息
                let result = await httpRequest({
                    url: `https://mobile-consumer-sapp.chery.cn/web/user/current/details?access_token=${ck}&terminal=3`,
                    headers,
                });
                if (result.status === 200 && result.data) {
                    console.log(`账号[${idx}] 昵称: ${result.data.displayName} 积分: ${result.data.pointAccount?.payableBalance || 0}`);
                } else {
                    console.log(`账号[${idx}] 获取用户信息失败: ${result.data?.message || ''}`);
                    success = false;
                    continue;
                }

                // 签到
                result = await httpRequest({
                    method: 'POST',
                    url: `https://mobile-consumer-sapp.chery.cn/web/event/trigger?access_token=${ck}`,
                    headers: { ...headers, "X-Requested-With": "com.digitalmall.chery" },
                    data: { eventCode: "SJ10002" },
                });
                if (result.status === 200) {
                    console.log(`账号[${idx}] 签到: ${result.data?.message || '成功'}`);
                } else {
                    console.log(`账号[${idx}] 签到失败: ${result.data?.message || ''}`);
                    success = false;
                }

                // 获取文章列表
                const articleResult = await httpRequest({
                    url: `https://mobile-consumer-sapp.chery.cn/web/community/recommend/contents?pageNo=1&pageSize=10&access_token=${ck}&terminal=3`,
                    headers,
                });
                if (articleResult.status === 200 && articleResult.data?.data?.data) {
                    const articles = articleResult.data.data.data;
                    if (articles.length > 0) {
                        // 分享文章
                        for (let j = 0; j < Math.min(2, articles.length); j++) {
                            const articleId = articles[j].content.id;
                            const shareResult = await httpRequest({
                                method: 'POST',
                                url: `https://mobile-consumer-sapp.chery.cn/web/community/contents/${articleId}/share?access_token=${ck}&terminal=3`,
                                headers,
                                data: { contentId: articleId },
                            });
                            if (shareResult.status === 200) {
                                console.log(`账号[${idx}] 分享文章成功: ${shareResult.data?.message || ''}`);
                            }
                        }
                    }
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

chery();