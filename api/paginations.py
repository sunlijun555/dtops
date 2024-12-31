# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：paginations.py
日期：2022年07月29日 11:27
"""
from rest_framework.pagination import PageNumberPagination


class CostumePageNumberPagination(PageNumberPagination):

    # 默认一页条数
    page_size = 10
    # 前端查询发生页数关键字名
    page_query_param = "page"
    # 用户自定义一页条数关键字名
    page_size_query_param = "page_size"
    # 用户自定义一页最大条数
    max_page_size = 20
