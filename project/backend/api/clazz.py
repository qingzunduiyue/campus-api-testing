from typing import Optional

from fastapi import APIRouter
from pydantic import create_model,Field
from tortoise.contrib.pydantic import pydantic_model_creator

from api.admin import AdminPydantic
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Clazz

router = APIRouter(prefix="/clazz")

ClazzPydantic = pydantic_model_creator(Clazz)
ClazzCreatePydantic = create_model(
    "ClazzCreatePydantic",
    **{
        name: (Optional[field.annotation], None)
        for name, field in  ClazzPydantic.model_fields.items()
    },
    major_id = (Optional[int], Field(None,alias="majorId")),

)


# 新增
@router.post("/add")
#异步框架
async def add(clazz_create_pydantic: ClazzCreatePydantic):
    #判断班级编号是否重复
    db_clazz = await Clazz.get_or_none(no=clazz_create_pydantic.no)
    if db_clazz is not None:
        raise CustomException("班级编号重复")
    #将参数转化为字典数据
    create_data = clazz_create_pydantic.model_dump(exclude_unset=True, exclude={"id"})#不需要传id
    await Clazz.create(**create_data)  #id =xxx,name =xxx
    return Result.success()

#更新
@router.put("/update")
async def update(clazz_create_pydantic: ClazzCreatePydantic):
    if clazz_create_pydantic.id is None:
        raise CustomException("缺少参数ID")
    #将参数转化为字典数据
    create_data = clazz_create_pydantic.model_dump(exclude_unset=True,exclude={"id"})
    await Clazz.filter(id=clazz_create_pydantic.id).update(**create_data)
    return Result.success()


#删除
@router.delete("/delete/{clazz_id}")
async def delete(clazz_id: int):
    await Clazz.filter(id=clazz_id).delete()
    return Result.success()


#单个查询
@router.get("/selectById/{clazz_id}")
async def selectByid(clazz_id: int):
    clazz = await Clazz.get_or_none(id=clazz_id)
    return Result.success(clazz)

#查询所有(条件查询）
@router.get("/selectAll")
async def selectAll(name:str =""):
    clazz_list = await Clazz.filter(name__contains = name)# 对name模糊查询
    return Result.success(clazz_list)

#分页查询
@router.get("/selectPage")
async def selectAll(name:str ="", pageNum:int =1, pageSize:int =10):
    # name__contains表示根据name进行模糊查询  prefetch_related 关联查询到 major模块的数据
    query = Clazz.filter(name__contains=name).prefetch_related("major")
    clazz_list = await query.offset((pageNum - 1)*pageSize).limit(pageSize)
    total = await query.count()
    #转成字典数据
    clazz_dict_list = [
        {
            **ClazzPydantic.model_validate(clazz).model_dump(),
            "majorId": clazz.major.id if clazz.major else None,
            "majorName": clazz.major.name if clazz.major else None
        }
            for clazz in clazz_list
    ]
    page_info = PageInfo(list=clazz_dict_list,total=total)
    return Result.success(page_info)