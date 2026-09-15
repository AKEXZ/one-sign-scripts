#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：韵达快递小程序 → 授权登录 → 找请求头带 Authorization 的 URL
      复制里面的 Authorization 参数值
变量：ONESIGN_YDKD_TOKEN（Authorization 值，多账号用 # 或 & 分隔）

cron: 0 6 * * *
new Env('韵达快递小程序签到')
"""
import os
import sys
import time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "韵达快递"
success = True


class RUN:
    def __init__(self, info, index):
        self.token = info
        self.index = index + 1
        self.headers = {
            'Host': 'op.yundasys.com',
            'Accept': 'application/json, text/plain, */*',
            'Authorization': self.token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF XWEB/8259',
            'Content-Type': 'application/json; charset=UTF-8',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://op.yundasys.com/mb-ext-channel/index.html',
            'Accept-Language': 'zh-CN,zh',
        }
        self.baseUrl = 'https://op.yundasys.com/gateway/ydmb-integral/ydintegral/'

    def do_request(self, url, data=None):
        try:
            s = requests.session()
            s.verify = False
            response = s.post(url, headers=self.headers, json=data or {})
            return response.json()
        except Exception as e:
            print(f"请求错误: {e}")
            return None

    def get_point(self):
        global success
        print('>>>>>>获取积分信息')
        json_data = {"channelId": "wxapp", "reqTime": int(time.time()), "accountSrc": "wxapp", "accountId": self.token}
        response = self.do_request(f'{self.baseUrl}member/integral/info', json_data)
        if response and response.get('code') == 200:
            data = response.get('data', {})
            point = data.get('total', 0)
            userId = data.get('userId', '')
            print(f'当前用户：【{userId}】\n当前积分：【{point}】')
            return True
        else:
            print('获取积分信息失败，可能token已失效')
            success = False
            return False

    def sign(self):
        print('>>>>>>签到')
        json_data = {"channelId": "wxapp", "itgType": "sign", "reqTime": int(time.time()), "accountSrc": "wxapp", "accountId": self.token}
        response = self.do_request(f'{self.baseUrl}obtain/event/integral', json_data)
        if response and response.get('code') == 200:
            print(f'签到成功，{response.get("message", "")}')
        else:
            print(f'签到: {response.get("message", "") if response else "无响应"}')

    def get_TaskList(self):
        print('>>>>>>获取任务列表')
        json_data = {"channelId": "wxapp", "pageNum": 1, "pageSize": 100, "businessType": "goldBetter",
                     "reqTime": int(time.time()), "accountSrc": "wxapp", "accountId": self.token}
        response = self.do_request(f'{self.baseUrl}integral/event/list', json_data)
        if response and response.get('message') == '请求成功':
            data = response.get('data', {})
            items = data.get('items', [])
            skip_types = ['关注公众号', '实名认证', '完善个人信息', '累计消耗积分', '寄快递', '购买超级会员', '兑换商品']
            all_done = True
            for item in items:
                eventStatus = item.get('eventStatus', '0')
                eventCode = item.get('eventCode', '')
                surplusCount = item.get('surplusCount', 0)
                title = item.get('eventName', '')
                if title in skip_types:
                    continue
                if title == '本月寄满3件':
                    surplusCount = 1
                stu = {"0": "已完成", "1": "未完成"}
                print(f'当前任务【{title}】,{stu.get(eventStatus, "未知")}')
                for _ in range(surplusCount):
                    if eventStatus == "1":
                        self.doTask(eventCode, title)
                        if title == '观看精彩视频':
                            self.watchAd(title)
                    time.sleep(1)
                if eventStatus == "1":
                    all_done = False
            if all_done:
                print("任务已全部完成")
            return True

    def watchAd(self, title):
        json_data = {"action": "ydmbintegral.ydintegral.obtain.event.integral", "appid": "wjvxmno358lze827",
                     "req_time": int(time.time()), "options": "false",
                     "data": {"accountId": self.token, "accountSrc": "wxapp", "reqTime": int(time.time()), "itgType": "wechat_viewadv"},
                     "version": "V1.0"}
        response = self.do_request(f'{self.baseUrl}obtain/event/integral', json_data)
        if response and response.get('code') == 200:
            print(f'{title},{response.get("message", "")}')
        else:
            print(f'{title},{response.get("message", "") if response else "无响应"}')

    def doTask(self, eventCode, title):
        json_data = {"channelId": "wxapp", "itgType": eventCode, "reqTime": int(time.time()), "accountSrc": "wxapp", "accountId": self.token}
        response = self.do_request(f'{self.baseUrl}obtain/event/integral', json_data)
        if response and response.get('code') == 200:
            print(f'{title},{response.get("message", "")}')
        else:
            print(f'{title},{response.get("message", "") if response else "无响应"}')

    def getDrawInfo(self):
        print('>>>>>>获取抽奖信息')
        json_data = {"reqTime": int(time.time()), "accountId": self.token, "accountSrc": "wxapp"}
        response = self.do_request('https://op.yundasys.com/gateway/ydmbaccount/ydaccount/mc/Itg/store/token', json_data)
        if response and response.get('code') == 200:
            data = response.get('data')
            if data:
                self.getDrawNumber(data)

    def getDrawNumber(self, data):
        json_data = {'activityId': 16, 'plum_session_applet': data, 'suid': 'gmrtxvrye6', 'mwl_client_flag': 'wxapp'}
        response = self.do_request('https://op.yundasys.com/itgstoresys/api/lottery/drawNumber', json_data)
        if response and response.get('code') == 200:
            freeDrawNumber = response.get('data', {}).get('freeDrawNumber', 0)
            print(f'剩余免费抽奖次数：【{freeDrawNumber}】')
            if freeDrawNumber == 1:
                self.doDraw(data)

    def doDraw(self, data):
        json_data = {'activityId': 16, 'plum_session_applet': data, 'suid': 'gmrtxvrye6', 'mwl_client_flag': 'wxapp'}
        response = self.do_request('https://op.yundasys.com/itgstoresys/api/lottery/draw', json_data)
        if response and response.get('code') == "200":
            msg = response.get('message', '')
            prizeName = response.get('data', {}).get('prizeName', '')
            print(f'{msg},获得{prizeName}')
        else:
            print(f'抽奖: {response.get("message", "") if response else "无响应"}')

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        if not self.get_point():
            return False
        self.sign()
        self.get_TaskList()
        self.getDrawInfo()
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_YDKD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_YDKD_TOKEN 变量")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        RUN(info, idx).main()
    if not success:
        sys.exit(1)