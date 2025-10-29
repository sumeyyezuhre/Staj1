from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pdf_utils import extract_text_from_pdf
from vectorstore import add_text_to_vectorstore, search_faiss
from ollama_runner import ask_gemma_with_context, summarize_pdf
from web_search import search_web
from chat_history import add_to_history, get_history

import os
import shutil
import uuid
import traceback
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

PDF_VECTOR_DB_BASE = "data/pdf_index"
DOCS_FOLDER = "data/uploads"

os.makedirs(DOCS_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(PDF_VECTOR_DB_BASE), exist_ok=True)

def is_summarization_intent(question: str) -> bool:
    question_lower = question.lower()
    keywords = ["özetle", "özet çıkar", "özetini", "ne hakkında", "konusu ne", "bana anlat"]
    for key in keywords:
        if key in question_lower:
            return True
    return False

def is_pdf_search_intent(question: str) -> bool:
    question_lower = question.lower()
    keywords = ["pdf'e göre", "belgeye göre", "yüklediğim dosyada", "pdf'ten bak", "metinde", "dosyaya göre"]
    for key in keywords:
        if key in question_lower:
            return True
    return False


def is_web_search_intent(question: str) -> bool:
    question_lower = question.lower()
    keywords = ["web'de ara", "internetten bul", "internette", "araştır", "google'da ara", "web'den bak"]
    for key in keywords:
        if key in question_lower:
            return True
    return False


def get_latest_pdf_path() -> str | None:
    if not os.path.exists(DOCS_FOLDER) or not os.listdir(DOCS_FOLDER):
        return None
    files = [os.path.join(DOCS_FOLDER, f) for f in os.listdir(DOCS_FOLDER) if f.lower().endswith('.pdf')]
    if not files:
        return None
    latest_file = max(files, key=os.path.getmtime)
    return latest_file


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "history": get_history()
    })

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = f"{DOCS_FOLDER}/{file_id}_{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        text = extract_text_from_pdf(file_path)
        add_text_to_vectorstore(text, PDF_VECTOR_DB_BASE)
        return {"status": "ok", "message": f"PDF '{file.filename}' yüklendi ve indekse eklendi."}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"--- !!! PDF YÜKLEME HATASI !!! ---\n{traceback.format_exc()}\n---------------------------------")
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": f"PDF işlenirken hata oluştu: {str(e)}"}
        )

@app.post("/ask")
async def ask_question(request: Request):
    """
    1. Özetleme
    2. Web'de Arama
    3. PDF'de Arama
    4. Sohbet
    """
    try:
        data = await request.json()
        question = data.get("question", "")
        search_web_flag = data.get("search_web_flag", False)

        if not question:
            return JSONResponse(status_code=400, content={"answer": "Soru boş olamaz."})

        response = ""

        #ÖZETLEME
        if is_summarization_intent(question):
            print(f"Mod 1: Özetleme isteği algılandı.")
            latest_pdf = get_latest_pdf_path()
            if not latest_pdf:
                response = "Özetlenecek bir PDF bulunamadı. Lütfen önce bir PDF yükleyin."
            else:
                response = summarize_pdf(pdf_path=latest_pdf)

        #WEB'DE ARAMA
        elif search_web_flag or is_web_search_intent(question):
            print(f"Mod 2: Web Arama isteği algılandı.")
            web_context = search_web(question)
            response = ask_gemma_with_context(
                question=question,
                pdf_context="",
                web_context=web_context
            )

        #PDF'DE ARAMA
        elif is_pdf_search_intent(question):
            print(f"Mod 3: PDF Arama isteği algılandı.")
            pdf_context = search_faiss(question, PDF_VECTOR_DB_BASE, k=3)
            response = ask_gemma_with_context(
                question=question,
                pdf_context=pdf_context,
                web_context=""
            )

        #SOHBET
        else:
            print(f"Mod 4: Genel Sohbet isteği algılandı.")
            response = ask_gemma_with_context(
                question=question,
                pdf_context="",
                web_context=""
            )

        add_to_history(question, response)
        return JSONResponse(content={"answer": response})

    except Exception as e:
        print(f"--- !!! SUNUCU HATASI (/ask) !!! ---\n{traceback.format_exc()}\n---------------------------------")
        error_message = f" Sunucu Tarafında Bir Hata Oluştu: {str(e)}"
        try:
            data = await request.json()
            question = data.get("question", "Hatalı Soru")
            add_to_history(question, error_message)
        except:
            pass
        return JSONResponse(content={"answer": error_message})