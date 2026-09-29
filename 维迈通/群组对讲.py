#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓包：抓包工具中筛选 eco.trantor.top，找到任意请求的 Authorization 头，复制 Bearer 后面的完整 JWT token
变量：ONESIGN_VMTDD_TOKEN（Bearer token，多账号用 # 分隔）
      可选变量 ONESIGN_VMTDD_LOCATION（经纬度，格式 "lat,lon"，默认洛阳）
      可选变量 ONESIGN_VMTDD_REGION（城市名，默认洛阳市）

cron: 30 9 * * *
new Env('维迈通群组对讲');
"""
import json
import math
import os
import sys
import time
import random

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SCRIPT_NAME = "维迈通群组对讲"
BASE_URL = "https://eco.trantor.top"
success = True


def Log(cont=''):
    print(cont)


class RUN:
    def __init__(self, info, index):
        global success
        self.token = info.strip()
        self.index = index + 1

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

    def my_points(self):
        global success
        result = self._post('/ecosystem/integral/userIntegral/myIntegral')
        if result and result.get('code') == 0:
            data = result['data']
            Log(f"  当前积分: {data.get('value', '0')}")
            return data
        else:
            Log(f"  查询积分失败: {result}")
            success = False
            return None

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

    def task_list(self):
        result = self._post('/ecosystem/integral/operation/v1/integralDataList')
        if result and result.get('code') == 0:
            data = result['data']
            for task in data.get('dailyTasks', []):
                status = '✅' if task.get('receiveStatus') == 1 else '⬜'
                Log(f"  {status} {task['taskTitle']} (+{task['value']}积分)")
            return data
        else:
            Log(f"  获取任务列表失败: {result}")
            return None

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

    def _generate_trajectory(self, start_lat, start_lon, distance_m=1500, points_per_km=150, time_offset_s=0):
        avg_speed_mps = 8.0

        alt_base = random.uniform(50, 400)
        alt_amplitude = random.uniform(30, 200)
        alt_phase = random.uniform(0, math.pi * 2)
        alt_freq = random.uniform(1.5, 3.5)

        bearing = random.uniform(0, 360)
        bearing_rad = math.radians(bearing)

        lat_per_m = 1.0 / 111320.0
        lon_per_m = 1.0 / (111320.0 * math.cos(math.radians(start_lat)))

        points_count = max(60, int(distance_m / 1000.0 * points_per_km))
        step_m = distance_m / points_count
        step_time_ms = int(step_m / avg_speed_mps * 1000)

        base_ms = int(time.time() * 1000) - time_offset_s * 1000
        points = []

        current_lat = start_lat
        current_lon = start_lon
        prev_speed = random.uniform(5, 20)

        ride_start_ms = base_ms - points_count * step_time_ms

        for i in range(points_count):
            progress = i / points_count

            turn_amount = math.sin(progress * math.pi * random.uniform(1.5, 3.0)) * random.uniform(20, 50)
            turn_amount += random.uniform(-3, 3)
            cur_bearing = bearing_rad + math.radians(turn_amount)

            lat_offset = step_m * lat_per_m * math.cos(cur_bearing)
            lon_offset = step_m * lon_per_m * math.sin(cur_bearing)

            current_lat += lat_offset
            current_lon += lon_offset

            raw_alt = alt_base + alt_amplitude * math.sin(progress * math.pi * alt_freq + alt_phase)
            alt_noise = random.uniform(-8, 8)
            alt = round(raw_alt + alt_noise, 1)
            alt = max(9.0, min(500.0, alt))

            if progress < 0.05:
                target_speed = random.uniform(0, 15)
            elif progress > 0.9:
                target_speed = random.uniform(0, 10)
            elif random.random() < 0.03:
                target_speed = random.uniform(0, 3)
            elif random.random() < 0.08:
                target_speed = random.uniform(55, 95)
            elif random.random() < 0.1:
                target_speed = random.uniform(5, 20)
            else:
                target_speed = random.uniform(18, 50)

            speed = round(prev_speed + (target_speed - prev_speed) * random.uniform(0.3, 0.7), 3)
            speed = max(0.0, min(98.0, speed))
            prev_speed = speed

            ts = base_ms - (points_count - i) * step_time_ms

            cur_bearing_deg = round(math.degrees(cur_bearing) % 360, 1)

            points.append(f"{round(current_lat, 6)},{round(current_lon, 6)},{cur_bearing_deg},{alt},{speed},{ts}")

        return ';'.join(points), ride_start_ms, points_count, base_ms

    def _upload_trajectory_batch(self, user_id, pos_items, upload_time_ms):
        files = []
        weather_data = {}
        through_city_data = {}

        for item in pos_items:
            group_id, pos_content, ride_time_ms, ending_ts = item[:4]

            filename = f"{group_id}_{user_id}_{ride_time_ms}_1.5.27.11.pos"
            ending_content = pos_content + f";0,0,0,0,0,{ending_ts};"
            files.append(('file', (filename, ending_content.encode('utf-8'), 'application/octet-stream')))

            weather_code = str(random.randint(0, 3))
            weather_ts = str(int(math.ceil(ride_time_ms / 1000.0)))
            weather_data[filename] = [{weather_ts: weather_code}]

            through_city_data[filename] = [{weather_ts: self.region_name}]

        data = {
            'token': self.token,
            'time': str(upload_time_ms),
            'weather': json.dumps(weather_data),
            'throughCity': json.dumps(through_city_data),
        }

        try:
            resp = requests.post(
                'https://data.trantor.top/uploadLocationFile/trajectory',
                data=data,
                files=files,
                timeout=30,
            )
            result = resp.json()
            Log(f"  轨迹上传响应: code={result.get('code')}, msg={result.get('msg', '')}")
            return result
        except Exception as e:
            Log(f"  轨迹上传异常: {e}")
            return None

    def simulate_group_intercom(self):
        global success
        Log("模拟群组对讲...")

        lat_parts = self.location.split(',')
        try:
            lat = float(lat_parts[0].strip())
            lon = float(lat_parts[1].strip())
        except (ValueError, IndexError):
            Log("  位置解析失败，使用默认坐标")
            lat, lon = 34.1509, 112.4730

        user_id = self.user_id or '2960774'

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

        Log("  骑行前查询数据...")
        riding_data_before = self._post('/ecosystem/trajectoryData/ridingData', data='white=2')
        if riding_data_before and riding_data_before.get('code') == 0:
            Log(f"  骑行前数据: {riding_data_before['data'].get('brandName', '?')} {riding_data_before['data'].get('cyclingName', '?')}")
        self._sleep()

        distance = random.randint(2000, 10000)
        time_offset_s = 0

        pos_content, ride_time_ms, pts_count, base_ms = self._generate_trajectory(
            lat, lon, distance_m=distance, time_offset_s=time_offset_s
        )
        group_id = int(user_id)
        ending_ts = int(time.time() * 1000)
        pos_items = [(group_id, pos_content, ride_time_ms, ending_ts)]

        estimated_duration_s = int(distance / 8.0)
        Log(f"  轨迹: {distance}m, {pts_count}点, 约{estimated_duration_s // 60}分{estimated_duration_s % 60}秒, group_id={group_id}")

        for upload_idx in range(2):
            upload_time_ms = int(time.time() * 1000)
            Log(f"  上传轨迹 第{upload_idx + 1}次 ({distance}m, {pts_count}点) ...")
            upload_result = self._upload_trajectory_batch(user_id, pos_items, upload_time_ms)
            if upload_result and upload_result.get('code') == 200:
                Log(f"  第{upload_idx + 1}次上传成功！")
            else:
                Log(f"  第{upload_idx + 1}次上传失败: {upload_result}")
                success = False
                return False
            if upload_idx == 0:
                self._sleep()

        self._sleep()
        Log("  查询骑行数据...")
        riding_data = self._post('/ecosystem/trajectoryData/ridingData', data='white=2')
        if riding_data and riding_data.get('code') == 0:
            brand = riding_data['data'].get('brandName', '未知')
            bike = riding_data['data'].get('cyclingName', '未知')
            Log(f"  骑行数据: {brand} {bike}")
        return True

    def main(self):
        global success

        if not self.my_points():
            return False

        info = self.sign_info()
        if info and int(info.get('isSign', 1)) != 1:
            self.sign()
        elif info:
            Log("今日已签到，跳过")

        self._sleep()
        tasks = self.task_list()

        need_group = True
        if tasks:
            for t in tasks.get('dailyTasks', []):
                if t.get('receiveStatus') == 1 and '群组对讲' in t.get('taskTitle', ''):
                    Log("群组对讲任务已完成，跳过")
                    need_group = False

        if need_group:
            self._sleep()
            if self.simulate_group_intercom():
                Log("  等待服务端确认群组对讲...")
                verified = False
                for retry in range(6):
                    time.sleep(5)
                    tasks_after = self.task_list()
                    if tasks_after:
                        for t in tasks_after.get('dailyTasks', []):
                            if '群组对讲' in t.get('taskTitle', '') and t.get('receiveStatus') == 1:
                                Log(f"  ✅ 群组对讲确认完成 (等待 {(retry + 1) * 5}s)")
                                verified = True
                                break
                    if verified:
                        break
                if not verified:
                    Log("  ⚠️ 群组对讲 30s 内未确认，可能需 App 内完成")
            else:
                Log("  ⚠️ 群组对讲模拟失败")

        self._sleep()
        self.receive_integral()

        self.my_points()

        return True


if __name__ == '__main__':
    token = os.environ.get('ONESIGN_VMTDD_TOKEN', '')
    if not token:
        print("未配置 ONESIGN_VMTDD_TOKEN 变量")
        sys.exit(1)

    tokens = token.split('#')
    tokens = [t for t in tokens if t]
    print(f"共获取到{tokens}个账号")

    for idx, info in enumerate(tokens):
        RUN(info, idx).main()

    if not success:
        sys.exit(1)