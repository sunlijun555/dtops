# -*- coding:utf-8 -*-
"""
作者：slj
文件名称：constants.py
日期：2022年06月22日 16:49
"""


class HostConfig:

    ip = '100.100.69.13'
    port = 22
    username = 'root'
    password = 'broadxt333'
    its800_save_path = '/mnt/its800'
    scheduler_its800_save_path = '/mnt/scheduler/its800'

    download_save_path = '/home/project/download'
    # download_save_path = './download'
    upload_save_path = '/home/project/upload'
    px_save_path = '/mnt/px'

    local_save_path = '/mnt/local_case_file'
    # local_save_path = './local_case_file'

    drsu_table = 'traffic_report_obstacle_drsu'
    drc_table = 'traffic_report_obstacle_2d'
    event_table = 'traffic_event'

    @classmethod
    def get_pg_conf(cls):
        user = 'postgres'
        password = 123456
        port = 5433
        dbname = 'meta_data'
        return [user, password, cls.ip, port, dbname]

    # dra,drc,crm事件数据备份数据库配置信息
    PROJECT_DB_CONF = {
        "jichang_hiway": {
            'user': 'postgres',
            'password': '123456',
            'host': '172.16.3.6',
            'port': 5432,
            'dbname': 'meta_data',
        },
        "huhangyong": {
            "user": "postgres",
            "password": "123456",
            'host': '172.16.3.6',
            "port": 5432,
            "dbname": "huhangyong",
        },
        "hangqian_hiway": {
            'user': 'postgres',
            'password': '123456',
            'host': '100.100.69.13',
            'port': 5433,
            'dbname': 'meta_data',
        }
    }

    TRAJECTORY_EDIT_CONF = {
        'jichang_hiway': {
            # 'user': 'postgres',
            # 'password': 'postgres',
            # 'host': 'localhost',
            'user': 'postgres',
            'password': '123456',
            'host': '172.16.3.6',
            'port': 5432,
            'dbname': 'meta_data',
            'trajectory_drc_table': 'traffic_report_trajectory_drc_edit',
            'trajectory_dra_table': 'traffic_report_trajectory_dra'
        },
        "hangqian_hiway": {
            'user': 'postgres',
            'password': '123456',
            'host': '100.100.69.13',
            'port': 5433,
            'dbname': 'meta_data',
            'trajectory_drc_table': 'traffic_report_trajectory_drc_edit',
            'trajectory_dra_table': 'traffic_report_trajectory_dra'
        }
    }


class Ivs3800Config:
    ip = '100.100.69.15'
    username = 'yunwei'
    password = 'broadxt333'

    videos_path = '/mnt/3800/videos'
    # videos_path = '/home/project/videos'
    # videos_path = '../videos'


# DRA/DRC数据来源数据库配置信息
DR_DB_CONF = {
  "jichang_hiway": {
    "host": "10.10.43.6",
    "user": "DRCRM",
    "password": "CRM_jcgs,",
    "obs_dbname": "meta_data",
    "event_dbname": "crm_dsls_event",
    "port": 5431,
    "drc_table": "traffic_report_obstacle_2d",
    "drsu_table": "traffic_report_obstacle_drsu",
    "event_table": "traffic_event"
  },
  "huhangyong": {
    "host": "172.16.20.81",
    "user": "postgres",
    "password": "broadxt333",
    "obs_dbname": "meta_data",
    "port": 5432,
    "drc_table": "traffic_report_obstacle_2d",
    "drsu_table": "traffic_report_obstacle_drsu"
  },
    "hangqian_hiway":{
        "host": "100.100.69.5",
        "user": "DRCRM",
        "password": "123456",
        "obs_dbname": "meta_data_not_tcdb",
        "port": 5432,
        "drc_table": "traffic_report_obstacle_2d",
        "drsu_table": "traffic_report_obstacle_drsu"
    }
}

# crm事件数据来源数据库配置信息
EVENT_ID_DB_CONF = {
    "jichang_hiway": {
        "host": "10.10.43.6",
        "user": "DRCRM",
        "password": "CRM_jcgs,",
        "event_dbname": "crm_dsls_event",
        "port": 5432,
        "event_table": "traffic_event"
    },
    "huhangyong": {
        "host": "172.16.20.83",
        "user": "postgres",
        "password": "broadxt333",
        "event_dbname": "crm_dsls_event",
        "port": 5432,
        "event_table": "traffic_event"
    },
    "hangqian_hiway":{
        "host": "100.100.69.5",
        "user": "DRCRM",
        "password": "123456",
        "event_dbname": "crm_dsls_event",
        "port": 5432,
        "event_table": "traffic_event"
    }
}

# its800主机信息
ITS800_CONFIG = {
    "jichang_hiway": {
        "port": 22,
        "username": "admin",
        "password": "jichang@333",
        "su_password": "broadxt12#$"
    },
    "huhangyong": {
        "port": 22,
        "username": "admin",
        "password": "huhangyong@333",
        "su_password": "broadxt12#$"
    }
}

# 像素偏差数据服务器配置信息
PX_BIAS_CONF = {
    "jichang_hiway": {
        'user': 'broadxt',
        'password': 'broadxt333',
        'su_password': 'broadxt333',
        'host': '10.10.43.4',
        'port': 22
    }
}
