"""
抓包：七猫免费小说 app → 福利页面 → 抓包 authorization 和 qm-params
变量：ONESIGN_QMREAD_COOKIE（格式：authorization#qm-params，多账号用 @ 或换行分隔）

cron: 0 9,21 * * *
new Env('七猫抽奖');
"""

import json
import os
import sys
import time
import requests

SCRIPT_NAME = "七猫抽奖"
success = True


def get_config(env_name: str) -> str:
    """获取环境变量值"""
    return os.environ.get(env_name, "")


def lucky_wheel(au: str, qm: str):
    """幸运大转盘"""
    for i in range(5):
        url = (
            "https://xiaoshuo.wtzw.com/api/v2/lucky-draw/do-extracting"
            + "?activity_id=0&version=2021010401&apiVersion=20190309143259-1.9&t="
            + str(int(time.time()))
        )
        headers = {
            "Host": "xiaoshuo.wtzw.com",
            "accept": "application/json, text/plain, */*",
            "user-agent": "Mozilla/5.0 (Linux; Android 7.1.2; 21051182C Build/N2G47H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Safari/537.36 webviewversion/71700 webviewpackagename/com.kmxs.reader",
            "x-requested-with": "com.kmxs.reader",
            "referer": "https://xiaoshuo.wtzw.com/app-h5/freebook/wheelSurf?activity_id=0",
            "accept-encoding": "gzip, deflate",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "authorization": au,
            "qm-params": qm,
        }
        try:
            resp = requests.get(url=url, headers=headers, timeout=30)
            if "金币" in resp.text:
                print("幸运大转盘: " + json.loads(resp.text)["data"]["prize_title"])
            else:
                print("今日抽奖次数已用完，请明日再来")
        except Exception as e:
            print(f"幸运大转盘请求异常: {e}")
        time.sleep(2)


def lucky_seven(au: str, qm: str):
    """幸运7抽奖"""
    url = "https://api-gw.wtzw.com/lucky-seven/h5/v1/lottery"
    headers = {
        "Host": "api-gw.wtzw.com",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://xiaoshuo.wtzw.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; 21051182C Build/N2G47H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045435 Safari/537.36 webviewversion/71700 webviewpackagename/com.kmxs.reader",
        "Referer": "https://xiaoshuo.wtzw.com/app-h5/freebook/lucky7/index?enable_close=1",
        "authorization": au,
        "qm-params": qm,
    }
    ds = [0, 2, 5, 1, 3]
    for jk in ds:
        data = {
            "source": str(jk),
            "apiVersion": "20190309143259-1.9",
            "t": str(int(time.time())),
        }
        try:
            resp = requests.post(url=url, headers=headers, data=data, timeout=30)
            if "data" in resp.text:
                print("七猫幸运抽奖: " + json.loads(resp.text)["data"]["title"])
            else:
                print("七猫幸运抽奖: " + json.loads(resp.text)["errors"]["title"])
        except Exception as e:
            print(f"七猫幸运抽奖请求异常: {e}")
        time.sleep(2)


def main():
    global success
    print("【七猫小说】：开始抽奖...")

    dvm = get_config("ONESIGN_QMREAD_COOKIE")
    if not dvm:
        print("【七猫小说】：未配置 ONESIGN_QMREAD_COOKIE 变量")
        success = False
    else:
        # 分割多账号
        if "@" in dvm:
            accounts = dvm.split("@")
        elif "&" in dvm:
            accounts = dvm.split("&")
        else:
            accounts = dvm.split("\n")

        accounts = [a.strip() for a in accounts if a.strip()]

        for idx, account in enumerate(accounts):
            print(f"----- 账号[{idx + 1}]开始执行 -----")
            parts = account.split("#")
            if len(parts) < 2:
                print(f"账号[{idx + 1}] 格式错误，需要 authorization#qm-params")
                success = False
                continue

            au = parts[0].strip()
            qm = parts[1].strip()

            try:
                lucky_wheel(au, qm)
                time.sleep(2)
                lucky_seven(au, qm)
            except Exception as e:
                print(f"账号[{idx + 1}] 执行异常: {e}")
                success = False

            time.sleep(2)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()