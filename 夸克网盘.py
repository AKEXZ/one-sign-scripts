#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：浏览器打开 https://pan.quark.cn/ 并登录
      复制全部 cookie
变量：ONESIGN_KKYP_COOKIE（cookie 值，多账号用 # 或 & 分隔）

cron: 0 2 * * *
new Env('夸克网盘签到')
"""
import os
import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "夸克网盘"
success = True


class RUN:
    def __init__(self, info, index):
        self.cookie = info
        self.index = index + 1
        self.s = requests.session()
        self.s.verify = False

    def get_account_info(self):
        url = "https://pan.quark.cn/account/info"
        querystring = {"fr": "pc", "platform": "pc"}
        headers = {"content-type": "application/json", "cookie": self.cookie}
        response = self.s.get(url=url, headers=headers, params=querystring).json()
        if response.get("data"):
            return response["data"]
        return False

    def get_growth_info(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        headers = {"content-type": "application/json", "cookie": self.cookie}
        response = self.s.get(url=url, headers=headers, params=querystring).json()
        if response.get("data"):
            return response["data"]
        return False

    def get_growth_sign(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"sign_cyclic": True}
        headers = {"content-type": "application/json", "cookie": self.cookie}
        response = self.s.post(url=url, json=payload, headers=headers, params=querystring).json()
        if response.get("data"):
            return True, response["data"]["sign_daily_reward"]
        return False, response.get("message", "")

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")
        account_info = self.get_account_info()
        if not account_info:
            print(f"账号[{self.index}]登录失败，cookie无效")
            success = False
            return False
        print(f"用户名: {account_info.get('nickname', '')}")
        growth_info = self.get_growth_info()
        if growth_info:
            cap_sign = growth_info.get("cap_sign", {})
            if cap_sign.get("sign_daily"):
                print(f"今日已签到+{int(cap_sign.get('sign_daily_reward', 0) / 1024 / 1024)}MB，连签进度({cap_sign.get('sign_progress', 0)}/{cap_sign.get('sign_target', 0)})")
            else:
                sign_ok, sign_return = self.get_growth_sign()
                if sign_ok:
                    print(f"今日签到+{int(sign_return / 1024 / 1024)}MB，连签进度({cap_sign.get('sign_progress', 0) + 1}/{cap_sign.get('sign_target', 0)})")
                else:
                    print(f"签到失败: {sign_return}")
                    success = False
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_KKYP_COOKIE', '')
    if not token:
        print("未配置 ONESIGN_KKYP_COOKIE 变量")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")
    for idx, info in enumerate(tokens):
        RUN(info, idx).main()
    if not success:
        notify_failure(SCRIPT_NAME, success)
        sys.exit(1)