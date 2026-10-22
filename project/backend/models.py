from tortoise.models import Model
from tortoise import fields


class Admin(Model):
    id = fields.IntField(pk=True, null=False)
    username = fields.CharField(max_length=255, null=True)
    password = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=255, null=True)
    role = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'admin'

class Major(Model):
    #专业模块
    id = fields.IntField(pk=True, null=False) #pk：是否为主键
    no = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    college = fields.CharField(max_length=255, null=True)

    class Meta:
        table = 'major'


class Clazz(Model):
    #班级模块
    id = fields.IntField(pk=True, null=False) #pk：是否为主键
    no = fields.CharField(max_length=255, null=True)
    name = fields.CharField(max_length=255, null=True)
    teacher = fields.CharField(max_length=255, null=True)
    major = fields.ForeignKeyField('models.Major', null=True)

    class Meta:
        table = 'clazz'