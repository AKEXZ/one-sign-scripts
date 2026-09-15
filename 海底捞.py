#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：海底捞小程序 → 我的 → 每日签到 → 找请求头带 _HAIDILAO_APP_TOKEN 的 URL
      复制 _HAIDILAO_APP_TOKEN 的值，格式：TOKEN_APP_xxx
变量：ONESIGN_HDL_TOKEN（_HAIDILAO_APP_TOKEN，多账号用 # 或 & 分隔）

cron: 0 6 * * *
new Env('海底捞小程序签到')
"""
import os
import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "海底捞"
success = True


class RUN:
    def __init__(self, info, index):
        self.haidilao_app_token = info.strip()
        self.index = index + 1
        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'Host': 'superapp-public.kiwa-tech.com',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36 XWEB/1500047 MMWEBSDK/20260502 MMWEBID/784 MicroMessenger/8.0.76.3141(0x28004C50) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 miniProgram/wx1ddeb67115f30d1a',
            '_HAIDILAO_APP_TOKEN': self.haidilao_app_token,
            'appId': '15',
            'appName': 'HDLMember',
            'appVersion': '4.82.0',
            'content-type': 'application/json',
            'platformName': 'wechat',
            'charset': 'utf-8',
            'accept': 'application/json, text/plain, */*',
            'Origin': 'https://superapp-public.kiwa-tech.com',
            'X-Requested-With': 'com.tencent.mm',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'referer': 'https://servicewechat.com/wx1ddeb67115f30d1a/333/page-frame.html',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def do_request(self, url, method='POST', data=None, extra_headers=None):
        try:
            headers = self.headers.copy()
            if extra_headers:
                headers.update(extra_headers)
            if method == 'POST':
                response = self.s.post(url, json=data, headers=headers)
            else:
                response = self.s.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"请求错误: {e}")
            return None

    def queryMemberCacheInfo(self):
        print('>>>>>>获取用户信息')
        try:
            data = {"type": 1}
            response = self.do_request(
                'https://superapp-public.kiwa-tech.com/activity/wxapp/applet/queryMemberCacheInfo', data=data)
            if response and response.get('success'):
                data = response.get('data', {})
                customerName = data.get('customerName', '')
                mobile = data.get('mobile', '')
                if mobile and len(mobile) >= 11:
                    mobile = mobile[:3] + "****" + mobile[7:]
                coinNum = data.get('coinNum', '')
                memberLevel = data.get('memberLevel', '')
                print(f"用户名：【{customerName}】\n手机号：【{mobile}】\n等级：【{memberLevel}】\n捞币：【{coinNum}】")
                return True
            return False
        except Exception as e:
            print(f"获取用户信息异常: {e}")
            return False

    def sign_in(self):
        try:
            data = {"signinSource": "MiniApp"}
            extra_headers = {
                'referer': f"https://superapp-public.kiwa-tech.com/app-sign-in/?SignInToken={self.haidilao_app_token}&source=MiniApp",
                'ReqType': 'APPH5',
                'deviceId': 'null',
            }
            response = self.do_request(
                'https://superapp-public.kiwa-tech.com/activity/wxapp/signin/signin',
                data=data, extra_headers=extra_headers)
            if response and response.get('success'):
                print("签到成功！")
                return True
            else:
                print(f"签到失败: {response}")
                return False
        except Exception as e:
            print(f"签到异常: {e}")
            return False

    def queryFragment(self):
        try:
            extra_headers = {
                'referer': f"https://superapp-public.kiwa-tech.com/app-sign-in/?SignInToken={self.haidilao_app_token}&source=MiniApp",
                'ReqType': 'APPH5',
                'deviceId': 'null',
            }
            response = self.do_request(
                'https://superapp-public.kiwa-tech.com/activity/wxapp/signin/queryFragment',
                extra_headers=extra_headers)
            if response and response.get('success'):
                data = response.get('data', {})
                total = data.get('total', 0)
                expireDate = data.get('expireDate', '')
                print(f"碎片总数：【{total}】\n过期时间：【{expireDate}】")
                return True
            return False
        except Exception as e:
            print(f"查询碎片异常: {e}")
            return False

    def signin_query(self):
        global success
        print('>>>>>>开始签到')
        try:
            extra_headers = {
                'referer': f"https://superapp-public.kiwa-tech.com/app-sign-in/?SignInToken={self.haidilao_app_token}&source=MiniApp",
                'ReqType': 'APPH5',
                'deviceId': 'null',
            }
            response = self.do_request(
                'https://superapp-public.kiwa-tech.com/activity/wxapp/signin/query',
                extra_headers=extra_headers)
            if response and response.get('success'):
                data = response.get('data', {})
                signinOr = data.get('signinOr', 0)
                activityName = data.get('activityName', '')
                signinQueryDetailList = data.get('signinQueryDetailList', [])
                daycount = sum(1 for day in signinQueryDetailList if day.get('dailySigninStatus', 1) == 2)
                totalDays = len(signinQueryDetailList)
                print(f"活动：【{activityName}】")
                if signinOr == 1:
                    print(f"今日已签到,本期累计签到【{daycount}/{totalDays}】天")
                else:
                    print(f"今日未签到,本期累计签到【{daycount}/{totalDays}】天")
                    self.sign_in()
                self.queryFragment()
                return True
            else:
                print(f"查询签到失败: {response}")
                success = False
                return False
        except Exception as e:
            print(f"查询签到异常: {e}")
            success = False
            return False

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        self.queryMemberCacheInfo()
        self.signin_query()
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_HDL_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_HDL_TOKEN 变量")
        print("抓包获取方式：海底捞小程序 → 我的 → 每日签到 → 找请求头带 _HAIDILAO_APP_TOKEN 的 URL")
        print("复制 _HAIDILAO_APP_TOKEN 的值（格式：TOKEN_APP_xxx），填入 ONESIGN_HDL_TOKEN 变量")
        sys.exit(1)
    tokens = token.replace('&', '#').split('#')
    tokens = [t for t in tokens if t.strip()]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        RUN(info, idx).main()
    if not success:
        notify_failure(SCRIPT_NAME, success)
        sys.exit(1)