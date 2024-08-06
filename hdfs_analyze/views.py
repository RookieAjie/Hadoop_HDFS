import json
import subprocess

import psutil
import requests
import validators
from django.shortcuts import render, redirect
from collections import defaultdict
from hdfs_analyze import models
import redis

# 使用redis缓存存储一下当前正在检测的集群编号
r = redis.Redis(host='localhost', port=6379, db=0)


def get_decommissioned_nodes(nodes_str):
    """解析节点列表JSON数据，提取Decommissioned状态的节点信息"""
    if nodes_str == '':
        return None

    try:
        # 将 JSON 字符串转换为字典
        nodes_dict = json.loads(nodes_str)

        # 创建一个空列表来存储格式化的节点信息
        decommissioned_nodes = []

        # 遍历字典中的每个节点
        for node_id, node_info in nodes_dict.items():
            # 检查 adminState 是否为 Decommissioned
            if node_info.get('adminState') == 'Decommissioned':
                # 提取 IP 地址和端口号
                info_addr = node_info.get('infoAddr', 'Unknown address')

                # 格式化节点信息并添加到列表中
                formatted_node = f"{node_id} ({info_addr})"
                decommissioned_nodes.append(formatted_node)

        # 返回格式化的节点信息列表
        return decommissioned_nodes

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return None


# 清洗获取到的数据
def extract_node_info(nodes_str):
    """解析得到的节点列表，得到关键数据"""
    if nodes_str == '':
        return None

    try:
        # 将 JSON 字符串转换为字典
        live_nodes_dict = json.loads(nodes_str)

        # 创建一个空列表来存储格式化的节点信息
        formatted_nodes = []

        # 遍历字典中的每个节点
        for node_id, node_info in live_nodes_dict.items():
            # 提取 IP 地址和端口号
            if 'infoAddr' in node_info:
                ip_addr = node_info['infoAddr']
            else:
                ip_addr = node_info.get('xferaddr', 'Unknown address')

            # 格式化节点信息并添加到列表中
            formatted_node = f"{node_id} ({ip_addr})"
            formatted_nodes.append(formatted_node)

        # 打印格式化的节点信息列表
        return formatted_nodes

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")


# 获取hdfs信息
def get_hdfs_info(cluster_nn_ip):
    url = "http://" + cluster_nn_ip + ":9870/jmx"

    # 验证合法性
    if not validators.url(url):
        return None

    response = requests.get(url)

    # 判断是否成功访问到数据
    if response.status_code != 200:
        print("Failed to retrieve HDFS info.")
        return None

    # 若成功，则将其格式化为json
    data = json.loads(response.text)

    # 初始化要返回的数据
    cluster_id = None
    live_nodes_list = None
    dead_nodes_list = None
    decommissioning_nodes_list = None
    total_capacity = None
    used_capacity = None
    remaining_capacity = None
    total_nodes_num = None
    live_nodes_num = None
    dead_nodes_num = None
    decom_live_nodes_num = None
    decom_dead_nodes_num = None
    decommissioning_nodes_num = None
    decommissioned_nodes_list = None
    nn_state = None

    for bean in data['beans']:
        if bean['name'] == 'Hadoop:service=NameNode,name=NameNodeInfo':
            cluster_id = bean['ClusterId']
            live_nodes_list = extract_node_info(bean['LiveNodes'])
            decommissioned_nodes_list = get_decommissioned_nodes(bean['LiveNodes'])
            dead_nodes_list = extract_node_info(bean['DeadNodes'])
            decommissioning_nodes_list = extract_node_info(bean['DecomNodes'])

        if bean['name'] == 'Hadoop:service=NameNode,name=FSNamesystem':
            total_capacity = bean['CapacityTotal'] / 1024 / 1024 / 1024
            used_capacity = bean['CapacityUsed'] / 1024 / 1024 / 1024
            remaining_capacity = bean['CapacityRemaining'] / 1024 / 1024 / 1024
            live_nodes_num = bean['NumLiveDataNodes']
            dead_nodes_num = bean['NumDeadDataNodes']
            decom_live_nodes_num = bean['NumDecomLiveDataNodes']
            decom_dead_nodes_num = bean['NumDecomDeadDataNodes']
            decommissioning_nodes_num = bean['NumDecommissioningDataNodes']
            total_nodes_num = (live_nodes_num + dead_nodes_num)

        if bean['name'] == 'Hadoop:service=NameNode,name=NameNodeStatus':
            nn_state = bean['State']

    return {
        'cluster_id': cluster_id,
        'live_nodes_list': live_nodes_list,
        'dead_nodes_list': dead_nodes_list,
        'decommissioning_nodes_list': decommissioning_nodes_list,
        'total_capacity': total_capacity,
        'used_capacity': used_capacity,
        'remaining_capacity': remaining_capacity,
        'total_nodes_num': total_nodes_num,
        'live_nodes_num': live_nodes_num,
        'dead_nodes_num': dead_nodes_num,
        'decom_live_nodes_num': decom_live_nodes_num,
        'decom_dead_nodes_num': decom_dead_nodes_num,
        'decommissioning_nodes_num': decommissioning_nodes_num,
        'decommissioned_nodes_list': decommissioned_nodes_list,
        'nn_state': nn_state
    }


