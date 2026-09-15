#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：中通快递小程序 → 我的 → 会员中心 → 抓 x-token（JWT）
变量：ONESIGN_ZTKD_TOKEN（x-token 值，多账号用 # 分隔）

cron: 0 6 * * *
new Env('中通快递小程序签到')
"""
import os
import sys
import json
import time
import base64
from datetime import date, datetime, timedelta
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "中通快递"
success = True


def decode_jwt_payload(token):
    """从 JWT token 中提取 payload"""
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.b64decode(payload).decode('utf-8')
            return json.loads(decoded)
    except Exception:
        pass
    return {}


class RUN:
    def __init__(self, info, index):
        self.token = info
        self.index = index + 1

        jwt_payload = decode_jwt_payload(self.token)
        self.oid = jwt_payload.get('openId', '')
        self.mobile = jwt_payload.get('mobile', '')
        self.userId = jwt_payload.get('userId', '')

        self.baseUrl = 'https://membergateway.zto.com/'

        self.headers = {
            'Host': 'membergateway.zto.com',
            'content-type': 'application/json',
            'x-clientCode': 'wechatMiniZtoHelper',
            'x-oid': self.oid,
            'x-sv-v': '0.22.0',
            'x-token': self.token,
            'x-version': 'V8.160.1',
            'charset': 'utf-8',
            'Referer': 'https://servicewechat.com/wx7ddec43d9d27276a/693/page-frame.html',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; RMX5062 Build/UKQ1.231108.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/150.0.7871.181 Mobile Safari/537.36 XWEB/1500047 MMWEBSDK/20260502 MMWEBID/784 MicroMessenger/8.0.76.3141(0x28004C50) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android',
        }

    def do_post(self, path, data=None):
        try:
            s = requests.session()
            s.verify = False
            response = s.post(f'{self.baseUrl}{path}', headers=self.headers, json=data or {})
            return response.json()
        except Exception as e:
            print(f"请求错误: {e}")
            return None

    def get_point(self, end=False):
        global success
        response = self.do_post('member/getMemberPoints')
        if response and response.get('success') and response.get('data'):
            data = response.get('data', {})
            point = data.get('totalPoint', 0)
            over_due = data.get('overDuePoint', 0)
            mobile = self.mobile or ''
            if mobile:
                mobile = mobile[:3] + "*" * 4 + mobile[7:]
            if end:
                print(f'执行后积分: {point}')
            else:
                print(f'当前用户: {mobile}\n当前积分: {point}' + (f' (即将过期: {over_due})' if over_due else ''))
            return True
        else:
            msg = response.get('errMessage', '') if response else '无响应'
            print(f'获取积分失败: {msg}')
            success = False
            return False

    def check_sign(self):
        print('查询签到状态...')
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        json_data = {
            "startDate": f"{week_start} 00:00:00",
            "endDate": f"{week_end} 23:59:59"
        }
        response = self.do_post('member/activity/queryRecentSign', json_data)
        if response and response.get('status') and response.get('statusCode') == 'SYS000':
            result = response.get('result', {})
            daily_list = result.get('dailyList', [])
            continuous_days = result.get('continuousDays', 0)
            today_str = str(today)

            for day in daily_list:
                if day.get('date') == today_str:
                    if day.get('isSigned'):
                        pts = day.get('pointsEarned', 0)
                        print(f'今日已签到, 连续签到{continuous_days}天, 获得{pts}积分')
                    else:
                        pts = day.get('pointsEarned', 0)
                        print(f'今日未签到, 可获{pts}积分')
                        self.sign()
                    return
            print('今日不在签到周期内')
        else:
            msg = response.get('message', '') if response else '无响应'
            print(f'查询签到失败: {msg}')

    def sign(self):
        print('执行签到...')
        today_str = str(date.today())
        json_data = {
            "signType": "TODAY_SIGN",
            "signDate": f"{today_str} 00:00:00",
            "supplementaryScene": None
        }
        response = self.do_post('member/activity/signIn', json_data)
        if response and response.get('status') and response.get('statusCode') == 'SYS000':
            result = response.get('result', {})
            pts = result.get('pointsEarned', 0)
            print(f'签到成功! 获得{pts}积分')
        else:
            msg = response.get('message', '') if response else '无响应'
            print(f'签到失败: {msg}')

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        if self.get_point():
            self.check_sign()
            self.get_point(end=True)
            return True
        return False


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_ZTKD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_ZTKD_TOKEN 变量")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        RUN(info, idx).main()
    if not success:
        notify_failure(SCRIPT_NAME, success)
        sys.exit(1)