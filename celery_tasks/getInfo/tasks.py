# -*- coding: UTF8 -*- #
"""
@filename:tasks.py
@author:Ajie
@time:2024-07-23
"""
from hdfs_analyze import views
from celery_tasks.main import app
from hdfs_analyze import models
import redis

r = redis.Redis(host='localhost', port=6379, db=0)


def get_present_cluster_ip():
    present_num = r.get('present_num')
    if present_num is None:
        cluster_ip = models.NNInfo.objects.filter(cluster_id_id=models.Cluster.objects.first().cluster_id).first().nn_ip
    else:
        cluster_ip = models.NNInfo.objects.filter(cluster_id_id=present_num).first().nn_ip

    # print("present_num is %s" % present_num)
    # print("cluster_ip is %s" % cluster_ip)
    return cluster_ip


@app.task
def get_DN_info_onSchedule():
    cluster_ip = get_present_cluster_ip()
    data = views.get_hdfs_info(cluster_ip)
    if data is None:
        print('data is None')
        return 'Data is None'

    views.cluster_DN_info_update(data)
    return 'DNInfo任务完成'


@app.task
def get_Cluster_info_onSchedule():
    cluster_ip = get_present_cluster_ip()
    data = views.get_hdfs_info(cluster_ip)
    if data is None:
        print('data is None')
        return 'Data is None'
    views.cluster_info_update(data)
    return 'ClusterInfo任务完成'
