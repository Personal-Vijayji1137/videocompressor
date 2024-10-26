from fastapi import FastAPI
import os
import subprocess
from pydantic import BaseModel
import requests
app = FastAPI()
COMPRESS_RATE = 50
output_folder_path = '/app/output_folder'
@app.get("/")
def greet_json():
    return {"Hello": "World!"}

class VideoRequest(BaseModel):
    video_url: str
    video_name: str
    upload_url: str
    image_poster: str
    Image_upload_url: str
    BASE_URL: str
    reels_id: int
    upload_token: str

@app.post("/compress")
def compress_video(video_request: VideoRequest):
    print(video_request)
    video_url = video_request.video_url
    video_name = video_request.video_name
    upload_url = video_request.upload_url
    image_poster = video_request.image_poster
    Image_upload_url = video_request.Image_upload_url
    BASE_URL = video_request.BASE_URL
    reels_id = video_request.reels_id
    upload_token = video_request.upload_token
    trim_video_name = video_name.replace(".mp4","")
    output_file = os.path.join(output_folder_path, f"{trim_video_name}.webm")
    image_file = os.path.join(output_folder_path, f"{image_poster}")
    logo = os.path.join(os.getcwd(), 'logo.png')
    if os.path.exists(output_file):
        os.remove(output_file)
    if os.path.exists(image_file):
        os.remove(image_file)
    os.makedirs(output_folder_path, exist_ok=True)
    ffmpegArgs = [
        'ffmpeg',
        '-i', video_url,
        '-i', logo,
        '-http_persistent', '1',
        '-http_multiple', '1',
        '-filter_complex', '[1]scale=iw*0.1:-1,format=rgba,colorchannelmixer=aa=0.4[wm];[0][wm]overlay=W-w-10:10',
        '-c:v', 'libvpx-vp9',
        '-crf', str(COMPRESS_RATE),
        '-speed', '0',
        '-map_metadata', '-1',
        '-threads', '8',
        '-b:v', '2500k',
        '-maxrate', '2700k',
        '-bufsize', '4000k',
        '-c:a', 'libopus',
        '-b:a', '128k',
        '-ac', '2',
        '-f', 'webm',
        '-movflags', '+faststart',
        output_file
    ]
    try:
        subprocess.run(ffmpegArgs, check=True)
        with open(output_file, 'rb') as vid_f:
            video_headers = {'Content-Type': 'video/webm'}
            response = requests.put(upload_url, data=vid_f, headers=video_headers)
        if response.status_code == 200:
            ffmpegImageArgs = [
                'ffmpeg',
                '-ss', '00:00:01',
                '-i', video_url,
                '-vframes', '1',
                '-q:v', '2',
                '-update', '1',
                image_file
            ]
            subprocess.run(ffmpegImageArgs, check=True)
            with open(image_file, 'rb') as img_f:
                headers = {'Content-Type': 'image/jpeg'}
                img_response = requests.put(Image_upload_url, data=img_f, headers=headers)
            if img_response.status_code == 200:
                headers = {
                    'Authorization': f'Bearer {upload_token}',
                    'Content-Type': 'application/json'
                }
                body = {
                    "reels_id": reels_id,
                    "video_url": trim_video_name
                }
                api_response = requests.post(BASE_URL, headers=headers, json=body)
                if api_response.status_code == 200:
                    os.remove(output_file)
                    os.remove(image_file)
                    return {"message": "Compression, uploads, and API call successful", "output_file": output_file, "image_file": image_file}
                else:
                    return {"error": f"Final API call failed: {api_response.status_code} {api_response.text}"}
            else:
                return {"error": f"Image upload failed: {img_response.status_code} {img_response.text}"}
        else:
            return {"error": f"Upload failed: {response.status_code} {response.text}"}
    except subprocess.CalledProcessError as e:
        return {"error": f"Compression failed: {str(e)}"}
