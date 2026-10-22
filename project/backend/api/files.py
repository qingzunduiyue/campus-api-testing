from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, Request
from starlette.responses import FileResponse
from common.exception_handler import CustomException
from common.result import Result
from settings import UPLOAD_DIR

router = APIRouter(prefix='/files')

@router.post('/upload')
async def upload_file(request: Request, file: UploadFile = File(...)):
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.txt'}:
        raise CustomException('演示上传仅支持图片和 txt 文件')
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise CustomException('文件大小不能超过 5 MiB')
    filename = uuid4().hex + suffix
    (UPLOAD_DIR / filename).write_bytes(data)
    return Result.success(str(request.url_for('download_file', filename=filename)))

@router.get('/download/{filename}', name='download_file')
async def download_file(filename: str):
    candidate = (UPLOAD_DIR / filename).resolve()
    if candidate.parent != UPLOAD_DIR or not candidate.is_file():
        raise CustomException('文件不存在')
    return FileResponse(candidate, filename=filename)
