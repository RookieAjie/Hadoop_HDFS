from django.db import models


# Create your models here.
class Cluster(models.Model):
    """ 集群信息 """
    id = models.BigAutoField(primary_key=True, verbose_name='集群列表序号')
    cluster_name = models.CharField(max_length=50, verbose_name='集群名称')
    # cluster_nn_ip = models.TextField(verbose_name='集群nn ip')
    cluster_id = models.CharField(max_length=50, verbose_name='集群id', default='NULL', unique=True)


class ClusterInfo(models.Model):
    """ 集群信息 """
    cluster_id = models.ForeignKey(to='Cluster', to_field='id', on_delete=models.CASCADE, verbose_name='集群id')
    total_capacity = models.DecimalField(max_digits=10,decimal_places=3)
    used_capacity = models.DecimalField(max_digits=10,decimal_places=3)
    remaining_capacity = models.DecimalField(max_digits=10,decimal_places=3)


class DNInfo(models.Model):
    """ 节点信息 """
    total_nodes = models.IntegerField()
    live_nodes = models.IntegerField()
    dead_nodes = models.IntegerField()
    decommissioned_nodes = models.IntegerField()
    decommissioning_nodes = models.IntegerField()
    cluster_id = models.ForeignKey(to='Cluster', to_field='id', on_delete=models.CASCADE,
                                   verbose_name='集群id')


class DNList(models.Model):
    """ 对应状态节点列表 """
    node_list = models.TextField(verbose_name='对应状态节点列表')
    status = models.CharField(max_length=50)
    cluster_id = models.ForeignKey(to='Cluster', to_field='id', on_delete=models.CASCADE, verbose_name='所属集群')


class NNInfo(models.Model):
    """ NN信息 """
    nn_ip = models.CharField(max_length=50, verbose_name='NN ip')
    nn_role = models.CharField(max_length=30, verbose_name='NN role', default='active')
    cluster_id = models.ForeignKey(to='Cluster', to_field='id', on_delete=models.CASCADE, verbose_name='所属集群')