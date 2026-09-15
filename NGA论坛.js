/*
抓包：NGA app 内，抓包工具 → 任意 API 请求（如签到页）
      请求体中有 access_uid 和 access_token，复制值
      Request Headers 中的 User-Agent 复制整段
变量：ONESIGN_NGA_UID / ONESIGN_NGA_ACCESSTOKEN / ONESIGN_NGA_UA

cron: 20 8 * * *
new Env('NGA论坛签到');
*/

const axios = require("axios");
const SCRIPT_NAME = "NGA论坛";
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

const ngaUid = getConfig("nga.uid", "ONESIGN_NGA_UID");
const ngaToken = getConfig("nga.accesstoken", "ONESIGN_NGA_ACCESSTOKEN");
const ngaUA = getConfig("nga.UA", "ONESIGN_NGA_UA");

function ngaGet(lib, act, output = 11, other = null) {
    return new Promise(async (resolve) => {
        try {
            const url = "https://ngabbs.com/nuke.php";
            const res = await axios.post(
                url,
                `access_uid=${ngaUid}&access_token=${ngaToken}&app_id=1010&__act=${act}&__lib=${lib}&__output=${output}&${other}`,
                {
                    headers: {
                        "User-Agent": ngaUA || "xxxxxx Nga_Official/90409"
                    }
                }
            );
            console.log("    " + (res.data && res.data.time || res.data.code));
            resolve(res.data);
        } catch (err) {
            console.log(err);
            resolve({ error: ["签到接口请求出错"] });
        }
    });
}

async function task() {
    let success = true;
    console.log("【NGA】：开始签到...");
    const res1 = await ngaGet("check_in", "check_in");
    if (res1 && res1.data) {
        console.log("签到：" + res1.data[0]);
    } else {
        console.log("签到：" + (res1.error && res1.error[0]));
        if (String(res1.error && res1.error[0]).match(/登录|CLIENT/)) success = false;
    }
    if (!String(res1 && res1.data).match(/登录|CLIENT/)) {
        await ngaGet("mission", "checkin_count_add", 11, "mid=2&get_success_repeat=1&no_compatible_fix=1");
        await ngaGet("mission", "checkin_count_add", 11, "mid=131&get_success_repeat=1&no_compatible_fix=1");
        await ngaGet("mission", "checkin_count_add", 11, "mid=30&get_success_repeat=1&no_compatible_fix=1");
        console.log("看视频免广告");
        await ngaGet("mission", "video_view_task_counter_add_v2_for_adfree_sp1");
        for (let c of new Array(4)) await ngaGet("mission", "video_view_task_counter_add_v2_for_adfree");
        console.log("看视频得N币");
        for (let c of new Array(5)) await ngaGet("mission", "video_view_task_counter_add_v2");
        console.log("分享帖子 5");
        const tid = Math.ceil(Math.random() * 12346567) + 12345678;
        for (let c of new Array(5)) await ngaGet("data_query", "topic_share_log_v2", 12, "event=4&tid=" + tid);
        console.log("领取分享奖励 1N币");
        await ngaGet("mission", "check_mission", 11, "mid=149&get_success_repeat=1&no_compatible_fix=1");
        const stat = await ngaGet("check_in", "get_stat");
        if (stat && stat.data) {
            const [sign, money, y] = stat.data;
            console.log(`连签 ${sign.continued}天 累签 ${sign.sum}天`);
            console.log(`N币：${money.money_n}  铜币：${money.money}  啊哈：${y[0]}`);
        }
    }
    if (!success) { process.exit(1); }
}

task();