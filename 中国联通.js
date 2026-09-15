/*
抓包：1. 请求 m.client.10010.com/clientMyPage/v1/api/aggregateFloorData → 请求体 JSON 和 Cookie
      2. 任意 act.10010.com 的请求 → Request Headers → 完整 Cookie 值
必填：ONESIGN_UNICOM_COOKIE（act.10010.com 的 Cookie，含 ecs_token/session 等）
可选：ONESIGN_UNICOM_PHONE（手机号） / ONESIGN_UNICOM_DEVICEID / ONESIGN_UNICOM_APPID

cron: 0 9 * * *
new Env('中国联通签到');
*/

const axios = require("axios");
const SCRIPT_NAME = "中国联通";
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

const phone = getConfig("unicom.phone", "ONESIGN_UNICOM_PHONE");
const deviceId = getConfig("unicom.deviceId", "ONESIGN_UNICOM_DEVICEID");
const appId = getConfig("unicom.appId", "ONESIGN_UNICOM_APPID");
const sessionCookie = getConfig("unicom.cookie", "ONESIGN_UNICOM_COOKIE");

const nativeUa = "Dalvik/2.1.0 (Linux; U; Android 15; RMX5062 Build/UKQ1.231108.001);unicom{version:android@12.1500};ltst;";

const webviewUa = "Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36; unicom{version:android@12.1500,desmobile:0};devicetype{deviceBrand:realme,deviceModel:RMX5062};OSVersion/15;ltst;";

const loginHeaders = {
    "User-Agent": nativeUa,
    "Content-Type": "application/json; charset=utf-8",
};

const signHeaders = {
    "User-Agent": webviewUa,
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://img.client.10010.com",
    "Referer": "https://img.client.10010.com/SigininApp/index.html?cdncachetime=2978647&channel=shouye&webViewNavIsHidden=webViewNavIsHidden",
    "X-Requested-With": "com.sinovatech.unicom.ui",
};

let cookie = "";

async function onlineLogin() {
    try {
        const headers = { ...loginHeaders };
        if (sessionCookie) {
            headers["Cookie"] = sessionCookie;
        }
        const res = await axios.post(
            "https://m.client.10010.com/clientMyPage/v1/api/aggregateFloorData",
            {
                clientVersion: "android@12.1500",
                deviceModel: "RMX5062",
                appUUID: "dcc88322808f4e1a9b5929f81511f411",
                adCode: "410326",
                materialInfo: [],
                longitude: 112.473214,
                latitude: 34.150805,
            },
            { headers }
        );
        if (sessionCookie) {
            cookie = sessionCookie;
        }
        if (res.headers && res.headers["set-cookie"]) {
            const newCookies = res.headers["set-cookie"].map((c) => c.split(";")[0]).join("; ");
            if (cookie) {
                cookie = cookie + "; " + newCookies;
            } else {
                cookie = newCookies;
            }
        }
        if (res.data && res.data.code === "0000") {
            console.log("登录成功");
            return true;
        }
        console.log("登录失败: " + JSON.stringify(res.data));
        return false;
    } catch (err) {
        console.log("登录接口请求失败");
        return false;
    }
}

async function signboard() {
    try {
        const res = await axios.post(
            "https://act.10010.com/SigninApp/convert/signboard",
            "",
            { headers: { ...signHeaders, Cookie: cookie } }
        );
        if (res.data && res.data.status === "0000") {
            console.log("签到成功");
            return true;
        }
        const msg = (res.data && res.data.msg) || "未知错误";
        if (msg.indexOf("已经签到") > -1 || msg.indexOf("已签到") > -1 || msg.indexOf("重复") > -1) {
            console.log("今日已签到");
            return true;
        }
        console.log(`签到失败: ${msg}`);
        return false;
    } catch (err) {
        console.log("签到接口请求失败");
        return false;
    }
}

async function getIntegral() {
    try {
        const res = await axios.get(
            "https://activity.10010.com/sixPalaceGridTurntableLottery/signin/getIntegral",
            { headers: { ...signHeaders, Cookie: cookie } }
        );
        if (res.data && res.data.code === "0000" && res.data.data) {
            return res.data.data.integralTotal || "0";
        }
        return null;
    } catch (err) {
        return null;
    }
}

