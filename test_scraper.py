# test_scraper.py
from bs4 import BeautifulSoup
import requests
import re

def scrape_contenido(link):
    """
    Función que toma un enlace, realiza el scraping de la página web usando BeautifulSoup,
    elimina espacios y saltos de línea innecesarios, y formatea el contenido para tener
    saltos de línea solo después de puntos. También extrae la fecha de publicación si está disponible.

    Args:
    link (str): URL del sitio web a scrapear.

    Returns:
    dict: Contenido formateado del sitio web y la fecha de publicación o mensaje de error.
    """
    try:
        # Realizar una solicitud GET para obtener el contenido de la página
        response = requests.get(link, timeout=4)
        response.raise_for_status()  # Verifica que la solicitud fue exitosa
        soup = BeautifulSoup(response.content, "lxml", from_encoding=response.encoding)

        # Eliminar elementos de script y estilo para limpiar el contenido
        for script_or_style in soup(["script", "style"]):
            script_or_style.extract()

        # Extraer todo el texto plano del contenido
        raw_content = soup.get_text(separator=" ").strip()

        # Reemplazar múltiples espacios y saltos de línea por un solo espacio
        formatted_content = ' '.join(raw_content.split())

        # Insertar saltos de línea solo después de puntos
        formatted_content = formatted_content.replace('. ', '.\n')

        # Extraer la fecha de publicación utilizando posibles selectores de fecha
        fecha_publicacion = None

        # Buscando posibles etiquetas de fecha
        # Estos selectores pueden variar, ajusta según el sitio específico
        posibles_fechas = soup.find_all(text=re.compile(r'\b\d{1,2}\s(de\s)?\w+\s(de\s)?\d{4}\b', re.IGNORECASE))

        for fecha in posibles_fechas:
            # Aquí se busca asegurar que la fecha es un patrón correcto como "02 sep 2024"
            if re.search(r'\b\d{1,2}\s(de\s)?\w+\s(de\s)?\d{4}\b', fecha):
                fecha_publicacion = fecha.strip()
                break
        
        # Alternativamente buscar en etiquetas time, span, etc., si no se encuentra en texto plano
        if not fecha_publicacion:
            fecha_tag = soup.find('time')
            if fecha_tag and 'datetime' in fecha_tag.attrs:
                fecha_publicacion = fecha_tag['datetime']
            elif fecha_tag:
                fecha_publicacion = fecha_tag.get_text(strip=True)

        # Si aún no se encuentra, intenta buscar con clases comunes de fechas
        if not fecha_publicacion:
            fecha_tag = soup.find('span', class_=re.compile(r'(date|fecha|time)', re.IGNORECASE))
            if fecha_tag:
                fecha_publicacion = fecha_tag.get_text(strip=True)

        # Manejo de salida si no se encuentra la fecha
        if not fecha_publicacion:
            fecha_publicacion = 'Fecha no encontrada'

        return {
            'content': formatted_content,
            'date': fecha_publicacion
        }

    except requests.exceptions.RequestException as e:
        return {
            'content': 'Error al hacer la solicitud: {}'.format(e),
            'date': 'Fecha no encontrada'
        }
    except Exception as e:
        return {
            'content': 'Error al extraer contenido: {}'.format(e),
            'date': 'Fecha no encontrada'
        }
