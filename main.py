from fastapi import FastAPI, HTTPException, Header
import os
from supabase.client import create_client, Client
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from typing import Annotated
import random
import string
import yt_dlp

load_dotenv()

app = FastAPI()


url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
local_secret_key: str = os.environ.get("SECRET_TOKEN")
supabase: Client = create_client(url, key)


def download_and_convert_video(url):
    # Generate a random filename for the temporary video file
    temp_filename = (
        "".join(random.choices(string.ascii_lowercase + string.digits, k=8)) 
    )

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": temp_filename,
        "noplaylist": True,
        "verbose": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(([url]))

    return temp_filename + ".mp3"


@app.post("/convert")
async def convert_and_upload_to_supabase(
    url: str, secret_key: Annotated[str | None, Header()] = None
):

    if secret_key != local_secret_key:
        raise HTTPException(status_code=403, detail="not allowed")

    try:
        # Download and convert video to MP3
        mp3_filename = download_and_convert_video(url)

        # Upload MP3 file to Supabase storage
        bucket_name = "songs"
        new_file = open(mp3_filename, "rb")

        supabase.storage.from_(bucket_name).upload(f"/{mp3_filename}", new_file)

        res = supabase.storage.from_(bucket_name).get_public_url(f"/{mp3_filename}")

        print(res, "uploaded to supabase bucket")

        # Delete the temporary MP3 and video files
        os.remove(mp3_filename)

        # print(error)
        # if data.get("error") is not None:
        #     raise HTTPException(
        #         status_code=500, detail="Failed to upload MP3 to Supabase storage"
        #     )

        # Get the URL of the uploaded MP3 file
        # mp3_url = data["url"]

        # Return the MP3 URL in the response
        return JSONResponse(content={"mp3_url": res})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Hello World"}
