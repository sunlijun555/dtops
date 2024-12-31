# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：utils.py
日期：2022年06月15日 13:39
"""
# -*- coding: utf-8 -*-
import logging
import json
import os
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import tarfile
import paramiko
from rtops.settings import BASE_DIR
from rtops.settings import SECRET_KEY
import jwt

logger = logging.getLogger(__name__)


def create_token(payload, timeout=1):
    salt = SECRET_KEY
    headers = {
        'type': 'jwt',
        'alg': 'HS256'
    }
    # 构造payload
    payload['exp'] = datetime.now() + timedelta(days=timeout)
    token = jwt.encode(payload=payload, key=salt, algorithm='HS256', headers=headers)
    return token.encode()


def parse_node(project):
    node_info_file_path = os.path.join(BASE_DIR, 'config', 'node_info.json')
    if not os.path.exists(node_info_file_path):
        return f"{node_info_file_path} 文件不存在！"
    with open(node_info_file_path, 'r') as file_r:
        content = json.load(file_r)
        project_content = content.get(project)
    return project_content


class SSH:

    def __init__(self, host, port, username, password, su_password=None):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._su_password = su_password

        self._ssh_client = None
        self._invoke_shell = None

        self._transport = None
        self._sftp = None

    def connect_sftp(self):
        self._transport = paramiko.Transport((self._host, self._port))
        self._transport.connect(username=self._username, password=self._password)
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)

    def download_file(self, remote_path, local_path):
        self._sftp.get(remote_path, local_path)

    def close_sftp(self):
        self._transport.close()

    def connect(self, connect_invoke_shell=False):
        try:
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh_client.connect(hostname=self._host, port=self._port,
                                     username=self._username, password=self._password)
            if connect_invoke_shell:
                self._invoke_shell = self._ssh_client.invoke_shell()
                time.sleep(2)
                self._invoke_shell.recv(1024).decode()
        except Exception as error:
            logger.error(f"连接服务器出错: {error}")

    def exec_invoke_shell_command(self, command, end="Euler:"):
        """
        执行invoke_shell的命令，一发一收
        @param command: 命令
        @param end: 命令结束符
        @return: 命令返回结果
        """
        try:
            self._invoke_shell.send(f"{command}\n")
            time.sleep(1)
            data = ""
            count = 0
            while True:
                part = self._invoke_shell.recv(1024).decode()
                logger.info(f"接收数据: {part}")
                if not part:
                    count += 1
                data += part
                if end in part or count > 3:
                    break
            return data
        except OSError as os_error:
            logger.error(os_error)
            return None

    def exec_client_command(self, command):
        stdin, stdout, stderr = self._ssh_client.exec_command(command)
        return stdout.read().decode()

    def switch_root_user(self):
        assert self._invoke_shell is not None
        self.exec_invoke_shell_command("su", "Password")
        self.exec_invoke_shell_command(f"{self._su_password}")

    def close(self):
        self._ssh_client.close()
        if hasattr(self._invoke_shell, 'close'):
            self._invoke_shell.close()


def make_tar_gz(filename, source_dir):
    with tarfile.open(filename, "w:gz") as tar_gz:
        tar_gz.add(source_dir, arcname=os.path.basename(source_dir))


def compute_date_range(begin_date, end_date):
    if begin_date.count('-') > 3 and end_date.count('-') > 3:
        begin_date = begin_date.rsplit('-', 3)[0]
        end_date = end_date.rsplit('-', 3)[0]
    dates = []
    dt = datetime.strptime(begin_date, "%Y-%m-%d")
    date = begin_date[:]
    while date <= end_date:
        dates.append(date)
        dt = dt + timedelta(1)
        date = dt.strftime("%Y-%m-%d")
    return dates


class PGConnector:

    def __init__(self, user, password, host, port, dbname):
        self._user = user
        self._password = password
        self._host = host
        self._port = port
        self._dbname = dbname
        self._engine = None
        self._conn = None
        self._session = None

    def connect(self):
        self._engine = create_engine(f'postgresql://{self._user}:{self._password}'
                                     f'@{self._host}:{self._port}/{self._dbname}')
        self._conn = self._engine.connect()

    def close(self):
        self._engine.dispose()

    def begin(self):
        """开始事务"""
        self._session = self._conn.begin()

    def commit(self):
        """事务提交"""
        self._session.commit()

    def rollback(self):
        """事务回滚"""
        self._session.rollback()

    def execute_sql(self, sql):
        self._engine.execute(sql)

    def to_sql(self, dataframe, table_name):
        """dataframe写入数据库"""
        dataframe.to_sql(table_name, self._conn, if_exists='append', index=False, chunksize=100000)
