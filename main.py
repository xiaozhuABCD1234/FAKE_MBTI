from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
import shutil
import os
import io
from utils import get_low_poly_image
import cv2
import numpy as np
from fastapi.staticfiles import StaticFiles

app = FastAPI()
# 挂载静态文件目录（用于 CSS/JS/图片等资源）
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/low_poly_image/")
async def low_poly_image(
    file: UploadFile = File(...),
    num_points: int = Form(1000),
    detail_level: int = Form(5),
):
    allowed_content_types = {"image/jpeg", "image/png"}
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Invalid image format")

    # 将上传的文件内容读取到内存中
    file_content = await file.read()
    # 使用 OpenCV 加载图像
    nparr = np.frombuffer(file_content, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="Failed to load image")

    # 调用 get_low_poly_image 函数处理图像
    processed_image = get_low_poly_image(
        image, num_points=num_points, detail_level=detail_level
    )

    # 将处理后的图像编码为 JPEG 格式
    _, encoded_image = cv2.imencode(".jpg", processed_image)

    # 使用 StreamingResponse 返回处理后的图像
    return StreamingResponse(
        io.BytesIO(encoded_image.tobytes()),
        media_type="image/jpeg",
        headers={"Content-Disposition": "attachment; filename=low_poly_image.jpg"},
    )


# 直接返回 index.html
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


@app.get("/favicon.ico")
async def ico():
    return FileResponse("static/favicon.ico")


@app.get("/main.js")
async def js():
    return FileResponse("static/main.js")


@app.get("/style.css")
async def css():
    return FileResponse("static/style.css")
