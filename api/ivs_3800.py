#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：calc_camera_pix_offset 
@File    ：ivs_3800.py
@Author  ：huangwenxi
@Date    ：2022/4/21 10:04 
'''
import re
import time
import requests
import json
import threading
import logging

logger = logging.getLogger('ivs3800')


class Url:
    LOGIN = 'https://{}:{}/loginInfo/login/v1.0'
    LOGOUT = 'https://{}:{}/users/logout'
    KEEP_ALIVE = 'https://{}:{}/common/keepAlive'
    GET_DEVICE_LIST = 'https://{}:{}/device/deviceList/v1.0?deviceType=35&fromIndex=1&toIndex=1000'
    GET_PLAYBACK_RESOURCE = 'https://{}:{}/video/rtspurl/v1.0'
    GET_VIDEO_LIST = 'https://{}:{}/platform/recordlist/0/{}/{}/{}/{}/1/1000'
    GET_START_PLATFORM_PLAYBACK = 'https://{}:{}/playback/startplatformplaybackbyip'


class RequestKey:
    COMMON_CONTENT_TYPE = "Content-Type"
    COMMON_COOKIE = "Cookie"
    LOGIN_USERNAME = "userName"
    LOGIN_PASSWORD = "password"
    GET_PLAYBACK_RESOURCE_CAMERA_CODE = "cameraCode"
    GET_PLAYBACK_RESOURCE_MEDIA_URL_PARAM = "mediaURLParam"


class ResponseKey:
    COMMON_SET_COOKIE = 'Set-Cookie'
    COMMON_RESULT_CODE = 'resultCode'
    GET_DEVICE_LIST_TOTAL = 'total'
    GET_DEVICE_LIST_CBIV2 = 'cameraBriefInfosV2'
    GET_DEVICE_LIST_CBIL = 'cameraBriefInfoList'
    GET_DEVICE_LIST_CBI = 'cameraBriefInfo'
    GET_DEVICE_LIST_DEVICE_IP = 'deviceIp'
    GET_DEVICE_LIST_CODE = 'code'
    GET_VIDEO_LIST_RECORD_INFO = 'recordInfos'


class IVS3800:
    def __init__(self, ivs_3800_ip, ivs_3800_username, ivs_3800_password, keep_alive_period_sec):
        self._ivs_3800_ip = ivs_3800_ip
        self._port = 18531
        self._ivs_3800_username = ivs_3800_username
        self._ivs_3800_password = ivs_3800_password
        "保活的周期"
        self._keep_alive_period_sec = keep_alive_period_sec
        "ivs3800客户端连接的session"
        self._session_id = None
        self._device_list = None
        "登录的状态"
        self._login_status = False
        "登出的状态"
        self._logout_status = False
        "IVS3800需要进行保活的操作，超时时间是30分钟"
        self._keep_live_thread = threading.Thread(target=self._keep_live_task, args=())
        self._keep_live_thread.start()

    @property
    def login_status(self):
        return self._login_status

    @property
    def logout_status(self):
        return self._logout_status

    def login(self):
        """
        登录到IVS3800,获取session id
        :return:
        """
        url = Url.LOGIN.format(self._ivs_3800_ip, self._port)
        logger.info(url)
        header = {RequestKey.COMMON_CONTENT_TYPE: "application/json;charset=UTF-8"}
        request_content = {RequestKey.LOGIN_USERNAME: self._ivs_3800_username,
                           RequestKey.LOGIN_PASSWORD: self._ivs_3800_password}
        response = requests.post(url, headers=header, data=json.dumps(request_content), verify=False)
        result_code = json.loads(response.text)[ResponseKey.COMMON_RESULT_CODE]
        logger.info(response.headers)
        logger.info(response.text)
        if result_code:
            logger.error('登录到IVS3800失败')
            return False
        self._session_id = response.headers[ResponseKey.COMMON_SET_COOKIE].split('=')[1].split(';')[0]
        logger.info('登录到IVS3800成功, ip:{}, session_id:{}'.format(self._ivs_3800_ip, self._session_id))
        self._login_status = True
        self._logout_status = False
        return True

    def logout(self):
        """
        从ivs登出
        :return:
        """
        url = Url.LOGOUT.format(self._ivs_3800_ip, self._port)
        header = {RequestKey.COMMON_COOKIE: '{}'.format(self._session_id)}
        response = requests.post(url, headers=header, verify=False)
        if response.status_code >= 400:
            logger.error(f'登出失败. url: {url}, response: {response}')
            self._login_status = False
            self._logout_status = True
            return False

        response_dict = json.loads(response.text)
        result_code = response_dict[ResponseKey.COMMON_RESULT_CODE]
        if not result_code:
            logger.info('从IVS3800登出成功')
            self._logout_status = True
            self._login_status = False
            return True
        else:
            logger.error('从IVS3800登出失败')
            return False

    def get_device_list(self):
        """
        获取IVS3800下的子设备列表
        :return:
        """
        url = Url.GET_DEVICE_LIST.format(self._ivs_3800_ip, self._port)
        header = {RequestKey.COMMON_CONTENT_TYPE: "application/x-www-form-urlencoded",
                  RequestKey.COMMON_COOKIE: "JSESSIONID={}".format(self._session_id)}
        response = requests.get(url, headers=header, verify=False)
        result_json = json.loads(response.text)
        logger.info(result_json)
        result_code = result_json[ResponseKey.COMMON_RESULT_CODE]
        if result_code:
            logger.error('获取设备子列表失败')
            return False
        camera_brief_infos = result_json[ResponseKey.GET_DEVICE_LIST_CBIV2]
        total = camera_brief_infos[ResponseKey.GET_DEVICE_LIST_TOTAL]
        if not total:
            logger.error('IVS3800上不存在设备')
            return False
        self._device_list = camera_brief_infos[ResponseKey.GET_DEVICE_LIST_CBIL][ResponseKey.GET_DEVICE_LIST_CBI]
        return True

    def get_camera_code(self, camera_ip):
        """
        通过相机的ip地址获取相机的camera id
        :param camera_ip:
        :return:
        """
        for device in self._device_list:
            if device[ResponseKey.GET_DEVICE_LIST_DEVICE_IP] == camera_ip:
                logger.info('获取到设备ip:{} code:{}'.format(camera_ip, device[ResponseKey.GET_DEVICE_LIST_CODE]))
                return device[ResponseKey.GET_DEVICE_LIST_CODE]

    def get_real_view_resource(self):
        """
        获取IVS3800的实时直播资源
        :return:
        """
        pass

    def get_playback_resource(self, camera_code, start_time, end_time):
        """
        根据指定的相机code和起止时间获取回放的资源
        :param camera_code:相机编号
        :param start_time:开始时间（UTC）
        :param end_time:结束时间（UTC）
        :return:执行的结果和url
        """
        url = Url.GET_PLAYBACK_RESOURCE.format(self._ivs_3800_ip, self._port)
        header = {RequestKey.COMMON_CONTENT_TYPE: "application/json",
                  RequestKey.COMMON_COOKIE: "JSESSIONID={}".format(self._session_id)}
        body = {"cameraCode": "{}".format(camera_code),
                "mediaURLParam": {"broadCastType": 0,
                                  "packProtocolType": 1,
                                  "timeSpan": {"startTime": start_time,
                                               "endTime": end_time
                                               },
                                  "protocolType": 2,
                                  "serviceType": 4,
                                  "streamType": 1,
                                  "transMode": 0,
                                  "clientType": 1
                                  }
                }
        response = requests.post(url, headers=header, data=json.dumps(body), verify=False)
        response_dict = json.loads(response.text)
        result_code = response_dict['resultCode']
        if result_code:
            logger.error('获取资源的URL路径失败')
            return False, None
        resp_url = response_dict['rtspURL']
        return True, resp_url

    def get_video_list(self, camera_code, time_start, time_end):
        """
        根据指定的参数获取在这段时间内该相机的录像的个数
        :param camera_code:相机编号
        :param time_start:开始时间（UTC）
        :param time_end:结束时间（UTC）
        :return:录像的个数
        """
        connect_code = camera_code.split('#')[0]
        domain_code = camera_code.split('#')[1]
        url = Url.GET_VIDEO_LIST.format(self._ivs_3800_ip, self._port, connect_code, domain_code, time_start, time_end)
        logger.info(url)
        header = {RequestKey.COMMON_CONTENT_TYPE: "application/json",
                  RequestKey.COMMON_COOKIE: "JSESSIONID={}".format(self._session_id)}
        logger.info(header)
        response = requests.get(url, headers=header, verify=False)
        response_dict = json.loads(response.text)
        logger.info(response_dict)
        if response_dict[ResponseKey.COMMON_RESULT_CODE]:
            logger.error('获取录像失败')
            return False
        record_total = response_dict['recordInfos']['total']
        logger.info('录像的个数为{}'.format(record_total))
        return record_total

    def _keep_alive(self):
        url = Url.KEEP_ALIVE.format(self._ivs_3800_ip, self._port)
        header = {RequestKey.COMMON_COOKIE: "JSESSIONID={}".format(self._session_id)}
        response = requests.get(url, headers=header, verify=False)
        logger.info(json.loads(response.text))

    def _keep_live_task(self):
        """
        ivs3800保活线程
        :return:
        """
        cnt = 0
        while cnt < self._keep_alive_period_sec:
            if self._logout_status:
                logger.info('已从IVS3800中登出，无需保活')
                break
            if not self._login_status:
                logger.info('Login失效，退出')
                break
            self._keep_alive()
            time.sleep(1)
            cnt += 1


if __name__ == '__main__':
    _3800 = IVS3800('10.10.43.12', "aokan_2022", "broadxt@333", keep_alive_period_sec=60)
    _3800.login()
    _3800.get_device_list()
    _camera_code = _3800.get_camera_code('10.10.40.2')
    _, rtsp_url = _3800.get_playback_resource(_camera_code, "20220913100000", "20220913100200")
    _3800.save_playback_resource(rtsp_url, '')

