# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：response.py
日期：2022年07月14日 9:25
"""

from rest_framework.response import Response


class APIResponse(Response):
    def __init__(self, code=200, message='success', results=None,
                 http_status=None, headers=None, exception=False,
                 **kwargs):
        data = {
            'code': code,
            'message': message
        }

        if results is not None:
            data["results"] = results

        if kwargs is not None:
            for k, v in kwargs.items():
                setattr(data, k, v)
        super().__init__(data=data, status=http_status, headers=headers, exception=exception)
