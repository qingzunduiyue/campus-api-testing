import importlib
import pkgutil

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from common.exception_handler import CustomException
from common.result import Result
from models import Admin


class Account(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = None
    username: str = None
    password: str = None
    newPassword: str = None
    role: str = None
    name: str = None
    avatar: str = None


api_router = APIRouter()


# 登录
@api_router.post("/login")
async def login(account: Account):
    if account.role != '管理员':
        raise CustomException("不支持的用户角色")
    if account.role == '管理员':
        admin = await Admin.get_or_none(username=account.username)
        if admin is None:
            raise CustomException("账号或密码错误")
        if admin.password != account.password:
            raise CustomException("账号或密码错误")
        account = Account.model_validate(admin)
    return Result.success(account)


# 修改密码
@api_router.put("/updatePassword")
async def update_password(account: Account):
    if account.role == '管理员':
        admin = await Admin.get_or_none(id=account.id)
        if admin is None:
            raise CustomException("未找到用户")
        if admin.password != account.password:
            raise CustomException("原密码错误")
        if admin.password == account.newPassword:
            raise CustomException("新密码不能原密码跟相同")
        await Admin.filter(id=admin.id).update(password=account.newPassword)
    return Result.success(account)


# 自动导入当前目录下的所有模块
for _, module_name, _ in pkgutil.iter_modules(__path__, __name__ + "."):
    module = importlib.import_module(module_name)
    if hasattr(module, "router"):
        # 假设每个端点文件都有一个 router 变量
        api_router.include_router(module.router)
