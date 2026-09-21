#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：七猫免费小说 app → 福利页面 → 抓包 authorization 和 qm-params
变量：ONESIGN_QMREAD_COOKIE（格式：authorization#qm-params，多账号用 @ 或换行分隔）

cron: 10 9,20 * * *
new Env('七猫小说');
"""

import json
import os
import sys
import time
import random
import requests

SCRIPT_NAME = "七猫小说"
success = True

# 随机延迟 1~30 分钟
_delay = random.randint(60, 1800)
print(f"【七猫小说】随机延迟 {_delay // 60} 分 {_delay % 60} 秒")
time.sleep(_delay)


def get_config(env_name: str) -> str:
    """获取环境变量值"""
    return os.environ.get(env_name, "")


def lucky_wheel(au: str, qm: str):
    """幸运大转盘 (5次)"""
    print("======= 开始幸运大转盘 =======")
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
                print("  幸运大转盘: " + json.loads(resp.text)["data"]["prize_title"])
            else:
                print("  今日抽奖次数已用完，请明日再来")
                break
        except Exception as e:
            print(f"  幸运大转盘请求异常: {e}")
        time.sleep(2)


def lucky_seven(au: str, qm: str):
    """幸运7抽奖 (5次)"""
    print("======= 开始幸运7抽奖 =======")
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
                print("  七猫幸运抽奖: " + json.loads(resp.text)["data"]["title"])
            else:
                errors = json.loads(resp.text).get("errors", {})
                print("  七猫幸运抽奖: " + errors.get("title", resp.text[:100]))
        except Exception as e:
            print(f"  七猫幸运抽奖请求异常: {e}")
        time.sleep(2)


def query_balance(au: str):
    """查询金币余额"""
    print("======= 查询余额 =======")
    t = str(int(time.time()))
    url = "https://api-gw.wtzw.com/welf/h5/v1/task-list"
    headers = {
        "Authorization": au,
        "Host": "api-gw.wtzw.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; 21051182C Build/N2G47H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Safari/537.36",
    }
    data = {
        "module_sign": [
            {"sign": "9fdefb36c2ec66942d79b1a9a0a8d85d", "category": "time_limit"},
            {"sign": "0d7debfbc25c2184926b23b480bd2450", "category": "daily_task"},
        ],
        "t": t,
    }
    try:
        resp = requests.post(url=url, headers=headers, json=data, timeout=30)
        jsondata = resp.json()
        coin_data = jsondata.get("user", {}).get("coin_data", "未知")
        print(f"  当前金币余额: {coin_data}")
    except Exception as e:
        print(f"  查询余额异常: {e}")


def claim_treasure_box(au: str):
    """领取宝箱奖励（需听书满180分钟）"""
    print("======= 领取宝箱 =======")
    t = str(int(time.time()))
    url = "https://api-gw.wtzw.com/welf/h5/v1/task/treasure/reward"
    headers = {
        "Authorization": au,
        "content-type": "multipart/form-data;",
        "Host": "api-gw.wtzw.com",
    }
    try:
        resp = requests.post(url=url, headers=headers, params={"t": t}, timeout=30)
        print(f"  宝箱: {resp.text[:200]}")
    except Exception as e:
        print(f"  领取宝箱异常: {e}")
    time.sleep(random.randint(1, 3))


def claim_treasure_video(au: str):
    """领取宝箱视频奖励"""
    print("======= 领取宝箱视频奖励 =======")
    t = str(int(time.time()))
    url = "https://api-gw.wtzw.com/welf/h5/v1/task/treasure/video/reward"
    headers = {
        "Authorization": au,
        "content-type": "application/json",
        "Host": "api-gw.wtzw.com",
    }
    payload = {
        "position": "welfare_treasurebox_timely",
        "video_prefix": "task_video_two",
    }
    try:
        resp = requests.post(url=url, json=payload, headers=headers, params={"t": t}, timeout=30)
        print(f"  宝箱视频: {resp.text[:200]}")
    except Exception as e:
        print(f"  领取宝箱视频异常: {e}")
    time.sleep(random.randint(1, 3))


def coin_reading_reward(au: str):
    """模拟阅读章节领取金币 (100次，每次150金币)"""
    print("======= 模拟阅读领取金币 (100次) =======")
    url = "https://api-ks.wtzw.com/api/v1/coin/add"
    headers = {
        "Authorization": au,
        "Host": "api-ks.wtzw.com",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; 21051182C Build/N2G47H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Safari/537.36",
    }
    payload = "position_id=inchapter_top&type=6&sign=1"
    earned = 0
    for i in range(100):
        try:
            resp = requests.post(url=url, data=payload, headers=headers, timeout=30)
            jsondata = resp.json()
            coin = jsondata.get("data", {}).get("coin", 0)
            times = jsondata.get("data", {}).get("times", 0)
            earned += int(coin) if coin else 0
            if (i + 1) % 20 == 0:
                print(f"  进度: {i + 1}/100, 累计: +{earned}金币, 剩余次数: {times}")
            if times == 0:
                print(f"  次数用完，共领取 +{earned} 金币")
                break
        except Exception as e:
            print(f"  阅读金币领取异常 (第{i + 1}次): {e}")
        time.sleep(random.randint(1, 3))
    print(f"  阅读金币领取完成，累计 +{earned} 金币")


def finish_rewards(au: str):
    """完成任务并领取奖励"""
    print("======= 完成任务领取奖励 =======")
    t = str(int(time.time()))
    finish_url = "https://api-gw.wtzw.com/welf/h5/v1/task/finish-task"
    reward_url = "https://api-gw.wtzw.com/welf/h5/v1/task/reward"
    headers = {
        "Authorization": au,
        "Host": "api-gw.wtzw.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 7.1.2; 21051182C Build/N2G47H; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Safari/537.36",
    }

    task_ids = [22, 24, 154, 155, 156, 157, 158, 159, 160, 100, 105, 111, 113, 115, 116, 161, 42, 43, 44, 45, 46, 47]
    done = 0

    for task_id in task_ids:
        finish_data = {"t": t, "task_id": task_id}
        reward_task_data = {"t": t, "task_id": task_id, "type_prefix": "task"}
        reward_video_data = {"t": t, "task_id": task_id, "type_prefix": "video"}

        try:
            # task_id 113 特殊处理，执行5次
            loops = 5 if task_id == 113 else 1
            for _ in range(loops):
                r1 = requests.post(url=finish_url, headers=headers, data=finish_data, timeout=30)
                time.sleep(random.randint(1, 3))
                r2 = requests.post(url=reward_url, headers=headers, data=reward_task_data, timeout=30)
                time.sleep(random.randint(1, 3))
                r3 = requests.post(url=reward_url, headers=headers, data=reward_video_data, timeout=30)
                time.sleep(random.randint(1, 3))
            done += 1
        except Exception as e:
            print(f"  任务 {task_id} 异常: {e}")

    print(f"  完成任务: {done}/{len(task_ids)} 个")


def main():
    global success
    print("【七猫小说】：开始执行...")

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
            print(f"\n----- 账号[{idx + 1}]开始执行 -----")
            parts = account.split("#")
            if len(parts) < 2:
                print(f"账号[{idx + 1}] 格式错误，需要 authorization#qm-params")
                success = False
                continue

            au = parts[0].strip()
            qm = parts[1].strip()

            try:
                # 查余额
                query_balance(au)
                time.sleep(1)

                # 幸运大转盘
                lucky_wheel(au, qm)
                time.sleep(1)

                # 幸运7抽奖
                lucky_seven(au, qm)
                time.sleep(1)

                # 领取宝箱
                claim_treasure_box(au)
                time.sleep(1)

                # 领取宝箱视频
                claim_treasure_video(au)
                time.sleep(1)

                # 完成任务领取奖励
                finish_rewards(au)
                time.sleep(1)

                # 模拟阅读领取金币 (100次)
                coin_reading_reward(au)
                time.sleep(1)

                # 再次查余额
                query_balance(au)

            except Exception as e:
                print(f"账号[{idx + 1}] 执行异常: {e}")
                success = False

            time.sleep(random.randint(2, 5))

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()