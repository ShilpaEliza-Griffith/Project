from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore
import hashlib
import starlette.status as status

app = FastAPI()

# Initialize Firestore client
db = firestore.Client()

# Firebase Auth
HTTP_REQUEST = requests.Request()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def verify_user(request: Request):
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    
    try:
        user_info = google.oauth2.id_token.verify_firebase_token(token, HTTP_REQUEST)
        if not user_info:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_info
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@app.post("/create_gallery/")
async def create_gallery(request: Request, name: str = Form(...)):
    user_info = verify_user(request)
    user_id = user_info['uid']
    
    new_gallery = db.collection('galleries').add({
        "user_id": user_id,
        "name": name,
        "thumbnail_url": None  # Initialize thumbnail_url to None
    })
    
    return {"id": new_gallery[1].id}

