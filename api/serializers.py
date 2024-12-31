# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：serializers.py
日期：2022年06月10日 10:31
"""
import logging

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from api import models
from api.models import Project
from django.contrib.auth.hashers import make_password, check_password

logger = logging.getLogger("django")


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "perms")

    perms = serializers.SerializerMethodField()

    def get_perms(self, obj):
        return f"{obj}"


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name", "permissions", "permission_list")

    permissions = PermissionSerializer(many=True, read_only=True)
    permission_list = serializers.ListField(write_only=True)

    def create(self, validated_data):
        group = Group.objects.create(name=validated_data["name"])
        group.permissions.add(*validated_data["permission_list"])
        return group

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        if validated_data.get("permission_list"):
            instance.permissions.set(validated_data["permission_list"])
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "last_login", "date_joined", "user_permissions", "groups",
                  "password", "is_superuser", "username", "first_name", "last_name",
                  "email", "is_staff", "is_active", "user_permission_list", "group_list")

    password = serializers.CharField(write_only=True, required=False)
    last_login = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', label="上次登录", read_only=True)
    date_joined = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', label="创建时间", read_only=True)
    user_permissions = PermissionSerializer(many=True, read_only=True)
    user_permission_list = serializers.ListField(write_only=True)
    groups = GroupSerializer(many=True, read_only=True)
    group_list = serializers.ListField(write_only=True)

    def create(self, validated_data):
        user_permission_list = validated_data.pop("user_permission_list")
        group_list = validated_data.pop("group_list")
        user = User.objects.create_user(**validated_data)
        user.user_permissions.add(*user_permission_list)
        user.groups.add(*group_list)
        return user

    def update(self, instance, validated_data):
        if validated_data.get("user_permission_list"):
            user_permission_list = validated_data.pop("user_permission_list")
            instance.user_permissions.set(user_permission_list)
        if validated_data.get("group_list"):
            group_list = validated_data.pop("group_list")
            instance.groups.set(group_list)

        fields = ("is_superuser", "username", "first_name", "last_name",
                  "email", "is_staff", "is_active")
        for attr, value in validated_data.items():
            if attr in fields:
                setattr(instance, attr, value)
        instance.save()
        return instance


class ProjectModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = '__all__'

    user = serializers.CharField(source='user.username')
    content_type = serializers.CharField(source='content_type.model')
    action_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True, label="操作时间")
    action_flag = serializers.CharField(source='get_action_flag_display')
    change = serializers.SerializerMethodField()

    def get_change(self, obj):
        return f"{obj.action_time.strftime('%Y-%m-%d %H:%M:%S')}, 用户: {obj.user.username} {obj}"
