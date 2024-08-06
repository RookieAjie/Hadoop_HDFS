"""
URL configuration for Haoop_HDFS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from hdfs_analyze import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.cluster),

    path('cluster/', views.cluster),

    path('cluster/add/', views.cluster_add),

    path('cluster/<int:cluster_num>/delete/', views.cluster_delete),

    path('<int:cluster_num>/clusterinfo/', views.cluster_info),

    path('cluster/nodes/', views.cluster_nodes),

    path('cluster/nodes/list/', views.cluster_nodes_list),

    path('cluster/start-celery/', views.cluster_start_celery),

    path('cluster/stop-celery/', views.cluster_stop_celery),
]
