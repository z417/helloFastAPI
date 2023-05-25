#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 28/Apr/2023 10:28
 * @LastEditors  : Yuri
 * @LastEditTime : 28/Apr/2023 11:06
 * @FilePath     : /teach/helloFastAPI/backend/src/FileCodeBox/dependencies.py
 * @Description  : file desc
'''
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status


class IPRATELimit:
    def __init__(self, count, minutes):
        self.ips = {}
        self.count = count
        self.minutes = minutes

    def check_ip(self, ip):
        if ip in self.ips:
            if self.ips[ip]['count'] >= self.count:
                if self.ips[ip]['time'] + timedelta(minutes=self.minutes) > datetime.utcnow():
                    return False
                else:
                    self.ips.pop(ip)
        return True

    def add_ip(self, ip):
        ip_info = self.ips.get(ip, {'count': 0, 'time': datetime.utcnow()})
        ip_info['count'] += 1
        ip_info['time'] = datetime.utcnow()
        self.ips[ip] = ip_info
        return ip_info['count']

    async def remove_expired_ip(self):
        for ip, info in self.ips.items():
            if info['time'] + timedelta(minutes=self.minutes) < datetime.utcnow():
                self.ips.pop(ip)

    def __call__(self, request: Request):
        ip = request.headers.get(
            'X-Real-IP') or request.headers.get('X-Forwarded-For') or request.client.host
        if not self.check_ip(ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests, do it later')
        return ip
