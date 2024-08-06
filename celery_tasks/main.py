# -*- coding: UTF8 -*- #
"""
@filename:main.py
@author:Ajie
@time:2024-07-23
"""
from celery import Celery
import os
from datetime import timedelta
from celery.schedules import crontab

# 读取Django配置
os.environ['DJANGO_SETTINGS_MODULE'] = 'Haoop_HDFS.settings'

# 创建Celery对象，指定配置
app = Celery("Ajie", backend="redis://127.0.0.1:6379/1")

# celery项目配置：worker代理人，指定任务存储到哪里
app.config_from_object('celery_tasks.config')

app.conf.timezone = 'Asia/Shanghai'
app.conf.enable_utc = False

# 加载可用任务
app.autodiscover_tasks([
    'celery_tasks.getInfo',
])

app.conf.beat_schedule = {
    'get_DNInfo': {
        'task': 'celery_tasks.getInfo.tasks.get_DN_info_onSchedule',
        'schedule': timedelta(seconds=5),
        'args': ()
    },
    'get_ClusterInfo': {
        'task': 'celery_tasks.getInfo.tasks.get_Cluster_info_onSchedule',
        'schedule': timedelta(seconds=10),
        'args': ()
    }
}
