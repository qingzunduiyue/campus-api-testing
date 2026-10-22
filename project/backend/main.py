from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from api import api_router
from common.exception_handler import setup_exceptions
from common.result import Result
from models import Admin, Major, Clazz
from settings import TORTOISE_ORM

@asynccontextmanager
async def lifespan(app):
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        await Tortoise.generate_schemas(safe=True)
        if os.getenv('SEED_DEMO', 'true').lower() == 'true':
            await Admin.get_or_create(username='demo_admin', defaults={
                'password': 'Demo12345!', 'name': '演示管理员', 'role': '管理员'})
            major, _ = await Major.get_or_create(no='CS-DEMO', defaults={
                'name': '计算机科学（示例）', 'college': '示例学院'})
            await Clazz.get_or_create(no='CLASS-DEMO', defaults={
                'name': '示例一班', 'teacher': '示例教师', 'major_id': major.id})
        yield
    finally:
        await Tortoise.close_connections()

app = FastAPI(title='教学管理系统 · 本地演示', lifespan=lifespan)
app.add_middleware(CORSMiddleware,
    allow_origins=['http://localhost:5174', 'http://127.0.0.1:5174'],
    allow_methods=['*'], allow_headers=['*'])
app.include_router(api_router)
setup_exceptions(app)

@app.get('/')
async def root():
    return Result.success({'application': 'campus-management', 'mode': 'local-demo'})
