# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：permissions.py
日期：2022年06月15日 15:36
"""
from rest_framework.permissions import BasePermission


class CostumePermission(BasePermission):

    def has_permission(self, request, view):
        return True
