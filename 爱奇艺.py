#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖：pip install fake-useragent
抓包：爱奇艺 app → 我的 → 签到 → 抓包获取 cookie
      需包含 P00001、P00003、QC005、__dfp 字段
变量：ONESIGN_IQY_COOKIE（完整 cookie 值，多账号用 # 或 & 分隔）

cron: 25 6,12,18 * * *
new Env('爱奇艺签到')
"""
import os
import sys
import json
import time
from hashlib import md5
from random import randint, choice
from string import digits, ascii_lowercase, ascii_uppercase
from uuid import uuid4
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from re import findall

try:
    from fake_useragent import UserAgent
except ImportError:
    print("缺少依赖，请运行: pip install fake-useragent")
    sys.exit(1)

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "爱奇艺"
success = True


def extract_cookie_field(cookie, field):
    found = findall(rf"{field}=(.*?)(;|$)", cookie)
    if found:
        return found[0][0]
    return ""


class IQiYi:
    def __init__(self, cookie, index):
        self.index = index + 1
        self.cookie = cookie
        self.P00001 = extract_cookie_field(cookie, "P00001")
        self.userId = extract_cookie_field(cookie, "P00003")
        self.dfp = extract_cookie_field(cookie, "__dfp").split("@")[0]
        self.qyid = extract_cookie_field(cookie, "QC005")
        self.platform = str(uuid4())[:16]
        self.session = requests.session()
        self.session.verify = False
        self.user_agent = UserAgent().chrome
        self.headers = {
            "User-Agent": self.user_agent,
            "Cookie": f"P00001={self.P00001}",
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            'accept-language': "zh-CN,zh-Hans;q=0.9",
        }
        self.task_info = ""
        self.taskList = []
        self.lotteryList = []

    def req(self, url, method="GET", body=None):
        try:
            if method == "GET":
                response = self.session.get(url, headers=self.headers, params=body)
            elif method == "POST":
                response = self.session.post(url, headers=self.headers, data=json.dumps(body))
            elif method == "OTHER":
                response = self.session.get(url, headers=self.headers, params=body)
            if method in ["GET", "POST"]:
                return response.json()
        except Exception as e:
            print(f"请求发送失败: {e}")
        return {}

    def timestamp(self, short=False):
        return int(time.time()) if short else int(time.time() * 1000)

    def md5_str(self, s):
        return md5(s.encode(encoding='utf-8')).hexdigest()

    def uuid(self, num, upper=False):
        chars = digits + ascii_lowercase + (ascii_uppercase if upper else '')
        return ''.join(choice(chars) for _ in range(num))

    def sign(self):
        global success
        time_stamp = self.timestamp()
        data = f'agenttype=20|agentversion=15.5.5|appKey=lequ_rn|appver=15.5.5|authCookie={self.P00001}|qyid={self.qyid}|srcplatform=20|task_code=natural_month_sign|timestamp={time_stamp}|userId={self.userId}|cRcFakm9KSPSjFEufg3W'
        url = f'https://community.iqiyi.com/openApi/task/execute?task_code=natural_month_sign&timestamp={time_stamp}&appKey=lequ_rn&userId={self.userId}&authCookie={self.P00001}&agenttype=20&agentversion=15.5.5&srcplatform=20&appver=15.5.5&qyid={self.qyid}&sign={self.md5_str(data)}'
        headers = {'Content-Type': 'application/json'}
        body = {
            "natural_month_sign": {
                "verticalCode": "iQIYI", "agentVersion": "15.4.6", "authCookie": self.P00001,
                "taskCode": "iQIYI_mofhr", "dfp": self.dfp, "qyid": self.qyid, "agentType": 20, "signFrom": 1
            }
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            data = response.json()
            if data.get('code') == 'A0003':
                print("cookie已失效，请重新获取")
                success = False
                return
            elif data.get('code') == 'A00000':
                d = data.get('data', {})
                msg = d.get('msg', '')
                sign_days = d.get('data', {}).get('signDays')
                if msg and '已经到达上限' in msg:
                    print("签到失败，今天已签到")
                elif sign_days is not None:
                    print(f"签到成功, 本月累计签到{sign_days}天")
                elif d.get('code') != 'A0000' and d.get('code') != 'A0014':
                    print(f"签到失败: {msg}")
            else:
                print(f"签到失败: {data}")
        except Exception as e:
            print(f"签到异常: {e}")

    def dailyTask(self):
        url = f'https://tc.vip.iqiyi.com/taskCenter/task/queryUserTask?P00001={self.P00001}'
        data = self.req(url)
        if data.get('code') == 'A00000':
            for item in data.get("data", {}).get("tasks", {}).get("daily", []):
                if item["taskCode"] != "WatchVideo60mins" and item["status"] != 1:
                    self.taskList.append({
                        "taskTitle": item["taskTitle"],
                        "taskCode": item["taskCode"],
                        "status": item["status"]
                    })
        if self.taskList:
            for item in self.taskList:
                if item["status"] == 2:
                    url = f'https://tc.vip.iqiyi.com/taskCenter/task/joinTask?P00001={self.P00001}&taskCode={item["taskCode"]}&platform={self.platform}&lang=zh_CN&app_lm=cn'
                    self.req(url)
                    time.sleep(3)
                    url = f'https://tc.vip.iqiyi.com/taskCenter/task/notify?taskCode={item["taskCode"]}&P00001={self.P00001}&platform={self.platform}&lang=cn&bizSource=component_browse_timing_tasks&_={self.timestamp()}'
                    self.req(url)
                    time.sleep(1)
                if item["status"] in [2, 0]:
                    url = f"https://tc.vip.iqiyi.com/taskCenter/task/getTaskRewards?P00001={self.P00001}&taskCode={item['taskCode']}&lang=zh_CN&platform={self.platform}"
                    data = self.req(url)
                    if data.get('code') == 'A00000':
                        price = data.get('dataNew', [{}])[0].get("value", "0")
                        print(f"{item['taskTitle']}任务已完成, 获得{int(price[1:])}点成长值")
                        time.sleep(2)
        else:
            print("今日日常浏览任务已全部完成")

    def lottery(self):
        url = "https://iface2.iqiyi.com/aggregate/3.0/lottery_activity"
        params = {
            "app_k": 0, "app_v": 0, "platform_id": 10, "dev_os": 0, "dev_ua": 0, "net_sts": 0,
            "qyid": self.qyid, "psp_uid": self.userId, "psp_cki": self.P00001,
            "psp_status": 3, "secure_v": 1, "secure_p": 0, "req_sn": self.timestamp()
        }
        data = self.req(url, "GET", params)
        if data.get("code") == 0:
            daysurpluschance = int(data.get("daysurpluschance", 0))
            if daysurpluschance == 0:
                if self.lotteryList:
                    print(f"抽奖奖品：{'、'.join(self.lotteryList)}")
                else:
                    print("抽奖次数已用完, 明日再来吧")
            else:
                award_info = data.get("awardName", "")
                self.lotteryList.append(award_info)
                time.sleep(1)
                self.lottery()
        else:
            print(f"抽奖接口请求失败: {data}")

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        if not self.P00001 or not self.userId:
            print("cookie解析失败，请检查 P00001 和 P00003 字段")
            success = False
            return False
        print(">>>>>>签到")
        self.sign()
        print(">>>>>>日常任务")
        self.dailyTask()
        print(">>>>>>抽奖")
        self.lottery()
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_IQY_COOKIE', '')
    if not token:
        print("未配置 ONESIGN_IQY_COOKIE 变量")
        print("依赖：pip install fake-useragent")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        IQiYi(info, idx).main()
    if not success:
        notify_failure(SCRIPT_NAME, success)
        sys.exit(1)