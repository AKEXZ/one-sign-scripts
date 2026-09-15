/*
抓包：阿里云盘 app 登录后，抓包工具 → 请求 auth.aliyundrive.com
      找到请求体中的 refresh_token 字段，复制值
      或浏览器打开 aliyundrive.com 登录后，F12 → Application → Local Storage
      找 token 对象中的 refresh_token
变量：ONESIGN_ALIYUN_REFRESH_TOKEN

cron: 30 8 * * *
new Env('阿里云盘签到');
*/

const axios = require("axios");
const SCRIPT_NAME = "阿里云盘";
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

const refreshToken = getConfig("aliyun.refresh_token", "ONESIGN_ALIYUN_REFRESH_TOKEN");

async function getAccessToken() {
    try {
        const res = await axios.post(
            "https://auth.aliyundrive.com/v2/account/token",
            {
                grant_type: "refresh_token",
                app_id: "pJZInNHN2dZWk8qg",
                refresh_token: refreshToken,
            },
            { headers: { "Content-Type": "application/json; charset=UTF-8" } }
        );
        if (res.data.code === "InvalidParameter.RefreshToken" || res.data.code === "RefreshTokenExpired") {
            console.log(`token刷新失败,${res.data.message}`);
            return null;
        }
        console.log(`用户: ${res.data.nick_name}`);
        return { name: res.data.nick_name, token: res.data.access_token };
    } catch (err) {
        console.log("token接口请求失败");
        return null;
    }
}

async function sign(token, name) {
    try {
        const res = await axios.post(
            "https://member.aliyundrive.com/v1/activity/sign_in_list",
            { isReward: false },
            {
                headers: {
                    "Content-Type": "application/json",
                    "User-Agent": "AliApp(AYSD/6.15.1) com.alicloud.databox/54705669 Channel/36176927979800@rimet_android_6.15.1 language/zh-CN /Android Mobile/realme RMX5062",
                    "x-canary": "client=Android,app=adrive,version=v6.15.1",
                    Authorization: "Bearer " + token,
                },
            }
        );
        if (res.data.success) {
            console.log(`${name}，已连续签到${res.data.result.signInCount}天!`);
            return res.data.result.signInCount;
        } else {
            console.log(`${name}，签到失败，${res.data.message}!`);
            return -1;
        }
    } catch (err) {
        console.log("签到接口请求失败");
        return -1;
    }
}

async function aliyun() {
    let success = true;
    const auth = await getAccessToken();
    if (!auth) {
        console.log("【阿里云盘】：token刷新失败");
        success = false;
    } else {
        const day = await sign(auth.token, auth.name);
        if (day < 0) {
            success = false;
        } else {
            console.log("奖励领取需客户端签名，请在app内手动领取");
        }
        console.log("【阿里云盘】：签到完成");
    }
    if (!success) { process.exit(1); }
}

aliyun();