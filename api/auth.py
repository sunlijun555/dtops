# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：auth.py
日期：2022年06月15日 13:57
"""
import jwt
from django.contrib.auth.models import User
from jwt import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, APIException
from rtops.settings import SECRET_KEY


class JWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        salt = SECRET_KEY
        try:
            payload = jwt.decode(token, salt, ['HS256'])
            user_id = payload.get('id')
            if not user_id:
                raise APIException(detail="当前无登录用户")
            user = User.objects.get(id=user_id)
        except exceptions.ExpiredSignatureError:
            raise AuthenticationFailed({'code': 1003, 'error': 'token已失效'})
        except jwt.DecodeError:
            raise AuthenticationFailed({'code': 1003, 'error': 'token认证失败'})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({'code': 1003, 'error': '非法的token'})
        return user, token