# 格式化节点列表
def extract_node_list(data):
    if data == ['[]'] or data == []:
        return 'null'
    else:
        formatted_data = ', '.join([string.strip().replace("'", "") for string in data])
        return formatted_data


def cluster(request):
    if request.method == "GET":
        queryset = models.Cluster.objects.all()
        if queryset.exists():
            present_num = queryset.first().id
            r.set('present_num', present_num)
            print("cluster num is %s" % present_num)

        return render(request, 'cluster.html', {'cluster': queryset})

    cluster_nn_num = request.POST.get('cluster_nn_num')
    r.set('cluster_nn_num', cluster_nn_num)
    print("cluster num is %s" % r.get('cluster_nn_num'))
    return redirect('/cluster/add/')


def cluster_add(request):
    if request.method == 'GET':
        cluster_num = int(r.get('cluster_nn_num'))
        return render(request, 'cluster_add.html', {'cluster_num': cluster_num})

    # 获取用户POST请求提交的数据
    cluster_num = int(r.get('cluster_nn_num'))
    print("count is %s" % cluster_num)
    # 集群名
    cluster_name = request.POST['clusterName']

    # 集群nn的ip
    cluster_nn_ip = []
    for i in range(cluster_num):
        name = 'clusterNN' + str(i)
        cluster_nn_ip.append(request.POST[name])
        print(cluster_nn_ip[i])

    # 通过jmx查询到数据
    data = get_hdfs_info(cluster_nn_ip[0])

    print(data)
    if data is None:
        print("data is none")
        return redirect('/cluster/')

    # 若数据不为空，将数据分别保存至数据库

    # 若添加的集群id与之前添加的同名，则不允许添加
    if models.Cluster.objects.filter(cluster_id=data['cluster_id']).exists():
        print("已存在该集群!")
        return redirect('/cluster/')

    # 1 保存至 cluster 表
    models.Cluster.objects.create(cluster_id=data['cluster_id'], cluster_name=cluster_name)

    # 2 保存至 clusterInfo 表
    id_foreignkey = models.Cluster.objects.filter(cluster_id=data['cluster_id']).first().id

    models.ClusterInfo.objects.create(cluster_id_id=id_foreignkey,
                                      total_capacity=data['total_capacity'],
                                      used_capacity=data['used_capacity'],
                                      remaining_capacity=data['remaining_capacity'], )

    # 3 保存至 dnInfo 表
    models.DNInfo.objects.create(cluster_id_id=id_foreignkey, total_nodes=data['total_nodes_num'],
                                 live_nodes=data['live_nodes_num'], dead_nodes=data['dead_nodes_num'],
                                 decommissioned_nodes=(data['decom_live_nodes_num'] + data['decom_dead_nodes_num']),
                                 decommissioning_nodes=data['decommissioning_nodes_num'])

    # 4 保存至 dnList 表
    # 进行一下数据清洗
    live_nodes_list = extract_node_list(data['live_nodes_list'])
    dead_nodes_list = extract_node_list(data['dead_nodes_list'])
    decommissioning_nodes_list = extract_node_list(data['decommissioning_nodes_list'])
    decommissioned_nodes_list = extract_node_list(data['decommissioned_nodes_list'])

    models.DNList.objects.create(cluster_id_id=id_foreignkey, node_list=live_nodes_list, status='live_nodes')
    models.DNList.objects.create(cluster_id_id=id_foreignkey, node_list=dead_nodes_list, status='dead_nodes')
    models.DNList.objects.create(cluster_id_id=id_foreignkey, node_list=decommissioning_nodes_list,
                                 status='decommissioning_nodes')
    models.DNList.objects.create(cluster_id_id=id_foreignkey, node_list=decommissioned_nodes_list,
                                 status='decommissioned_nodes')

    # 5 保存至 nnInfo 表
    for ip in cluster_nn_ip:
        obj = get_hdfs_info(ip)
        models.NNInfo.objects.create(cluster_id_id=id_foreignkey, nn_ip=ip, nn_role=obj['nn_state'], )

    return redirect('/cluster/')


