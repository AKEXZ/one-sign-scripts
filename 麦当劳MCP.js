/*
抓包：麦当劳 app 登录后，抓包工具 → 任意 API 请求
      找到 Request Headers 中的 Authorization 字段（Bearer xxx），复制整段
变量：ONESIGN_MCDONALD_TOKEN

cron: 0 9 * * *
new Env('麦当劳领券');
*/

const axios = require("axios");
const SCRIPT_NAME = "麦当劳";
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

const token = getConfig("mcdonald.token", "ONESIGN_MCDONALD_TOKEN");
const baseURL = "https://mcp.mcd.cn/mcp-servers/mcd-mcp";

function request(toolName, args = {}) {
    return new Promise(async (resolve, reject) => {
        try {
            const headers = {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            };

            const requestBody = {
                jsonrpc: "2.0",
                id: Date.now(),
                method: "tools/call",
                params: {
                    name: toolName,
                    arguments: args
                }
            };

            const res = await axios.post(baseURL, requestBody, { headers });

            if (res.data && res.data.result) {
                resolve(res.data.result);
            } else if (res.data && res.data.error) {
                reject(new Error(res.data.error.message || "请求失败"));
            } else {
                resolve(res.data);
            }
        } catch (err) {
            reject(err);
        }
    });
}

function parseTextContent(toolResult) {
    if (!toolResult || !toolResult.content) return "";
    const textContent = toolResult.content.find(item => item.type === "text");
    return textContent ? textContent.text : "";
}

function stripImages(text) {
    return text.replace(/<img[^>]*>/g, "").replace(/\n{3,}/g, "\n\n").trim();
}

async function listTools() {
    try {
        const headers = {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        };
        const res = await axios.post(baseURL, {
            jsonrpc: "2.0",
            id: Date.now(),
            method: "tools/list",
            params: {}
        }, { headers });
        if (res.data && res.data.result && res.data.result.tools) {
            return res.data.result.tools;
        }
        return [];
    } catch (err) {
        return [];
    }
}

async function getAvailableCoupons() {
    try {
        const res = await request("available-coupons");
        return res;
    } catch (err) {
        console.log("查询优惠券列表失败: " + err.message);
        return null;
    }
}

async function autoBindCoupons() {
    try {
        const res = await request("auto-bind-coupons");
        return res;
    } catch (err) {
        console.log("一键领券失败: " + err.message);
        return null;
    }
}

async function getMyCoupons() {
    try {
        const res = await request("query-my-coupons");
        return res;
    } catch (err) {
        console.log("查询我的优惠券失败: " + err.message);
        return null;
    }
}

async function getCampaignCalendar(specifiedDate = null) {
    try {
        const args = specifiedDate ? { specifiedDate } : {};
        const res = await request("campaign-calender", args);
        return res;
    } catch (err) {
        console.log("查询活动日历失败: " + err.message);
        return null;
    }
}

async function mcdonald() {
    let success = true;
    console.log("【麦当劳】：开始领券...");

    try {
        // 0. 列出所有可用 MCP 工具
        const tools = await listTools();
        if (tools.length > 0) {
            const toolNames = tools.map(t => t.name).join(", ");
            console.log(`MCP 可用工具 (${tools.length}): ${toolNames}`);
        }

        // 1. 查询可领取的优惠券
        const availableCoupons = await getAvailableCoupons();
        if (availableCoupons) {
            const availableText = parseTextContent(availableCoupons);

            // 提取所有券名
            const nameMatches = availableText.match(/优惠券标题：(.+?)(?:\s*\\\s*|\s*$)/g);
            const couponNames = [];
            if (nameMatches) {
                for (const m of nameMatches) {
                    const n = m.match(/优惠券标题：(.+)/);
                    if (n) couponNames.push(n[1].trim().replace(/\\$/, ""));
                }
            }

            const unreceivedMatches = availableText.match(/状态：可领取/g);
            const unreceivedCount = unreceivedMatches ? unreceivedMatches.length : 0;

            if (unreceivedCount > 0) {
                console.log(`\n可领取优惠券 (${unreceivedCount}张):`);
                couponNames.forEach((n, i) => console.log(`  ${i + 1}. ${n}`));

                console.log("\n正在一键领取...");
                const bindResult = await autoBindCoupons();
                if (bindResult) {
                    const bindText = parseTextContent(bindResult);

                    // 提取成功/失败统计
                    const totalMatch = bindText.match(/总计:\s*(\d+)\s*张/);
                    const successMatch = bindText.match(/成功:\s*(\d+)\s*张/);
                    const failMatch = bindText.match(/失败:\s*(\d+)\s*张/);

                    if (totalMatch && successMatch) {
                        console.log(`\n领券结果: ${successMatch[1]}/${totalMatch[1]} 成功` + (failMatch && failMatch[1] !== "0" ? `, ${failMatch[1]} 失败` : ""));

                        // 提取每张券的 couponId/couponCode
                        const sections = bindText.split(/####\s+/);
                        for (const sec of sections) {
                            const nameM = sec.match(/^\s*\**(.+?)\**\s*$/m);
                            const idM = sec.match(/couponId[：:]\s*(\S+)/);
                            const codeM = sec.match(/couponCode[：:]\s*(\S+)/);
                            if (nameM && nameM[1].trim() && idM) {
                                console.log(`  ✅ ${nameM[1].trim()}  ${codeM ? codeM[1] : ""}`);
                            }
                        }
                    } else {
                        console.log(stripImages(bindText));
                    }
                }
            } else {
                console.log("暂无可领取的新优惠券");
            }
        }

        // 2. 查询我的优惠券
        const myCoupons = await getMyCoupons();
        if (myCoupons) {
            const myText = parseTextContent(myCoupons);
            const totalMatch = myText.match(/共\s*(\d+)\s*张/);
            const totalCount = totalMatch ? totalMatch[1] : "?";

            // 提取每张券的关键信息
            const sections = myText.split(/^##\s+/m).filter(s => s.trim());
            console.log(`\n我的优惠券 (共${totalCount}张):`);
            for (const sec of sections) {
                const nameM = sec.match(/^([^\n]+)/);
                const priceM = sec.match(/优惠[：:]\s*(.+?)(?:\s*$)/m);
                const validM = sec.match(/有效期[：:]\s*(.+?)(?:\s*$)/m);
                const tagM = sec.match(/标签[：:]\s*(.+?)(?:\s*$)/m);
                if (nameM) {
                    const name = nameM[1].trim();
                    const price = priceM ? priceM[1].trim() : "";
                    const valid = validM ? validM[1].trim() : "";
                    const tags = tagM ? tagM[1].trim() : "";
                    console.log(`  🎫 ${name}  ${price}  ${tags}`);
                }
            }
        }
    } catch (err) {
        console.log("执行失败: " + err.message);
        success = false;
    }

    if (!success) { process.exit(1); }
}

mcdonald();