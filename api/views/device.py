# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：device.py
日期：2022年06月17日 14:41
"""
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from api.auth import JWTAuthentication
from api.models import ITS800HostModel
from api.serializers import ITS800HostModelSerializer


class ITS800HostViewSet(mixins.ListModelMixin,
                        # mixins.CreateModelMixin,
                        # mixins.DestroyModelMixin,
                        mixins.RetrieveModelMixin,
                        GenericViewSet):
    """
    its800主机
    """
    # authentication_classes = [JWTAuthentication, ]
    queryset = ITS800HostModel.objects.all()
    serializer_class = ITS800HostModelSerializer
