# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：user.py
日期：2022年06月17日 14:41
"""
import logging
from django.contrib.auth.models import User, Group, Permission
from rest_framework.exceptions import APIException
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import mixins
from rest_framework.permissions import DjangoModelPermissions
from api.auth import JWTAuthentication
from api.serializers import UserSerializer, GroupSerializer, PermissionSerializer
from api.response import APIResponse


logger = logging.getLogger("django")


class UserViewSet(ModelViewSet):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [DjangoModelPermissions]
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(ModelViewSet):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [DjangoModelPermissions]
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class PermissionViewSet(GenericViewSet,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin):
    # authentication_classes = [JWTAuthentication]
    permission_classes = [DjangoModelPermissions]
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer


class UserInfoView(APIView):
    def get(self, request):
        user, _ = JWTAuthentication().authenticate(request)
        serializer = UserSerializer(instance=user)
        return APIResponse(results=serializer.data)
