import faiss
import os
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def add_text_to_vectorstore(text: str, index_base_path: str):
    index_file = index_base_path + ".index"
    pkl_file = index_base_path + ".pkl"

    sentences = text.split("\n\n")
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        print("Eklenecek içerik bulunamadı.")
        return  # Metin boşsa çık

    print(f"Metinden {len(sentences)} adet bölüm (chunk) oluşturuldu.")
    vectors = model.encode(sentences)

    if os.path.exists(index_file):
        try:
            index = faiss.read_index(index_file)
            with open(pkl_file, "rb") as f:
                all_sentences = pickle.load(f)

            index.add(np.array(vectors))
            all_sentences.extend(sentences)
            print(f"Mevcut indekse {len(sentences)} yeni bölüm eklendi. Toplam: {len(all_sentences)}")

        except Exception as e:
            print(f"Hata: İndeks yüklenemedi, yeni indeks oluşturulacak. Detay: {e}")
            # Hata olursa sıfırdan oluştur
            index = faiss.IndexFlatL2(vectors.shape[1])
            index.add(np.array(vectors))
            all_sentences = sentences
    else:
        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(np.array(vectors))
        all_sentences = sentences
        print(f"Yeni indeks oluşturuldu ve {len(sentences)} bölüm eklendi.")


    faiss.write_index(index, index_file)
    with open(pkl_file, "wb") as f:
        pickle.dump(all_sentences, f)


def search_faiss(query: str, index_base_path: str, k: int = 3) -> str:
    index_file = index_base_path + ".index"
    pkl_file = index_base_path + ".pkl"

    if not os.path.exists(index_file):
        print("İndeks dosyası bulunamadı. PDF yüklenmiş mi?")
        return ""

    try:
        index = faiss.read_index(index_file)
        with open(pkl_file, "rb") as f:
            sentences = pickle.load(f)
    except Exception as e:
        print(f"İndeks okunurken hata: {e}")
        return ""

    query_vec = model.encode([query])
    D, I = index.search(np.array(query_vec), k)

    if I.size == 0:
        return ""

    found_contexts = [sentences[i] for i in I[0]]
    print(f"PDF araması sonucu {len(found_contexts)} eşleşme bulundu.")
    return "\n".join(found_contexts)