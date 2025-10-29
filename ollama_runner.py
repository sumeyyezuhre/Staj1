import requests
from pdf_utils import extract_text_from_pdf
import os
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma:7b"

RAG_PROMPT = """
Sen bir yapay zeka asistanısın. Kullanıcının sorusunu cevaplamak için öncelikle aşağıda verilen 'Bağlam'ı kullanmaya çalış.
Eğer 'Bağlam' soruyu cevaplamak için alakasızsa (örneğin soru "selam" gibi genel bir sohbet sorusuysa), bağlamı dikkate alma ve genel bilgine dayanarak cevap ver.

Bağlam:
{context_block}

Soru: {question}

ÖNEMLİ NOT: Cevabı SADECE Türkçe dilinde ver. Başka bir dil kullanma.
Cevap:
""".strip()

CHAT_PROMPT = """
Sen yardımsever bir yapay zeka asistanısın. Kullanıcının sorusuna genel bilgine dayanarak sohbet havasında cevap ver.

Soru: {question}

ÖNEMLİ NOT: Cevabı SADECE Türkçe dilinde ver. Başka bir dil kullanma.
Cevap:
""".strip()

PROMPT_SUMMARIZE_CHUNK = """
Aşağıdaki metin parçasını detaylı bir şekilde, ana fikirleri koruyarak özetle.
Özet SADECE Türkçe olmalıdır.

Metin Parçası:
{text_chunk}

Detaylı Özet:
""".strip()

PROMPT_COMBINE_SUMMARIES = """
Aşağıda bir belgenin farklı bölümlerinden alınmış özetler bulunmaktadır. 
Bu özetleri kullanarak belgenin tamamı için akıcı ve kapsamlı bir nihai özet oluştur.
Nihai özet SADECE Türkçe olmalıdır.

Parça Özetler:
{combined_summaries}

Nihai Kapsamlı Özet:
""".strip()


def _call_ollama(prompt: str) -> str:
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        })

        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"HATA {response.status_code}: Ollama'dan geçerli cevap alınamadı."
    except requests.exceptions.ConnectionError:
        return "Ollama çalışmıyor. Terminalde `ollama run gemma:7b` komutu ile başlatmayı unutma."
    except Exception as e:
        return f"Beklenmedik bir hata oluştu: {str(e)}"


def build_rag_context_block(pdf_context: str, web_context: str) -> str:
    context_pieces = []
    if pdf_context:
        context_pieces.append(f"PDF'TEN ALINAN İLGİLİ BİLGİLER:\n{pdf_context}")
    if web_context:
        context_pieces.append(f"WEB ARAMA SONUÇLARI:\n{web_context}")



    if not context_pieces:
        return ""

    return "\n\n".join(context_pieces)


def ask_gemma_with_context(question: str, pdf_context: str = "", web_context: str = "") -> str:
    context_block = build_rag_context_block(pdf_context, web_context)

    if not context_block:
        print("Ollama Runner: Bağlam bulunamadı. Genel Sohbet modu çalışıyor.")
        prompt = CHAT_PROMPT.format(question=question)

        print("\n--- OLLAMA'YA GÖNDERİLEN CHAT PROMPT'U ---")
        print(prompt)
        print("-------------------------------------------\n")
    else:
        print("Ollama Runner: Bağlam bulundu. Soru-Cevap (RAG) modu çalışıyor.")
        prompt = RAG_PROMPT.format(
            context_block=context_block,
            question=question
        )

        print("\n--- OLLAMA'YA GÖNDERİLEN RAG PROMPT'U ---")
        print(prompt)
        print("-----------------------------------------\n")

    return _call_ollama(prompt)


def _split_text(text: str, chunk_size: int = 4000) -> list[str]:
    if not text:
        return []
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def summarize_pdf(pdf_path: str) -> str:

    print(f"Ollama Runner: Özetleme (Map-Reduce) modu çalışıyor. PDF: {pdf_path}")

    try:
        full_text = extract_text_from_pdf(pdf_path)
        if not full_text.strip():
            return "PDF'ten metin çıkarılamadı veya PDF boş."
    except Exception as e:
        print(f"PDF okuma hatası (summarize_pdf): {str(e)}")
        return f"PDF dosyası ('{os.path.basename(pdf_path)}') okunurken hata oluştu. Dosya bozuk veya şifreli olabilir."

    text_chunks = _split_text(full_text, chunk_size=4000)
    print(f"Metin {len(text_chunks)} parçaya bölündü.")

    if not text_chunks:
        return "❌ Metin parçalara bölünemedi."

    chunk_summaries = []
    for i, chunk in enumerate(text_chunks):
        print(f"Parça {i + 1}/{len(text_chunks)} özetleniyor...")
        chunk_prompt = PROMPT_SUMMARIZE_CHUNK.format(text_chunk=chunk)
        summary = _call_ollama(chunk_prompt)

        if "❌" in summary or "HATA" in summary:
            print(f"Parça {i + 1} özetlenirken hata: {summary}")
            continue

        chunk_summaries.append(summary)

    if not chunk_summaries:
        return "❌ Metin parçalarının hiçbiri özetlenemedi."

    print(f"{len(chunk_summaries)} adet parça özeti başarıyla oluşturuldu.")

    combined_summaries = "\n\n---\n\n".join(chunk_summaries)

    print("Tüm parça özetleri birleştiriliyor ve nihai özet oluşturuluyor...")
    final_prompt = PROMPT_COMBINE_SUMMARIES.format(combined_summaries=combined_summaries)

    final_summary = _call_ollama(final_prompt)

    return final_summary