def cluster_DN_info_update(data):
    cluster_id_id = models.Cluster.objects.filter(cluster_id=data['cluster_id']).first().id
    # 更新DNInfo 表
    dn_info = models.DNInfo.objects.get(cluster_id_id=cluster_id_id)

    if (dn_info.total_nodes != data['total_nodes_num'] or
            dn_info.live_nodes != data['live_nodes_num'] or
            dn_info.dead_nodes != data['dead_nodes_num'] or
            dn_info.decommissioned_nodes != (data['decom_live_nodes_num'] + data['decom_dead_nodes_num']) or
            dn_info.decommissioning_nodes != data['decommissioning_nodes_num']):
        # 更新信息
        dn_info.total_nodes = data['total_nodes_num']
        dn_info.live_nodes = data['live_nodes_num']
        dn_info.dead_nodes = data['dead_nodes_num']
        dn_info.decommissioned_nodes = data['decom_live_nodes_num'] + data['decom_dead_nodes_num']
        dn_info.decommissioning_nodes = data['decommissioning_nodes_num']
        dn_info.save()
        print("DNInfo 更新完毕!")
    # print("-----------------------------------------------")
    # print("DNInfo 更新后：")
    # print(dn_info.total_nodes)
    # print(dn_info.live_nodes)
    # print(dn_info.dead_nodes)
    # print(dn_info.decommissioned_nodes)
    # print(dn_info.decommissioning_nodes)

    # 更新 DNList 表
    # 进行一下数据清洗
    live_nodes_list = extract_node_list(data['live_nodes_list'])
    dead_nodes_list = extract_node_list(data['dead_nodes_list'])
    decommissioning_nodes_list = extract_node_list(data['decommissioning_nodes_list'])
    decommissioned_nodes_list = extract_node_list(data['decommissioned_nodes_list'])

    # 从数据库查询数据
    dn_list = models.DNList.objects.filter(cluster_id_id=cluster_id_id)

    live_nodes_instance = dn_list.filter(status='live_nodes').first()
    dead_nodes_instance = dn_list.filter(status='dead_nodes').first()
    decommissioning_nodes_instance = dn_list.filter(status='decommissioning_nodes').first()
    decommissioned_nodes_instance = dn_list.filter(status='decommissioned_nodes').first()

    if ((live_nodes_instance.node_list != live_nodes_list or
         dead_nodes_instance.node_list != dead_nodes_list or
         decommissioning_nodes_instance.node_list != decommissioning_nodes_list) or
            decommissioned_nodes_instance.node_list != decommissioned_nodes_list):
        live_nodes_instance.node_list = live_nodes_list
        live_nodes_instance.save()
        dead_nodes_instance.node_list = dead_nodes_list
        dead_nodes_instance.save()
        decommissioning_nodes_instance.node_list = decommissioning_nodes_list
        decommissioning_nodes_instance.save()
        decommissioned_nodes_instance.node_list = decommissioned_nodes_list
        decommissioned_nodes_instance.save()
        print("DNInfo 更新完毕!")


