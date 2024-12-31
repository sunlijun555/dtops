# Create your views here.
# -*- coding:utf-8 -*-
import io
import os
import re
import shutil
import tarfile
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import threading
from datetime import datetime, timedelta

from django.contrib.admin.models import LogEntry
from django.forms import model_to_dict
from django.http import StreamingHttpResponse
from rest_framework.exceptions import APIException
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.views import APIView
from dwebsocket.decorators import require_websocket
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, mixins

from api.ivs_3800 import IVS3800
from api.paginations import CostumePageNumberPagination
from api.serializers import LogEntrySerializer
from api.models import Project
from api.serializers import ProjectModelSerializer
from rtops.settings import BASE_DIR
from api.utils import create_token, compute_date_range, PGConnector, SSH
from api.auth import JWTAuthentication
from rest_framework.permissions import DjangoModelPermissions
from api.constants import HostConfig, DR_DB_CONF, ITS800_CONFIG, Ivs3800Config, EVENT_ID_DB_CONF
from api.response import APIResponse
from api.utils import parse_node

logger = logging.getLogger('django')


class LoginView(APIView):
    """
    登录视图, post请求，使用用户id和name做payload凭据，创建token并返回
    """

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user_obj = User.objects.filter(username=username).first()
        if not (user_obj and user_obj.check_password(password)):
            logger.error('用户名或者密码错误')
            return APIResponse(code=500, message="用户名或者密码错误")
        token = create_token(payload={'id': user_obj.id, 'username': user_obj.username})
        return APIResponse(results={'token': token})


