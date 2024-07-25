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

@app.get("/galleries/")
async def galleries_list(request: Request):
    user_info = verify_user(request)
    user_id = user_info['uid']
    
    owned_galleries = db.collection('galleries').where('user_id', '==', user_id).stream()
    shared_galleries = db.collection('users').document(user_id).collection('shared_galleries').stream()

    owned_list = [{"id": gallery.id, **gallery.to_dict()} for gallery in owned_galleries]
    shared_list = [{"id": gallery.id, **gallery.to_dict()} for gallery in shared_galleries]
    
    return {"owned_galleries": owned_list, "shared_galleries": shared_list}

@app.get("/galleries/{gallery_id}/images/")
async def retrieve_images(request: Request, gallery_id: str):
    verify_user(request)
    
    images = db.collection('images').where('gallery_id', '==', gallery_id).stream()
    return [image.to_dict() for image in images]

@app.post("/galleries/{gallery_id}/share/")
async def share_gallery(request: Request, gallery_id: str, email: str = Form(...)):
    user_info = verify_user(request)
    user_id = user_info['uid']
    
    user_query = db.collection('users').where('email', '==', email).stream()
    recipient = next(user_query, None)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with the provided email does not exist")

    recipient_id = recipient.id

    gallery_ref = db.collection('galleries').document(gallery_id)
    if not gallery_ref.get().exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    gallery_data = gallery_ref.get().to_dict()
    db.collection('users').document(recipient_id).collection('shared_galleries').document(gallery_id).set(gallery_data)

    return {"detail": "Gallery shared successfully"}

def compute_md5(file: UploadFile) -> str:
    """Compute MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with io.BytesIO(file.file.read()) as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

async def duplicate_image_gallery(file_hash: str) -> bool:
    """Check if the image hash is a duplicate across all galleries."""
    all_images_ref = db.collection("images")
    docs = all_images_ref.where("hash", "==", file_hash).stream()
    return any(docs)

@app.post("/upload_image/")
async def upload_image(request: Request, file: UploadFile = File(...)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return HTMLResponse(content="Unauthorized", status_code=401)

    data = await request.form()
    gallery_id = data.get("gallery_id")
    if not gallery_id:
        return HTMLResponse(content="Gallery ID is required", status_code=400)

    # Compute MD5 hash
    file_hash = compute_md5(file)

    if await duplicate_image_gallery(file_hash):
        return HTMLResponse(content="Duplicate image detected across galleries", status_code=400)


    gallery_img = db.collection("galleries").document(gallery_id)
    images_gall = gallery_img.collection("images")
    docs = images_gall.where("hash", "==", file_hash).stream()

    for doc in docs:
        return HTMLResponse(content="Duplicate image detected", status_code=400)

    images_gall.add({
        "hash": file_hash,
        "uploaded_at": firestore.SERVER_TIMESTAMP
    })
