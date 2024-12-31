import uuid

from django.db import models


# Create your models here.


# 基类：是抽象的(不会完成数据库迁移)，目的是提供共有字段的
class BaseModel(models.Model):
    create_time = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    update_time = models.DateTimeField(auto_now=True, blank=True, null=True)
    file = models.FileField

    class Meta:
        abstract = True  # 必须完成该配置


class Project(models.Model):
    project_name = models.CharField(max_length=30, verbose_name="项目名称", unique=True)
    label_name = models.CharField(max_length=20, verbose_name="项目中文名称", unique=True)

    class Meta:
        verbose_name = "项目"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.label_name