async function getTaskList(type) {
    try {
        const res = await axios.get(
            `https://activity.10010.com/sixPalaceGridTurntableLottery/task/taskList?type=${type}`,
            { headers: { ...signHeaders, Cookie: cookie } }
        );
        if (res.data && res.data.code === "0000" && res.data.data && res.data.data.taskList) {
            return res.data.data.taskList;
        }
        console.log(`获取任务列表(type=${type})失败: ${res.data && res.data.desc || "未知错误"}`);
        return [];
    } catch (err) {
        console.log(`获取任务列表(type=${type})请求失败`);
        return [];
    }
}

async function completeTask(taskId) {
    try {
        const res = await axios.get(
            `https://activity.10010.com/sixPalaceGridTurntableLottery/task/completeTask?taskId=${taskId}&orderId=&systemCode=QDQD`,
            { headers: { ...signHeaders, Cookie: cookie } }
        );
        if (res.data && res.data.code === "0000") {
            return true;
        }
        console.log(`  完成任务失败: ${res.data && res.data.desc || "未知错误"}`);
        return false;
    } catch (err) {
        console.log(`  完成任务请求失败`);
        return false;
    }
}

async function getTaskReward(taskId) {
    try {
        const res = await axios.get(
            `https://activity.10010.com/sixPalaceGridTurntableLottery/task/getTaskReward?taskId=${taskId}`,
            { headers: { ...signHeaders, Cookie: cookie } }
        );
        if (res.data && res.data.code === "0000" && res.data.data) {
            const d = res.data.data;
            const prize = d.prizeCount || "";
            const name = d.prizeName || "奖励";
            console.log(`  奖励领取成功: ${name} ${prize ? "+" + prize + "元" : ""}`);
            return true;
        }
        console.log(`  奖励领取失败: ${res.data && res.data.desc || "未知错误"}`);
        return false;
    } catch (err) {
        console.log(`  奖励领取请求失败`);
        return false;
    }
}

async function processTasks() {
    console.log("【中国联通】：开始处理任务...");
    const taskTypes = [0, 1, 2, 4];
    const allTaskLists = await Promise.all(taskTypes.map((t) => getTaskList(t)));
    const allTasks = allTaskLists.flat();

    const seen = new Set();
    const uniqueTasks = allTasks.filter((t) => {
        if (!t || !t.id) return false;
        if (seen.has(t.id)) return false;
        seen.add(t.id);
        return true;
    });

    const pendingTasks = uniqueTasks.filter((t) => t.taskState === "1");
    if (pendingTasks.length === 0) {
        console.log("所有任务已完成");
        console.log("【中国联通】：任务处理完成");
        return;
    }

    const skipTaskTypes = ["8"];
    const skippable = pendingTasks.filter((t) => skipTaskTypes.includes(t.taskType));
    const actionable = pendingTasks.filter((t) => !skipTaskTypes.includes(t.taskType));

    console.log(`共 ${uniqueTasks.length} 个任务，${pendingTasks.length} 个待完成`);
    if (skippable.length > 0) {
        const names = skippable.map((t) => t.taskName).join("、");
        console.log(`跳过 ${skippable.length} 个需手动操作的任务: ${names}`);
    }

    if (actionable.length === 0) {
        console.log("无可自动完成的任务");
        console.log("【中国联通】：任务处理完成");
        return;
    }

    let doneCount = 0;
    for (const task of actionable) {
        console.log(`处理任务: ${task.taskName} (${task.id})`);
        const completed = await completeTask(task.id);
        if (completed) {
            await getTaskReward(task.id);
            doneCount++;
        }
    }
    console.log(`任务处理完成: ${doneCount}/${actionable.length} 个成功`);
    console.log("【中国联通】：任务处理完成");
}

async function unicom() {
    let success = true;
    console.log("【中国联通】：开始签到...");
    const loginOk = await onlineLogin();
    if (!loginOk) {
        console.log("【中国联通】：登录失败，请检查cookie");
        success = false;
    } else {
        const signOk = await signboard();
        if (!signOk) {
            console.log("【中国联通】：签到失败");
            success = false;
        } else {
            const points = await getIntegral();
            if (points !== null) {
                console.log(`当前积分: ${points}`);
            }
            console.log("【中国联通】：签到完成");
        }
        if (success) {
            await processTasks();
        }
    }
    if (!success) { process.exit(1); }
}

unicom();