#duckduckgo.py
from duckduckgo_search import DDGS
from datetime import datetime

def obtener_enlaces(query):
    """
    Función que toma un término de búsqueda,
    realiza la búsqueda en DuckDuckGo y devuelve los enlaces obtenidos.
    
    Args:
    query (str): Palabra clave o término de búsqueda.
    
    Returns:
    list: Lista de URLs obtenidas de la búsqueda.
    """
    urls = []

    # Modificar el query para incluir noticias en español e inglés
    query_modificado = f"{query} (lang:es OR lang:en)"

    print(f"Query Modificada: {query_modificado}")  # Verifica la query generada

    try:
        # Realizar la búsqueda con DDGS
        with DDGS() as ddgs:
            # Ajusta el timelimit a 'w' para la última semana o 'm' para el último mes
            for i, result in enumerate(ddgs.text(query_modificado, region="wt-wt", safesearch="Off", timelimit="m")):
                if i >= 10:  # Limitar a 10 resultados
                    break
                urls.append(result['href'])  # Agregar solo la URL del resultado
    except Exception as e:
        print(f"Error durante la búsqueda: {e}")

    return urls