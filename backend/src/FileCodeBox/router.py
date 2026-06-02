from fastapi import APIRouter, Depends
from pydantic import IPvAnyAddress

from src.Auth.dependencies import get_current_user
from src.FileCodeBox.config import ERROR_COUNT, ERROR_MINUTE, UPLOAD_COUNT, UPLOAD_MINUTE
from src.FileCodeBox.dependencies import IPRATELimit
from src.FileCodeBox.schemas import ShareDataSchema

router = APIRouter(
    prefix="/api/fileCodeBox",
    tags=["File Code Box"],
    # dependencies=[Depends(get_current_user)],
)


error_ip_limit = IPRATELimit(ERROR_COUNT, ERROR_MINUTE)
upload_ip_limit = IPRATELimit(UPLOAD_COUNT, UPLOAD_MINUTE)


@router.post("/share", description="share files")
async def share_file(file_model: ShareDataSchema, ip: IPvAnyAddress = Depends(error_ip_limit), current_user=Depends(get_current_user)):
    upload_ip_limit.add_ip(ip)
    return 1