def cluster_info_update(data):
    cluster_id_id = models.Cluster.objects.filter(cluster_id=data['cluster_id']).first().id

    # 更新clusterInfo 表
    cluster_obj = models.ClusterInfo.objects.get(cluster_id_id=cluster_id_id)

    # 检查是否需要更新
    if (cluster_obj.total_capacity != data['total_capacity'] or
            cluster_obj.used_capacity != data['used_capacity'] or
            cluster_obj.remaining_capacity != data['remaining_capacity']):
        cluster_obj.total_capacity = data['total_capacity']
        cluster_obj.used_capacity = data['used_capacity']
        cluster_obj.remaining_capacity = data['remaining_capacity']
        cluster_obj.save()
        print("ClusterInfo 更新完毕!")

    # 更新 NNInfo 表的对应nn状态
    nn_obj = models.NNInfo.objects.filter(cluster_id_id=cluster_id_id)
    for item in nn_obj:
        present_state = get_hdfs_info(item.nn_ip).get('nn_state')
        if item.nn_role != present_state:
            item.nn_role = present_state
            item.save()
            print("NNInfo 表已更新！")


def cluster_delete(request, cluster_num):
    models.Cluster.objects.filter(id=cluster_num).delete()
    return redirect('/cluster/')


def cluster_info(request, cluster_num):
    model = models.Cluster.objects.filter(id=cluster_num).first()
    r.set('present_num', cluster_num)
    # print("cluster num is %s" % cluster_num)

    queryset = models.ClusterInfo.objects.filter(cluster_id_id=model.id)
    nn_queryset = models.NNInfo.objects.filter(cluster_id_id=model.id)
    # print("type(nn_queryset) is %s" % type(nn_queryset))

    return render(request, 'cluster_info.html', {'ClusterInfo': queryset, 'Model': model, 'NNInfo': nn_queryset})


def cluster_nodes(request):
    present_num = r.get('present_num')
    model = models.Cluster.objects.filter(id=present_num).first()

    queryset = models.DNInfo.objects.filter(cluster_id_id=model.id)
    return render(request, 'cluster_nodes.html', {'Model': model, 'DNInfo': queryset})


def cluster_nodes_list(request):
    present_num = r.get('present_num')
    model = models.Cluster.objects.filter(id=present_num).first()

    queryset = models.DNList.objects.filter(cluster_id_id=model.id)
    grouped_items = defaultdict(list)
    for item in queryset:
        grouped_items[item.status].append(item.node_list)

    # Now you can get the lists like this:
    live_nodes = grouped_items['live_nodes']
    dead_nodes = grouped_items['dead_nodes']
    decommissioning_nodes = grouped_items['decommissioning_nodes']
    decommissioned_nodes = grouped_items['decommissioned_nodes']
    # print("live nodes are : %s" % live_nodes)
    # print("dead nodes are : %s" % dead_nodes)
    # print("decommissioning nodes are : %s" % decommissioning_nodes)

    return render(request, 'cluster_nodes_list.html',
                  {'Model': model, 'live_nodes': live_nodes, 'dead_nodes': dead_nodes,
                   'decommissioning_nodes': decommissioning_nodes, 'decommissioned_nodes': decommissioned_nodes})


def cluster_start_celery(request):
    # 启动 Celery worker
    worker = subprocess.Popen(['celery', '-A', 'celery_tasks.main', 'worker', '-l', 'info', '-P', 'eventlet'])

    # 启动 Celery beat
    beat = subprocess.Popen(['celery', '-A', 'celery_tasks.main', 'beat', '-l', 'info'])

    r.set('worker', worker.pid)
    r.set('beat', beat.pid)

    return redirect('/cluster/')


def cluster_stop_celery(request):
    worker = int(r.get('worker'))
    beat = int(r.get('beat'))

    kill(worker)
    kill(beat)
    return redirect('/cluster/')


def kill(proc_pid):
    parent_process = None
    try:
        parent_process = psutil.Process(proc_pid)
    except psutil.NoSuchProcess:
        return

    children = parent_process.children(recursive=True)

    for child in children:
        child.terminate()

    parent_process.terminate()