class ProjectListViewSet(mixins.ListModelMixin, GenericViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectModelSerializer


class NodeActiveListView(APIView):
    """
    存活的点位列表视图
    """

    def get(self, request):
        # get方法url参数获取使用query_params获取
        project = request.query_params.get('project')
        node_info_file_path = os.path.join(BASE_DIR, 'config', 'node_info.json')
        if not os.path.exists(node_info_file_path):
            raise APIException(f"{node_info_file_path} 文件不存在！")
        with open(node_info_file_path, 'r') as file_r:
            content = json.load(file_r)
        if project not in content:
            raise APIException(f'不存在的项目: {project}')
        result = {}
        for node_id, node_info in content.get(project).items():
            ip = node_info.get('ip')
            if node_info.get('is_active'):
                result.setdefault(ip, []).append(node_id)
        return Response(result)


class ShowNodeIts800File(APIView):
    """展示一个点位下所拥有的its800文件列表"""
    def get(self, request):
        its800_data_dir = "/opt/third_algorithm_D/debug_its_period/debug"
        project = request.query_params.get("project")
        date = request.query_params.get("date")
        node_id = request.query_params.get("node_id")
        project_content = parse_node(project)
        its800 = project_content.get(node_id).get("ip")
        base_its800_info = ITS800_CONFIG.get(project, {})
        if not base_its800_info:
            raise ValueError(f"未找到{project}项目配置")
        port = base_its800_info.get('port')
        username = base_its800_info.get('username')
        password = base_its800_info.get('password')
        su_password = base_its800_info.get('su_password')
        ssh = SSH(its800, port, username, password, su_password)
        try:
            ssh.connect(connect_invoke_shell=True)
            ssh.switch_root_user()
            result = ssh.exec_invoke_shell_command(f"ls {its800_data_dir} -t --color=no")
            data_pattern_obj = re.compile(r"\d+-\d+-\d+-\d+-\d+-\d+")
            file_list = data_pattern_obj.findall(result)
        except (AssertionError, Exception) as exception:
            logger.error(exception)
            raise APIException(detail=f"{its800} 主机连接失败")
        finally:
            ssh.close()
        data = []
        for file in file_list:
            if date in file and not file.endswith("tar.gz"):
                data.append(file)
        return APIResponse(results=data)

    def get_file_more_node(self, project, start_time, end_time, node_id):
        """ 多点位获取文件列表 """
        project_content = parse_node(project)
        node_ids = node_id.split(',')
        its800_ips = [(node, project_content.get(node).get("ip")) for node in node_ids]
        base_its800_info = ITS800_CONFIG.get(project, {})
        if not base_its800_info:
            raise ValueError(f"未找到{project}项目配置")
        port = base_its800_info.get('port')
        username = base_its800_info.get('username')
        password = base_its800_info.get('password')
        su_password = base_its800_info.get('su_password')
        data = []
        filter_files = []
        start_date = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        year_month_day = start_date.strftime('%Y-%m-%d')
        minute = start_date.minute // 10 * 10
        diff_minutes = minute + ((end_date - start_date).seconds // 60)
        i = start_date.minute // 10 * 10
        hour = start_date.hour
        while i < diff_minutes:
            if i + 10 > 60:
                i = 0
                diff_minutes = diff_minutes - 60
                hour += 1
            print(f"{year_month_day}-{hour}-{i}-{i + 10}")
            filter_files.append(f"{year_month_day}-{hour}-{i}-{i + 10}")
            i += 10
        with ThreadPoolExecutor(max_workers=len(its800_ips)) as t:
            res = [t.submit(lambda cxp: self.connect_its800(*cxp), (ip, port, username, password, su_password, project, filter_files))
                   for ip in its800_ips]
            for future in as_completed(res):
                data.append(future.result())
        return data

    @staticmethod
    def connect_its800(ip, port, username, password, su_password, project, filter_files=None):
        its800_data_dir = "/opt/third_algorithm_D/debug_its_period/debug"
        ssh = SSH(ip[1], port, username, password, su_password)
        try:
            ssh.connect(connect_invoke_shell=True)
            ssh.switch_root_user()
            result = ssh.exec_invoke_shell_command(f"ls {its800_data_dir} -t --color=no")
            data_pattern_obj = re.compile(r"\d+-\d+-\d+-\d+-\d+-\d+")
            file_list = data_pattern_obj.findall(result)
        except (AssertionError, Exception) as exception:
            logger.error(exception)
            raise APIException(detail=f"{ip} 主机连接失败")
        finally:
            ssh.close()
        data = []
        for file in file_list:
            if not file.endswith("tar.gz"):
                if file in filter_files:
                    data.append(file)
        return {ip[0]: data}


class Its800DataTreeView(APIView):
    """its800数据查询，请求格式：
    {
    "project": "jichang_hiway",
    "node_list": [
        "12000001",
        "12000003",
        "12000004"],
    "start_time": "2022-06-18-22-20-30",
    "end_time": "2022-06-23-13-50-59"
    }
    """

    def post(self, request):
        save_dir = HostConfig.its800_save_path
        project = request.data.get('project')
        node_list = request.data.get('node_list')
        start_time = request.data.get('start_time')
        start_datetime = datetime.strptime(start_time, '%Y-%m-%d-%H-%M-%S')
        end_time = request.data.get('end_time')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%d-%H-%M-%S')
        if not (start_time and end_time and node_list and project and isinstance(node_list, list)):
            raise APIException("post body 格式错误")
        node_info_file_path = os.path.join(BASE_DIR, 'config', 'node_info.json')
        if not os.path.exists(node_info_file_path):
            raise APIException(f"{node_info_file_path} 文件不存在！")
        with open(node_info_file_path, 'r') as file_r:
            content = json.load(file_r)
        node_items = content.get(project)
        result = {}
        str_time_obj = re.compile(r"\d+-\d+-\d+-\d+-\d+")

        date_range = compute_date_range(start_time, end_time)
        for node in node_list:
            data = []
            node_item = node_items.get(node)
            its800_ip = node_item.get('ip')
            if its800_ip in result:
                result.setdefault(its800_ip, {}).setdefault('node', []).append(node)
                continue

            base_path = os.path.join(save_dir, project, its800_ip)
            scheduler_path = os.path.join(HostConfig.scheduler_its800_save_path, project, its800_ip)
            for date in date_range:
                data_path = os.path.join(base_path, date)
                scheduler_data_path = os.path.join(scheduler_path, date)
                # 当天数据不存在，过滤
                if os.path.exists(data_path):
                    for its800_name in os.listdir(data_path):
                        its800_str_time = str_time_obj.match(str(its800_name))
                        if its800_str_time:
                            its800_datetime = datetime.strptime(its800_str_time.group(), '%Y-%m-%d-%H-%M')
                            if start_datetime <= its800_datetime <= end_datetime:
                                data.append(its800_name)
                # 查找scheduler下定时收集的800数据
                if os.path.exists(scheduler_data_path):
                    for its800_name in os.listdir(scheduler_data_path):
                        its800_str_time = str_time_obj.match(str(its800_name))
                        if its800_str_time:
                            its800_datetime = datetime.strptime(its800_str_time.group(), '%Y-%m-%d-%H-%M')
                            if start_datetime <= its800_datetime <= end_datetime:
                                if its800_name not in data:
                                    data.append(its800_name)
            result.setdefault(its800_ip, {}).setdefault('node', []).append(node)
            result.setdefault(its800_ip, {}).setdefault('data', data)
        return Response(result)


class Its800DownloadView(APIView):
    """
    its800文件下载，请求格式：
    {
    "project": "jichang_hiway",
    "its800_ip": "10.10.40.249",
    "file": "2022-06-21-11-40-50.tar.gz"
    }
    """

    def post(self, request):
        def file_iterator(file_name, chunk_size=512):
            with open(file_name, 'rb') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break

        save_dir = HostConfig.its800_save_path
        project = request.data.get('project')
        its800_ip = request.data.get('its800_ip')
        file = request.data.get('file')
        if not (project and its800_ip and file):
            raise APIException("post body 格式错误")
        day_pattern_obj = re.compile(r'\d+-\d+-\d+')
        everyday_dir = day_pattern_obj.match(file)
        if everyday_dir:
            file_path = os.path.join(save_dir, project, its800_ip, everyday_dir.group(), file)
            if not os.path.isfile(file_path):
                file_path = os.path.join(HostConfig.scheduler_its800_save_path, project, its800_ip, everyday_dir.group(), file)
            if not os.path.isfile(file_path):
                raise APIException("没有这样的文件")
            response = StreamingHttpResponse(file_iterator(file_path))
            # 让文件流写入硬盘，需要对下面两个字段赋值
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file)
            return response
        else:
            return Response(f'未发现这样的文件: {file}')


class Its800UploadView(APIView):
    """
    its800文件上传接口
    """

    def post(self, request):
        save_dir = HostConfig.its800_save_path
        project = request.data.get('project')
        its800_ip = request.data.get('its800_ip')
        file_name = request.data.get('file_name')
        file = request.data.get('file')
        if not (project and its800_ip and file_name and file):
            raise APIException("post body 格式错误")
        day_pattern_obj = re.compile(r'\d+-\d+-\d+')
        everyday_dir = day_pattern_obj.match(file_name)
        if not everyday_dir:
            raise APIException("文件名称格式错误")
        file_dir = os.path.join(save_dir, project, its800_ip, everyday_dir.group())
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_path = os.path.join(file_dir, file_name)
        with open(file_path, 'wb') as file_obj:
            for chunk in file.chunks():
                file_obj.write(chunk)
        return APIResponse(results="文件上传成功")


class TaskStatusView(APIView):
    """
    get传入taskid，查询任务状态
    """

    def get(self, request):
        task_id = request.query_params.get('task_id')
        from celery.result import AsyncResult
        task = AsyncResult(task_id)
        status = task.status
        return APIResponse(results={task_id: status})


class DATAToExcelView(APIView):
    """
    导出为excel，get方法携带job_id、data_type参数，根据data_type为
    dra还是drc导出相应csv数据
    """

    def get(self, request):
        def file_iterator(file_content, chunk_size=512):
            while True:
                c = file_content.read(chunk_size)
                if c:
                    yield c
                else:
                    break

        job_id = request.query_params.get("job_id")
        data_type = request.query_params.get("data_type")
        if not job_id:
            raise APIException(detail="job_id参数为空")
        pg = PGConnector(*HostConfig.get_pg_conf())
        if data_type == "dra":
            table = HostConfig.drsu_table
        elif data_type == "drc":
            table = HostConfig.drc_table
        else:
            raise APIException(detail="不支持的data_type")
        pg.connect()
        sql = f"""
                SELECT * FROM "public".{table} 
                WHERE job_id = '{job_id}';"""
        dataframe = pg.read_sql(sql)
        pg.close()
        buffer = io.StringIO()
        dataframe.to_csv(buffer, index=False, encoding='utf-8')
        buffer.seek(0)
        response = StreamingHttpResponse(file_iterator(buffer))
        response["Content-Type"] = 'text/csv'
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(job_id)
        return response


class LocalDataImportView(APIView):
    """
    导入本地数据
    """

    def post(self, request):
        print(request.data)
        file = request.data.get('file')
        with open('./files.txt', 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        print('导入成功')


class EventParserView(APIView):

    def get(self, request):
        event_id = request.query_params.get('event_id')
        project_name = request.query_params.get('project')
        if not (event_id and project_name):
            raise APIException(detail=f"缺少event_id或者project参数")
        if not event_id.isdigit():
            raise APIException(detail=f"event_id必须为数字")
        event_mapping = {
            "4": "单车异常停车预警",
            "6": "逆行预警",
            "7": "违规行人预警",
            "8": "超低速预警",
            "9": "低速预警",
            "10": "抛洒物预警",
            "11": "拥堵预警",
            "12": "道路封闭预警",
            "13": "跨车道行驶预警",
            "14": "道路结冰预警",
            "15": "道路湿滑预警",
            "16": "团雾预警",
            "17": "超速预警",
            "18": "道路维护预警",
            "19": "占用应急车道预警",
            "20": "跨车道行驶预警",
            "22": "行人被遮挡事件",
            "25": "交通事故预警",
            "27": "占用公交车道预警"
        }

        base_info_sql = f"""
        SELECT occur_time, relieve_time, traffic_event_type, node_ids FROM 
        traffic_event WHERE traffic_event_id = {event_id} OR drc_event_report_id = {event_id};"""

        sub_node_id_sql = f"""
        SELECT DISTINCT sub_node_ids FROM traffic_event_history 
        WHERE traffic_event_id = {event_id} OR drc_event_report_id = {event_id} AND sub_node_ids IS NOT NULL;
        """

        judge_time_sql = f"""
        SELECT judge_time FROM traffic_event_judge_time  thjt
        LEFT JOIN traffic_event_history teh on thjt.traffic_event_history_id = teh.id
        WHERE teh.traffic_event_id = {event_id} OR drc_event_report_id = {event_id} AND sub_node_ids IS NOT NULL
        ORDER BY judge_time ASC LIMIT 1;
        """

        db_conf = EVENT_ID_DB_CONF.get(project_name)
        user, password, host, port, event_dbname \
            = map(lambda x: db_conf.get(x), ['user', 'password', 'host', 'port', 'event_dbname'])
        read_event_connector = PGConnector(user, password, host, port, event_dbname)
        try:
            read_event_connector.connect()
            dataframe = read_event_connector.read_sql(base_info_sql)
            if dataframe.empty:
                raise APIException(detail="数据库不存在此id")
            original_data = dataframe.to_dict(orient="records")[0]
            occur_time = original_data.get('occur_time')
            relieve_time = original_data.get('relieve_time')
            node_ids = original_data.get('node_ids')
            traffic_event_type = str(original_data.get('traffic_event_type'))

            event_type = event_mapping.get(traffic_event_type)

            judge_time_dataframe = read_event_connector.read_sql(judge_time_sql)

            if not judge_time_dataframe.empty:
                occur_time = judge_time_dataframe.to_dict(orient="records")[0].get("judge_time")

            sub_node_id_dataframe = read_event_connector.read_sql(sub_node_id_sql)
            if sub_node_id_dataframe.empty:
                sub_node_ids = ""
            else:
                another_data = sub_node_id_dataframe.to_dict()
                sub_node_dict = another_data.get('sub_node_ids', {})

                node_list = []
                for idx, sub_node_id_str in sub_node_dict.items():
                    if not sub_node_id_str:
                        continue
                    if ',' in sub_node_id_str:
                        ids = sub_node_id_str.strip().split(',')
                        node_list += ids
                    else:
                        node_list.append(sub_node_id_str)
                deal_with_nodes = list(set(node_list))
                deal_with_nodes.sort()
                sub_node_ids = ','.join(deal_with_nodes)
            data = {'start_time': str(occur_time),
                    'end_time': str(relieve_time),
                    'event_type': event_type,
                    'node_id': node_ids,
                    'drc_report_id': sub_node_ids
                    }
        except APIException as api_error:
            raise api_error
        except Exception as exception:
            logger.error(exception)
            raise APIException(detail="发生未知错误")
        finally:
            read_event_connector.close()
        return APIResponse(results=data)


class EntryLogView(GenericViewSet,
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin):
    authentication_classes = [JWTAuthentication]
    permission_classes = [DjangoModelPermissions]
    queryset = LogEntry.objects.all()
    serializer_class = LogEntrySerializer
    pagination_class = CostumePageNumberPagination


class WebSocketView:
    # @accept_websocket 处理websocket和HTTP请求该装饰器用的较多
    # @require_websocket 仅处理websocket请求，拒绝HTTP请求
    # request.is_websocket() 如果请求类型是websocket，返回True，否则返回False 通常与 @accept_websocket装饰器搭配
    # request.websocket 当websocket请求建立后，该请求具有一个websocket属性，可以通过该属性进行通信，如果request.is_websocket()
    # 是False，则这个属性为None。
    # request.websocket.wait() 阻塞接收消息
    # request.websocket.read() 非阻塞接收消息
    # request.websocket.count_messages() 返回队列中的消息数量
    # request.websocket.has_messages() 如果有新消息返回True，否则返回False
    # request.websocket.send() 向客户端发送bytes类型的数据
    # request.websocket.close() 服务器端主动关闭websocket服务
    # request.websocket.iter() websocket迭代器

    @classmethod
    def as_view(cls):
        @require_websocket
        def view(request):
            if request.websocket:
                data = request.websocket.wait()
                if data:
                    data = data.decode()
                    if data in ['all.log', 'its800.log', 'error.log']:
                        file_path = os.path.join(BASE_DIR, 'log', data)
                        with open(file_path, 'r') as file_obj:
                            file_obj.seek(0, 2)
                            while 1:
                                line = file_obj.readline().strip()
                                if line:
                                    request.websocket.send(line.encode())
                                time.sleep(0.01)
                                if request.websocket.has_messages() and request.websocket.wait().decode() == 'close':
                                    request.websocket.close()
                                    return Response({'code': 101, 'message': 'close websocket'})

        return view
