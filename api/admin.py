from django.contrib import admin
from api.models import Project

# Register your models here.

admin.site.site_header = 'Dtops后台管理'
admin.site.site_title = 'Dtops后台管理'


# admin.site.index_title = '3'


def rename(newname):
    def decorator(fn):
        fn.__name__ = newname
        return fn

    return decorator


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'project_name', 'label_name']
