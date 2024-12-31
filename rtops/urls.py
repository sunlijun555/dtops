"""rtops URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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
from django.conf.urls import url, include
from rest_framework import routers
from api.views import generic, user
from django.contrib import admin
from rest_framework.documentation import include_docs_urls
from django.views import static  # 新增
from django.conf import settings  # 新增


router = routers.DefaultRouter()
router.register(r'users', user.UserViewSet)
router.register(r'groups', user.GroupViewSet)
router.register(r'permission', user.PermissionViewSet)
router.register(r'project', generic.ProjectListViewSet)
router.register(r'entry_log', generic.EntryLogView)


# 使用自动URL路由连接我们的API。
# 另外，我们还包括支持浏览器浏览API的登录URL。
urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^admin/', admin.site.urls),
    url(r'^static/(?P<path>.*)$', static.serve, {'document_root': settings.STATIC_ROOT}, name='static'),
    # 接口文档
    url('docs/', include_docs_urls(title='接口文档')),
    # APIView
    url(r'^api/userinfo', user.UserInfoView.as_view()),
    url(r'^api/show_node_its800_file', generic.ShowNodeIts800File.as_view()),
    url(r'^login/$', generic.LoginView.as_view()),
    url(r'^api/node', generic.NodeActiveListView.as_view()),
    url(r'^api/its800_query/', generic.Its800DataTreeView.as_view()),
    url(r'^api/its800_download/', generic.Its800DownloadView.as_view()),
    url(r'^api/its800_upload/', generic.Its800UploadView.as_view()),
    url(r'^api/task_status/', generic.TaskStatusView.as_view()),
    url(r'^api/data_to_excel/', generic.DATAToExcelView.as_view()),
    url(r'^api/parse_event/', generic.EventParserView.as_view()),
    url(r'^api/local_data_import/', generic.LocalDataImportView.as_view()),
    # ws
    url(r'^echo/', generic.WebSocketView.as_view()),
]
