#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包步骤：
  1. 打开抓包工具
  2. 打开德邦快递小程序 → 授权登录
  3. 在抓包中找任意带 ECO_TOKEN Cookie 的请求（如 /gwapi/onlineService/...）
  4. 复制 Cookie 中 ECO_TOKEN= 后面的值（不含 ECO_TOKEN= 前缀）
  ⚠️ 抓完包后不要重新打开小程序，否则 ECO_TOKEN 会失效
变量：ONESIGN_DBKD_TOKEN（ECO_TOKEN 值，多账号用 # 分隔）

cron: 0 6 * * *
new Env('德邦快递小程序签到')
"""
import os
import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "德邦快递"
success = True


class RUN:
    def __init__(self, info, index):
        self.token = info
        self.index = index + 1
        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x6309080f) XWEB/9079',
            'Cookie': f'ECO_TOKEN={self.token};',
            'Referer': 'https://servicewechat.com/wxa1ebeeb0ed47f0b2/633/page-frame.html'
        }
        self.phone = ''
        self.mobile = ''

    def do_request(self, method, url, data=None):
        try:
            if method == 'POST':
                response = self.s.post(url, json=data, headers=self.headers)
            else:
                response = self.s.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"请求错误: {e}")
            return None

    def queryUserInfo(self):
        """用 ECO_TOKEN 直接验证用户身份，不需要走 WeChat code 登录"""
        try:
            self.headers['Content-Type'] = 'application/json'
            self.headers['Accept'] = '*/*'
            response = self.do_request('GET',
                                       'https://www.deppon.com/gwapi/userService/eco/user/secure/queryUserInfo')
            if response and response.get('message') == 'ok':
                result = response.get('result', {})
                phone = result.get('mobile', '')
                self.mobile = phone[:3] + "*" * 4 + phone[7:]
                userName = result.get('userName', '')
                print(f"用户名：【{userName}】")
                print(f"手机号：【{self.mobile}】")
                return True
            else:
                print(f"用户验证失败: {response.get('message', response)}")
                return False
        except Exception as e:
            print(f"用户验证异常: {e}")
            return False

    def generate_tmp_token(self):
        try:
            response = self.do_request('GET',
                                       'https://www.deppon.com/gwapi/userService/eco/user/token/secure/generateTmpToken')
            if response and response.get('status') == 'success':
                print('临时Token获取成功！')
                return self.login_verify(response['result'])
            else:
                print(f"获取临时token失败: {response}")
                return False
        except Exception as e:
            print(f"获取临时token异常: {e}")
            return False

    def login_verify(self, code):
        try:
            data = {'code': code, 'flag': True}
            self.headers['Content-Type'] = 'application/json'
            response = self.do_request('POST', 'https://mas.deppon.com/crm-api/login/verify', data=data)
            if response and response.get('code') == 200:
                print("登录验证成功！")
                data = response.get('data', {})
                self.token = data.get('token', '')
                self.phone = data.get('mobile', '')
                self.headers['token'] = self.token
                self.headers['mobile'] = self.phone
                return True
            else:
                print(f"登录验证失败: {response}")
                return False
        except Exception as e:
            print(f"登录验证异常: {e}")
            return False

    def getSvipNewestInfo(self):
        print('获取用户最新信息------>>>')
        try:
            response = self.do_request('GET',
                                       'https://www.deppon.com/gwapi/memberService/eco/member/grade/secure/getSvipNewestInfo')
            if response and response.get('status') == "success":
                data = response.get('result', {})
                points = data.get('points', 0)
                print(f"积分：【{points}】")
                return True
            else:
                print(f"获取用户信息失败: {response}")
                return False
        except Exception as e:
            print(f"获取用户信息异常: {e}")
            return False

    def signIn_info(self):
        global success
        print('获取签到信息------>>>')
        try:
            data = {"phone": self.phone}
            response = self.do_request('POST', 'https://mas.deppon.com/crm-api/deppon/signIn/info', data=data)
            if response and response.get('code') == 200:
                data = response.get('data', {})
                is_sign_in = data.get('isSignIn')
                sign_in_day = data.get('signInDay')
                record_dtos = data.get('recordDTOS')
                if not is_sign_in and record_dtos and record_dtos[0]:
                    self.taskRuleId = record_dtos[0].get('taskRuleId', '')
                    self.signIn()
                else:
                    print(f"今天已签到, 已签到{sign_in_day}天")
                return True
            else:
                print(f"获取签到信息失败: {response}")
                success = False
                return False
        except Exception as e:
            print(f"获取签到信息异常: {e}")
            success = False
            return False

    def signIn(self):
        print('执行签到------>>>')
        try:
            data = {"phone": self.phone, 'taskRuleId': self.taskRuleId}
            response = self.do_request('POST', 'https://mas.deppon.com/crm-api/deppon/signIn', data=data)
            if response and response.get('code') == 200:
                data = response.get('data', [])
                remarks = [item['remark'] for item in data if item.get('remark')]
                remarks_str = ', '.join(remarks) if remarks else ''
                print(f"签到成功: {remarks_str}")
            else:
                print(f"签到失败: {response}")
        except Exception as e:
            print(f"签到异常: {e}")

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        if self.queryUserInfo():
            self.generate_tmp_token()
            self.getSvipNewestInfo()
            self.signIn_info()
            self.getSvipNewestInfo()
            return True
        else:
            success = False
            return False


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_DBKD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_DBKD_TOKEN 变量")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        RUN(info, idx).main()
    if not success:
        notify_failure(SCRIPT_NAME, success)
        sys.exit(1)