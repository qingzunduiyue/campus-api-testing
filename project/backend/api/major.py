from typing import Optional

from fastapi import APIRouter
from pydantic import create_model
from tortoise.contrib.pydantic import pydantic_model_creator

from api.admin import AdminPydantic
from common.exception_handler import CustomException
from common.result import Result, PageInfo
from models import Major

router = APIRouter(prefix="/major")

MajorPydantic = pydantic_model_creator(Major)
MajorCreatePydantic = create_model(
    "MajorPydantic",
    **{
        name: (Optional[field.annotation], None)
        for name, field in  MajorPydantic.model_fields.items()
    }
)


# 新增
@router.post("/add")
#异步框架
async def add(major_create_pydantic: MajorCreatePydantic):
    #判断专业代码是否重复
    db_major = await Major.get_or_none(no=major_create_pydantic.no)
    if db_major is not None:
        raise CustomException("专业代码重复")
    #将参数转化为字典数据
    create_data = major_create_pydantic.model_dump(exclude_unset=True, exclude={"id"})#不需要传id
    await Major.create(**create_data)  #id =xxx,name =xxx
    return Result.success()

#更新
@router.put("/update")
async def update(major_create_pydantic: MajorPydantic):
    if major_create_pydantic.id is None:
        raise CustomException("缺少参数ID")
    #判断专业代码是否重复
    db_major = await Major.get_or_none(no=major_create_pydantic.no)
    if db_major is not None and db_major.id != major_create_pydantic.id:
        raise CustomException("专业代码重复")
    #将参数转化为字典数据
    create_data = major_create_pydantic.model_dump(exclude_unset=True,exclude={"id"})
    await Major.filter(id=major_create_pydantic.id).update(**create_data)
    return Result.success()


#删除
@router.delete("/delete/{major_id}")
async def delete(major_id: int):
    await Major.filter(id=major_id).delete()
    return Result.success()


#单个查询
@router.get("/selectById/{major_id}")
async def selectByid(major_id: int):
    major = await Major.get_or_none(id=major_id)
    return Result.success(major)

#查询所有(条件查询）
@router.get("/selectAll")
async def selectAll(name:str =""):
    major_list = await Major.filter(name__contains = name)# 对name模糊查询
    return Result.success(major_list)

#分页查询
@router.get("/selectPage")
async def selectAll(name:str ="", pageNum:int =1, pageSize:int =10):
    query = Major.filter(name__contains = name)
    major_list = await query.offset((pageNum - 1)*pageSize).limit(pageSize)
    total = await query.count()
    major_dict_list = [
        MajorPydantic.model_validate(major).model_dump()
        for major in major_list
    ]
    page_info = PageInfo(list=major_dict_list,total=total)
    return Result.success(page_info)