#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：抓包工具中筛选 eco.trantor.top，找到任意请求的 Authorization 头，复制 Bearer 后面的完整 JWT token
变量：ONESIGN_VMTDD_TOKEN（Bearer token，多账号用 # 分隔）
      可选变量 ONESIGN_VMTDD_LOCATION（经纬度，格式 "lat,lon"，用于获取推荐打卡点列表，默认洛阳）
      可选变量 ONESIGN_VMTDD_REGION（城市名，用于获取推荐打卡点，默认洛阳市）

cron: 0 8 * * *
new Env('维迈通多多签到');
"""
import json
import os
import sys
import time
import random
from datetime import datetime

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "维迈通多多"
BASE_URL = "https://eco.trantor.top"
success = True


def Log(cont=''):
    print(cont)


# ============================================================
# RUN 类 - 单账号签到 & 任务
# ============================================================

class RUN:
    def __init__(self, info, index):
        global success
        self.token = info.strip()
        self.index = index + 1

        # 解析位置信息（支持环境变量，多个账号位置不同时也用 # 分隔）
        location_raw = os.environ.get('ONESIGN_VMTDD_LOCATION', '34.15083803941892,112.47299011458907')
        region_raw = os.environ.get('ONESIGN_VMTDD_REGION', '洛阳市')
        locations = location_raw.split('#')
        regions = region_raw.split('#')
        loc_idx = index % len(locations)
        reg_idx = index % len(regions)
        self.location = locations[loc_idx].strip()
        self.region_name = regions[reg_idx].strip()

        self.s = requests.session()
        self.s.verify = False
        self.headers = {
            'version': '260906001',
            'user-agent': 'okhttp/4.12.0 (Linux; U; Android 15; RMX5062 Build/UKQ1.231108.001)',
            'language': 'zh_CN',
            'Authorization': f'Bearer {self.token}',
            'Host': 'eco.trantor.top',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
        }

        # 从 token 中解析用户信息
        self._parse_token()

        Log(f"\n---------开始执行第{self.index}个账号>>>>>")
        if self.user_id:
            Log(f"用户: {self.username} (ID: {self.user_id})")
        Log(f"位置: {self.region_name} ({self.location})")

    def _parse_token(self):
        self.user_id = ''
        self.username = '未知'
        try:
            parts = self.token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                import base64
                decoded = base64.b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                if isinstance(data, list) and len(data) >= 2:
                    self.user_id = str(data[0])
                    self.username = str(data[1])
        except Exception:
            pass

    def _post(self, path, data=None):
        try:
            if data:
                resp = self.s.post(
                    f'{BASE_URL}{path}',
                    data=data,
                    headers=self.headers,
                    timeout=15,
                )
            else:
                resp = self.s.post(
                    f'{BASE_URL}{path}',
                    headers=self.headers,
                    timeout=15,
                )
            return resp.json()
        except requests.RequestException as e:
            Log(f"请求错误: {e}")
            return None
        except json.JSONDecodeError:
            Log(f"响应解析失败: {resp.text[:200] if 'resp' in dir() else ''}")
            return None

    def _sleep(self, label=''):
        delay = 1.5 + random.uniform(0, 1)
        if label:
            Log(f"  ⏳ {label}，等待 {delay:.1f}s...")
        time.sleep(delay)

    # ---- 签到 ----

    def sign_info(self):
        Log("查询签到状态...")
        result = self._post('/ecosystem/integral/operation/signInfo')
        if result and result.get('code') == 0:
            data = result['data']
            is_sign = '已签到' if data.get('isSign') == 1 else '未签到'
            Log(f"  状态: {is_sign} | 连续签到: {data.get('continuousTimes', 0)}天 | 今日积分: {data.get('todayScore', '0')}")
            return data
        else:
            Log(f"  查询失败: {result}")
            return None

    def sign(self):
        global success
        Log("执行签到...")
        result = self._post('/ecosystem/integral/operation/sign')
        if result and result.get('code') == 0:
            Log(f"  签到成功！{result.get('msg', '')}")
            return True
        elif result and result.get('code') == 1 and '已经签到' in result.get('msg', ''):
            Log("  今日已签到，无需重复")
            return True
        else:
            Log(f"  签到失败: {result}")
            success = False
            return False

    # ---- 领取积分 ----

    def receive_integral(self):
        Log("领取待领积分...")
        result = self._post('/ecosystem/integral/operation/receive', data='id=all&type=0')
        if result and result.get('code') == 0:
            Log("  领取成功！")
            return True
        elif result and result.get('code') == 1 and '领取失败' in result.get('msg', ''):
            Log("  暂无待领取积分")
            return True
        else:
            Log(f"  领取异常: {result}")
            global success
            success = False
            return False

    # ---- 积分 ----

    def my_points(self, end=False):
        global success
        label = '执行后' if end else '当前'
        result = self._post('/ecosystem/integral/userIntegral/myIntegral')
        if result and result.get('code') == 0:
            data = result['data']
            Log(f"  {label}积分: {data.get('value', '0')}" +
                (f" (即将过期: {data.get('expirationValue', '0')})" if data.get('expirationValue', '0') != '0' else ""))
            return data
        else:
            Log(f"  查询积分失败: {result}")
            success = False
            return None

    # ---- 任务列表 ----

    def task_list(self):
        Log("获取任务列表...")
        result = self._post('/ecosystem/integral/operation/v1/integralDataList')
        if result and result.get('code') == 0:
            data = result['data']
            Log("  ── 每日任务 ──")
            for task in data.get('dailyTasks', []):
                status = '✅' if task.get('receiveStatus') == 1 else '⬜'
                Log(f"  {status} {task['taskTitle']} (+{task['value']}积分)")
            Log("  ── 进阶任务 ──")
            for task in data.get('advancedTasks', []):
                status = '✅' if task.get('receiveStatus') == 1 else '⬜'
                Log(f"  {status} {task['taskTitle']} (+{task['value']}积分)")
            return data
        else:
            Log(f"  获取任务列表失败: {result}")
            return None

    # ---- 点赞任务 ----

    def _get_recommend_punchpoints(self, need_count=5):
        punch_ids = []
        seen = set()
        next_page = None

        # 第一页: 不带 page 参数，通常只返回 2 个
        params = {
            'location': self.location,
            'type': '1',
            'regionName': self.region_name,
        }
        result = self._post('/ecosystem/punchpoint/recommend', data=params)
        if result and result.get('code') == 0:
            data = result['data']
            for item in data.get('list', []):
                if item['punchId'] not in seen:
                    punch_ids.append(item['punchId'])
                    seen.add(item['punchId'])
            next_page = data.get('nextPage')

        # 如果不够 need_count 个，用 nextPage 翻页获取更多 (每页最多 20 个)
        while len(punch_ids) < need_count and next_page:
            self._sleep()
            params['page'] = next_page
            result = self._post('/ecosystem/punchpoint/recommend', data=params)
            if result and result.get('code') == 0:
                data = result['data']
                for item in data.get('list', []):
                    if item['punchId'] not in seen:
                        punch_ids.append(item['punchId'])
                        seen.add(item['punchId'])
                next_page = data.get('nextPage')
            else:
                break

        return punch_ids

    def _like_punchpoint(self, punch_id):
        result = self._post('/ecosystem/useraction/like', data={
            'punchId': str(punch_id),
            'type': '1',
        })
        return result and result.get('code') == 0

    def do_like_task(self, count=5):
        global success
        Log(f"执行点赞任务 (目标: {count}个打卡点)...")

        punch_ids = self._get_recommend_punchpoints()
        if not punch_ids:
            Log("  没有可点赞的打卡点")
            return False

        target = min(count, len(punch_ids))
        ok = 0
        for i in range(target):
            pid = punch_ids[i]
            if self._like_punchpoint(pid):
                Log(f"  [{i+1}/{target}] 点赞 punchId={pid} 成功")
                ok += 1
            else:
                Log(f"  [{i+1}/{target}] 点赞 punchId={pid} 失败")
                success = False
            if i < target - 1:
                self._sleep()

        Log(f"  点赞完成: {ok}/{target}")
        return ok >= target

    # ---- 骑行模拟 ----

    def _generate_trajectory(self, start_lat, start_lon, distance_m=1200, points_count=60):
        lat_per_km = 1.0 / 111000.0
        lon_per_km = 1.0 / (111000.0 * 0.848)
        total_dist = distance_m / 1000.0
        lat_step = total_dist * lat_per_km / points_count
        lon_step = total_dist * lon_per_km / points_count

        now_ms = int(time.time() * 1000)
        points = []
        for i in range(points_count):
            lat = round(start_lat + lat_step * i, 6)
            lon = round(start_lon + lon_step * i, 6)
            alt = round(250.0 + random.uniform(-5, 5), 1)
            speed = round(random.uniform(8, 35), 3)
            ts = now_ms - (points_count - i) * 2000
            points.append(f"{lat},{lon},{alt},0.0,{speed},{ts}")
        return ';'.join(points), now_ms

    def _upload_trajectory(self, group_id, user_id, pos_content, upload_time_ms):
        filename = f"{group_id}_{user_id}_{upload_time_ms}_1.5.27.11.pos"

        weather_str = json.dumps({
            f"{filename}": [{"1": "1"}]
        })
        through_city_str = json.dumps({
            f"{filename}": [{"1": self.region_name}]
        })

        files = {
            'file': (filename, pos_content.encode('utf-8'), 'application/octet-stream'),
        }
        data = {
            'token': self.token,
            'time': str(upload_time_ms),
            'weather': weather_str,
            'throughCity': through_city_str,
        }

        try:
            resp = requests.post(
                'https://data.trantor.top/uploadLocationFile/trajectory',
                data=data,
                files=files,
                timeout=30,
            )
            return resp.json()
        except Exception as e:
            Log(f"  轨迹上传异常: {e}")
            return None

    def simulate_riding(self):
        global success
        Log("模拟骑行 1km...")

        lat_parts = self.location.split(',')
        try:
            lat = float(lat_parts[0].strip())
            lon = float(lat_parts[1].strip())
        except (ValueError, IndexError):
            Log("  位置解析失败，使用默认坐标")
            lat, lon = 34.1509, 112.4730

        # 1. 上报设备连接
        Log("  上报设备连接...")
        device_result = self._post('/ecosystem/deviceConnect/report', data={
            'province': '河南省',
            'city': self.region_name,
            'location': self.location,
            'deviceModel': 'SOAIY GD36',
            'macAddress': '41:42:F8:68:33:6B',
        })
        if device_result and device_result.get('code') == 0:
            Log("  设备连接上报成功")
        else:
            Log(f"  设备连接上报失败: {device_result}")

        self._sleep()

        # 2. 生成轨迹并上传
        Log("  生成轨迹数据...")
        pos_content, upload_time_ms = self._generate_trajectory(lat, lon)
        group_id = abs(int(time.time() * 1000000) % 9999999999)  # 随机 session id
        user_id = self.user_id or '2960774'

        Log(f"  上传轨迹 (group_id={group_id}, 约1.2km)...")
        upload_result = self._upload_trajectory(group_id, user_id, pos_content, upload_time_ms)
        if upload_result and upload_result.get('code') == 200:
            Log("  轨迹上传成功！")
            return True
        else:
            Log(f"  轨迹上传失败: {upload_result}")
            success = False
            return False

    # ---- 签到日历 ----

    def sign_calendar(self, year=None, month=None):
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        result = self._post('/ecosystem/integral/operation/v1/calendar', data={
            'year': str(year),
            'month': str(month),
        })
        if result and result.get('code') == 0:
            signed = [d['date'][-2:] for d in result['data'] if d.get('signStatus') == '2']
            Log(f"  本月已签到 {len(signed)} 天: {', '.join(signed) if signed else '无'}")
            return result['data']
        else:
            Log(f"  查询日历失败: {result}")
            return None

    # ---- 主流程 ----

    def main(self):
        global success

        # 1. 查询积分
        if not self.my_points():
            return False

        # 2. 签到
        info = self.sign_info()
        if info and info.get('isSign') == 0:
            self.sign()
        elif info:
            Log("今日已签到，跳过")

        # 3. 点赞任务 (通过 API 可自动完成的任务)
        self._sleep()
        self.do_like_task(count=5)

        # 4. 签到日历
        self._sleep()
        self.sign_calendar()

        # 5. 任务列表总结
        self._sleep()
        self.task_list()

        # 6. 领取积分 (所有任务执行后统一领取)
        self._sleep()
        self.receive_integral()

        # 7. 最终积分
        self.my_points(end=True)

        return True


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    token = os.environ.get('ONESIGN_VMTDD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_VMTDD_TOKEN 变量")
        print("抓包获取: 抓包工具筛选 eco.trantor.top，复制任意请求 Authorization 头 Bearer 后的 JWT token")
        sys.exit(1)

    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{len(tokens)}个账号")

    for idx, info in enumerate(tokens):
        RUN(info, idx).main()

    if not success:
        sys.exit(1)