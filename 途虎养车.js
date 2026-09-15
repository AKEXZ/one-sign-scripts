/**
 * 抓包：途虎养车小程序 → 积分页面 → 抓包获取 Authorization (去掉 Bearer)
 * 变量：ONESIGN_TUHU_TOKEN（token）
 *       多账号用 @ 分隔
 *
 * cron: 12 8 * * *
 * new Env('途虎养车签到');
 */

const axios = require("axios");
const SCRIPT_NAME = "途虎养车";
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
        return { data: response.data, status: response.status };
    } catch (e) {
        if (e.response) {
            const respData = e.response.data;
            const preview = typeof respData === 'string' ? respData.substring(0, 200) : JSON.stringify(respData);
            console.log(`请求失败 [${e.response.status}]: ${preview}`);
            return { data: respData, status: e.response.status };
        }
        console.log(`网络错误: ${e.message}`);
        return { data: null, status: 0 };
    }
}

function hideMobile(mobile) {
    if (!mobile) return '';
    return mobile.slice(0, 3) + '****' + mobile.slice(-4);
}

async function tuhu() {
    let success = true;
    console.log("【途虎养车】：开始签到...");

    const tokenStr = getConfig("", "ONESIGN_TUHU_TOKEN") || '';
    const tokenArr = tokenStr.split('@').filter(t => t.trim());

    if (!tokenArr.length) {
        console.log("【途虎养车】：未配置 ONESIGN_TUHU_TOKEN 变量");
        success = false;
    } else {
        for (let i = 0; i < tokenArr.length; i++) {
            const idx = i + 1;
            const token = tokenArr[i].trim();

            const baseHeaders = {
                'Authorization': token.startsWith('Bearer ') ? token : 'Bearer ' + token,
                'authType': 'oauth',
                'Content-Type': 'application/json',
                'version': '7.73.3',
                'channel': 'wechat-miniprogram',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Mac MacWechat/WMPF MacWechat/3.8.7(0x13080712) UnifiedPCMacWechat(0xf2641a50) XWEB/19978',
                'Referer': 'https://servicewechat.com/wx27d20205249c56a3/1385/page-frame.html',
            };

            console.log(`----- 账号[${idx}]开始执行 -----`);

            try {
                // 获取用户信息
                const userRes = await httpRequest({
                    method: 'POST',
                    url: 'https://cl-gateway.tuhu.cn/cl-user-info-site/userAccount/getCurrentUserInfo',
                    headers: baseHeaders,
                    data: '{}',
                });
                const userResult = userRes.data;

                if (userResult?.code === 10000 && userResult?.data) {
                    const { nickName, mobile } = userResult.data;
                    console.log(`用户: ${nickName} [${hideMobile(mobile)}]`);
                } else {
                    console.log(`账号[${idx}] 获取用户信息失败，token可能无效`);
                    success = false;
                    continue;
                }

                // 查询签到状态
                const signInfoRes = await httpRequest({
                    method: 'POST',
                    url: 'https://cl-gateway.tuhu.cn/cl-common-api/api/member/getSignInInfo',
                    headers: baseHeaders,
                    data: JSON.stringify({ channel: 'WXAPP' }),
                });
                const signInfo = signInfoRes.data;

                if (signInfo?.code === 10000 && signInfo?.data) {
                    if (signInfo.data.signInStatus) {
                        const days = signInfo.data.continuousDays || 0;
                        console.log(`今日已签到，连续签到${days}天`);
                    } else {
                        // 执行签到
                        const checkInRes = await httpRequest({
                            method: 'POST',
                            url: 'https://cl-gateway.tuhu.cn/cl-common-api/api/dailyCheckIn/userCheckIn',
                            headers: baseHeaders,
                            data: JSON.stringify({ channel: 'wxapp' }),
                        });
                        const checkInResult = checkInRes.data;

                        if (checkInResult?.code === 10000 && checkInResult?.data?.checkInResult) {
                            const days = checkInResult.data.continuousDays || 1;
                            const reward = checkInResult.data.rewardIntegral || 0;
                            console.log(`签到成功，连续签到${days}天，获得${reward}积分`);
                        } else {
                            console.log(`签到失败: ${JSON.stringify(checkInResult)}`);
                            success = false;
                        }
                    }
                } else {
                    console.log(`查询签到状态失败，直接尝试签到`);
                    const checkInRes = await httpRequest({
                        method: 'POST',
                        url: 'https://cl-gateway.tuhu.cn/cl-common-api/api/dailyCheckIn/userCheckIn',
                        headers: baseHeaders,
                        data: JSON.stringify({ channel: 'wxapp' }),
                    });
                    const checkInResult = checkInRes.data;

                    if (checkInResult?.code === 10000 && checkInResult?.data?.checkInResult) {
                        const days = checkInResult.data.continuousDays || 1;
                        const reward = checkInResult.data.rewardIntegral || 0;
                        console.log(`签到成功，连续签到${days}天，获得${reward}积分`);
                    } else {
                        console.log(`签到失败: ${JSON.stringify(checkInResult)}`);
                        success = false;
                    }
                }

                // 获取积分
                const integralRes = await httpRequest({
                    method: 'POST',
                    url: 'https://api.tuhu.cn/user/SelectUserIntegralByUserId',
                    headers: baseHeaders,
                    data: JSON.stringify({ channel: 'wx_app' }),
                });
                const integralResult = integralRes.data;

                if (integralResult?.Code === '1') {
                    console.log(`当前积分: ${integralResult.UserIntegral || 0}`);
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

tuhu();