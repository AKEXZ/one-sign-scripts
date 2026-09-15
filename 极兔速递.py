#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：极兔速递小程序 → 授权登录 → 找请求头带 authtoken 的 URL
      复制 authtoken 参数值
变量：ONESIGN_JTSD_TOKEN（authtoken 值，多账号用 # 或 & 分隔）

cron: 0 6 * * *
new Env('极兔速递小程序签到')
"""
import os
import sys
import time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "极兔速递"
success = True


class RUN:
    def __init__(self, info, index):
        self.token = info
        self.index = index + 1
        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            "Host": "applets.jtexpress.com.cn",
            "authtoken": self.token,
            "xweb_xhr": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x6309080f) XWEB/8555",
            "content-type": "application/json;charset=UTF-8",
            "accept": "*/*",
            "sec-fetch-site": "cross-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://servicewechat.com/wxe37801988179d0a5/316/page-frame.html",
            "accept-language": "zh-CN,zh;q=0.9"
        }
        self.baseUrl = 'https://applets.jtexpress.com.cn/'

    def qureyMyselfGrow(self):
        global success
        print('>>>>>>获取用户信息')
        response = self.s.get(f'{self.baseUrl}/applets/user/qureyMyselfGrow?', headers=self.headers)
        data_info = response.json()
        if data_info.get('succ', False):
            data = data_info.get('data', {})
            mobile = data.get('mobile', '')
            mobile = mobile[:3] + "*" * 4 + mobile[7:]
            memberId = data.get('memberId', '')
            growValue = data.get('growValue', '')
            nextStartGrow = data.get('nextStartGrow', '')
            print(f"账号[{self.index}]登录成功！\n手机号：【{mobile}】\n用户ID：【{memberId}】\n成长值：【{growValue}/{nextStartGrow}】")
            return True
        else:
            print('获取用户信息失败，可能token已失效')
            success = False
            return False

    def addActionRecord(self):
        print('>>>>>>进入签到详情')
        json_data = {
            "eventTimestamp": int(time.time() * 1000),
            "pagePath": "packageA/signIn/index",
            "reportAddress": "",
            "reportLocation": "",
            "phoneModel": "microsoft",
            "eventType": "enter_signIn",
            "elementContent": "",
            "elementEventName": "进入签到详情",
            "elementCode": 2
        }
        response = self.s.post(f'{self.baseUrl}/applets/user/addActionRecord', headers=self.headers, json=json_data)
        return response.json().get('succ', False)

    def sign(self):
        print('>>>>>>开始签到')
        response = self.s.post(f'{self.baseUrl}/applets/user/sign', headers=self.headers, json={})
        data_info = response.json()
        if data_info.get('succ', False):
            day = data_info.get('data', {}).get('day', '')
            print(f"签到成功！累计签到【{day}】天")
            return True
        else:
            print(f"签到失败: {data_info.get('msg', '')}")
            return False

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        if self.qureyMyselfGrow():
            self.addActionRecord()
            self.sign()
            return True
        return False


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_JTSD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_JTSD_TOKEN 变量")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        RUN(info, idx).main()
    if not success:
        notify_failure(SCRIPT_NAME, success)
        sys.exit(1)