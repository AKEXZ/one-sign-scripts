#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包步骤（仅首次或 token 全部过期时）：
  1. 打开抓包工具
  2. 打开德邦快递小程序 → 授权登录
  3. 在抓包中找任意带 ECO_TOKEN Cookie 的请求（如 /gwapi/onlineService/...）
  4. 复制 Cookie 中 ECO_TOKEN= 后面的值（不含 ECO_TOKEN= 前缀）
  ⚠️ 抓完包后不要重新打开小程序，否则 ECO_TOKEN 会失效

Token 持久化：
  首次运行后，login_verify 拿到的 CRM token 会保存到 .dbkd_crm_tokens.json，
  后续运行优先用 CRM token，过期后才走 ECO_TOKEN → generateTmpToken 流程。
  仅当 ECO_TOKEN 和 CRM token 都过期时才需要重新抓包。

变量：ONESIGN_DBKD_TOKEN（ECO_TOKEN 值，多账号用 # 分隔）

cron: 0 6 * * *
new Env('德邦快递小程序签到')
"""
import json
import os
import sys
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 随机延迟 1~30 分钟
import random
_delay = random.randint(60, 1800)
print(f"【德邦快递】随机延迟 {_delay // 60} 分 {_delay % 60} 秒")
time.sleep(_delay)

SCRIPT_NAME = "德邦快递"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIE_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == 'scripts' else SCRIPT_DIR
CRM_TOKEN_FILE = os.path.join(COOKIE_DIR, ".dbkd_crm_tokens.json")
success = True


def load_crm_tokens():
    """加载持久化的 CRM token，返回 list[dict]"""
    try:
        if os.path.exists(CRM_TOKEN_FILE):
            with open(CRM_TOKEN_FILE, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"[Token] 读取 CRM token 文件失败: {e}")
    return []


def save_crm_tokens(all_tokens):
    """保存所有账号的 CRM token"""
    try:
        with open(CRM_TOKEN_FILE, 'w') as f:
            json.dump(all_tokens, f, ensure_ascii=False, indent=2)
        print(f"[Token] 已保存 {len(all_tokens)} 个账号的 CRM token")
    except IOError as e:
        print(f"[Token] 保存 CRM token 失败: {e}")


class RUN:
    def __init__(self, info, index, saved_crm=None):
        self.eco_token = info.strip()
        self.index = index + 1
        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x6309080f) XWEB/9079',
            'Cookie': f'ECO_TOKEN={self.eco_token};',
            'Referer': 'https://servicewechat.com/wxa1ebeeb0ed47f0b2/633/page-frame.html'
        }
        self.phone = ''
        self.mobile = ''
        self.crm_token = ''
        self._saved_crm = saved_crm or {}

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

    def try_crm_token(self):
        """尝试用已保存的 CRM token 直接签到，跳过 ECO_TOKEN 流程"""
        crm_token = self._saved_crm.get('crm_token', '')
        phone = self._saved_crm.get('phone', '')
        if not crm_token or not phone:
            print("无已保存的 CRM token，走完整登录流程")
            return False

        self.crm_token = crm_token
        self.phone = phone
        self.headers['token'] = crm_token
        self.headers['mobile'] = phone
        self.headers['channel'] = 'WECHAT_MINI'

        print("尝试用已保存的 CRM token...")
        if not self._try_signin_flow():
            print("⚠️ CRM token 已过期，走 ECO_TOKEN 重新登录")
            self.crm_token = ''
            self.phone = ''
            self.headers.pop('token', None)
            self.headers.pop('mobile', None)
            self.headers.pop('channel', None)
            return False

        print("✅ CRM token 有效！")
        return True

    def queryUserInfo(self):
        """用 ECO_TOKEN 验证用户身份"""
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
                msg = response.get('message', str(response)) if response else '无响应'
                print(f"用户验证失败 (ECO_TOKEN 可能已过期): {msg}")
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
            self.headers['channel'] = 'WECHAT_MINI'
            response = self.do_request('POST', 'https://mas.deppon.com/crm-api/login/verify', data=data)
            if response and response.get('code') == 200:
                print("登录验证成功！")
                data = response.get('data', {})
                self.crm_token = data.get('token', '')
                self.phone = data.get('mobile', '')
                self.headers['token'] = self.crm_token
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

    def _try_signin_flow(self):
        """仅用 CRM token 执行签到流程（memberactivity 接口），返回是否成功"""
        print('获取签到状态------>>>')
        try:
            self.headers['channel'] = 'WECHAT_MINI'
            data = {"phone": self.phone, "label": "WELFARE_MEMBER_SPECIAL"}
            response = self.do_request('POST',
                                       'https://mas.deppon.com/crm-api/pay/memberactivity/getSigninStatus',
                                       data=data)
            if response and response.get('code') == 200:
                resp_data = response.get('data', {})
                today_signin = resp_data.get('todaySignin', True)
                continuous_days = resp_data.get('continuousSigninDays', 0)
                if not today_signin:
                    return self._do_sign()
                else:
                    print(f"今天已签到, 连续签到{continuous_days}天")
                    return True
            else:
                print(f"获取签到状态失败 (token 可能已过期): {response}")
                return False
        except Exception as e:
            print(f"获取签到状态异常: {e}")
            return False

    def signIn_info(self):
        global success
        result = self._try_signin_flow()
        if not result:
            success = False
        return result

    def _do_sign(self):
        print('执行签到------>>>')
        try:
            self.headers['channel'] = 'WECHAT_MINI'
            data = {"phone": self.phone, "label": "WELFARE_MEMBER_SPECIAL"}
            response = self.do_request('POST',
                                       'https://mas.deppon.com/crm-api/pay/memberactivity/signin',
                                       data=data)
            if response and response.get('code') == 200:
                print("签到成功！")
                return True
            else:
                print(f"签到失败: {response}")
                return False
        except Exception as e:
            print(f"签到异常: {e}")
            return False

    def get_crm_for_save(self):
        """导出当前 CRM token 用于持久化"""
        if self.crm_token and self.phone:
            return {'crm_token': self.crm_token, 'phone': self.phone}
        return {}

    def main(self):
        global success
        print(f"\n---------开始执行第{self.index}个账号>>>>>")

        # 1) 优先尝试已保存的 CRM token
        if self.try_crm_token():
            self.getSvipNewestInfo()
            return True

        # 2) CRM token 不可用，走完整 ECO_TOKEN 流程
        if not self.queryUserInfo():
            success = False
            print("ECO_TOKEN 已过期或无效，请重新抓包获取新的 ECO_TOKEN")
            print("   小程序: 德邦快递 → 授权登录 → 复制 Cookie 中的 ECO_TOKEN 值")
            return False
        if not self.generate_tmp_token():
            success = False
            print("临时 token 获取失败，请重新抓包获取新的 ECO_TOKEN")
            return False
        self.getSvipNewestInfo()
        self.signIn_info()
        self.getSvipNewestInfo()
        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_DBKD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_DBKD_TOKEN 变量")
        print("抓包获取: 德邦快递小程序 → 授权登录 → 复制 Cookie 中的 ECO_TOKEN 值")
        sys.exit(1)
    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")

    saved_crm_list = load_crm_tokens()

    success = True
    all_crm = []
    for idx, info in enumerate(tokens):
        saved_crm = saved_crm_list[idx] if idx < len(saved_crm_list) else None
        runner = RUN(info, idx, saved_crm=saved_crm)
        run_result = runner.main()
        if not run_result:
            success = False
        all_crm.append(runner.get_crm_for_save())

    save_crm_tokens(all_crm)

    if not success:
        sys.exit(1)