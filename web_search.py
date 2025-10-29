from duckduckgo_search import DDGS


def search_web(query: str) -> str:
    results = []
    region = "tr-tr"

    print(f"Web araması yapılıyor (Bölge: {region}, Soru: {query})...")

    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, region=region, max_results=5):
                results.append(f"{r['title']}: {r['body']}")

        if results:
            print(f"Web araması sonucu {len(results)} adet içerik bulundu.")
            return "\n".join(results)
        else:
            print("Web araması (DuckDuckGo) sonuç bulamadı.")
            return ""

    except Exception as e:
        print(f"DuckDuckGo araması sırasında hata oluştu: {e}")
        return ""