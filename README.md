# OneSign Scripts

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Scripts](https://img.shields.io/badge/scripts-22-blue)](.)

自动化每日签到脚本集，覆盖快递、网盘、生活、社区等 20+ 个平台。适配呆呆面板调度，支持多账号。

---

## 📋 脚本列表

### 快递

| 脚本 | 站点 | 环境变量 |
|------|------|---------|
| 顺丰速运.py | 顺丰速运 | `ONESIGN_SFSY_TOKEN` |
| 中通快递.py | 中通快递 | `ONESIGN_ZTKD_TOKEN` |
| 韵达快递.py | 韵达快递 | `ONESIGN_YDKD_TOKEN` |
| 极兔速递.py | 极兔速递 | `ONESIGN_JTSD_TOKEN` |
| 德邦快递.py | 德邦快递 | `ONESIGN_DBKD_TOKEN` |

### 网盘

| 脚本 | 站点 | 环境变量 |
|------|------|---------|
| 阿里云盘.js | 阿里云盘 | `ONESIGN_ALIYUN_REFRESH_TOKEN` |
| 夸克网盘.py | 夸克网盘 | `ONESIGN_KKYP_COOKIE` |

### 生活

| 脚本 | 站点 | 环境变量 |
|------|------|---------|
| 麦当劳MCP.js | 麦当劳 | `ONESIGN_MCDONALD_TOKEN` |
| 海底捞.py | 海底捞 | `ONESIGN_HDL_TOKEN` |
| 途虎养车.js | 途虎养车 | `ONESIGN_TUHU_TOKEN` |
| 捷停车.js | 捷停车 | `ONESIGN_JTC_TOKEN` |
| 维迈通多多.py | 维迈通多多 | `ONESIGN_VMTDD_TOKEN` |
| 奇瑞汽车.js | 奇瑞汽车 | `ONESIGN_CHERY_TOKEN` |
| 中国联通.js | 中国联通 | `ONESIGN_UNICOM_COOKIE` |

### 娱乐

| 脚本 | 站点 | 环境变量 |
|------|------|---------|
| 爱奇艺.py | 爱奇艺 | `ONESIGN_IQY_COOKIE` |
| 七猫抽奖.py | 七猫免费小说 | `ONESIGN_QMREAD_COOKIE` |
| ACFun签到.js | ACFun | `ONESIGN_ACFUN_COOKIE` |
| 网易云游戏.js | 网易云游戏 | `ONESIGN_CG163_AUTHORIZATION` |
| 好游快爆.js | 好游快爆 | `ONESIGN_HYKB_COOKIE` |

### 社区

| 脚本 | 站点 | 环境变量 |
|------|------|---------|
| MT论坛.js | MT 论坛 | `ONESIGN_MT_COOKIE` |
| NGA论坛.js | NGA 论坛 | `ONESIGN_NGA_UID` / `ONESIGN_NGA_ACCESSTOKEN` / `ONESIGN_NGA_UA` |

---

## 🚀 使用方式

在呆呆面板中添加对应环境变量，脚本的 `cron` 和 `new Env()` 会被自动识别调度。

也可手动运行：
```bash
python3 脚本名.py
node 脚本名.js
```

### 多账号

- Python 脚本：用 `#` 或 `&` 分隔
- Node.js 脚本：用 `@` 或换行分隔

---

## ⚠️ 免责声明

本项目仅供学习研究。使用者需自行承担一切风险，请遵守相关平台的使用条款。

---

## 📄 License

MIT License