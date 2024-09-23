from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Calcular la fecha límite desde hoy a 8 meses atrás 
fecha_limite = datetime.now() - timedelta(days=246)
fecha_limite_formateada = fecha_limite.strftime("%m/%d/%Y")

# Cargar las variables de entorno
load_dotenv()

# Definir el modelo de datos
class WebPageData(BaseModel):
    title: str = Field(description="The title of the web page")
    date: str = Field(description="The publication date of the content")
    content: str = Field(description="The main content of the web page")
    url: str = Field(description="The URL of the web page")
    source: str = Field(description="The name of the web page")

# Inicializar el parser
parser = JsonOutputParser(pydantic_object=WebPageData)

# Crear la plantilla de prompt, manejando toda la lógica de validación
prompt = PromptTemplate(
    template = """
        Eres un asistente que se usará para extraer información relevante de artículos de la web y evaluar su relevancia para un tema específico.

        Dado el texto :
        Texto: {text}

        1. Extrae el título principal del artículo. Asegúrate de que sea el título del artículo, no el del sitio web o de cualquier otra sección.
        
        2. Extrae la fecha de publicación del artículo, no la fecha de actualización ni la fecha actual ni la fecha de la misma página. Si encuentras múltiples fechas (por ejemplo, "Published" y "Updated"), utiliza la fecha de publicación.

        3. Asegúrate de que la fecha esté en formato MM/DD/YYYY. Si encuentras fechas en otros formatos, conviértelas al formato MM/DD/YYYY si es posible. Si no puedes convertir la fecha, incluye la fecha tal como está sin marcar la noticia como irrelevante. Los formatos comunes pueden incluir:
            - YYYY-MM-DD (por ejemplo, 2024-03-02)
            - DD/MM/YYYY (por ejemplo, 02/03/2024)
            - Month DD, YYYY (por ejemplo, May 5, 2024)
        Si la fecha está incompleta o no es clara, incluye el valor encontrado sin marcar la noticia como irrelevante.

        4. Extrae el contenido principal del artículo, buscando específicamente dentro de los elementos de contenido principal como `<article>`, `<p>`, y similares. Excluye comentarios, anuncios, y cualquier otra sección irrelevante, asegurándote de que se captura todo el contenido relevante y completo. Si el contenido está dividido en varias secciones, asegúrate de concatenarlas para tener el texto íntegro.

        5. Extrae el nombre de la fuente del artículo. Esto debe ser el nombre del sitio web, que generalmente se puede encontrar en el título de la página o deducirse del dominio principal de la URL.

        6. Evalúa la relevancia de la noticia asegurándote de que el contenido sea estrictamente relevante para el tema de búsqueda: "{tema}". La relevancia debe basarse en palabras clave y contexto, y debe evaluarse después de extraer todo el contenido del artículo.

        7. Marca la noticia como irrelevante **solo** si el contenido no es pertinente al tema de búsqueda. No marques noticias como irrelevantes debido a problemas con la fecha de publicación u otras anomalías que no afecten la relevancia temática.

        8. Proporciona el resultado en formato JSON con los siguientes campos:
            {{
                "title": "<title>",
                "date": "<date>",
                "content": "<content>",
                "url": "<url>",
                "source": "<source>"
            }}
            
        9. No inventes información ni hagas suposiciones; sigue estrictamente las instrucciones dadas para la extracción de datos y evaluación de relevancia. 
    """
)

# Inicializar el modelo de OpenAI
model = ChatOpenAI(temperature=0.1, model= "gpt-4o-mini")

# Combinar los componentes en una cadena
chain = prompt | model | parser

def generar_resumen_ia(text_input, tema):
    """
    Función para generar un resumen en formato JSON de un texto proporcionado usando IA.

    Args:
    text_input (str): Texto de entrada con los datos de la página web.
    tema (str): Tema de búsqueda relacionado con el contenido.

    Returns:
    dict: Resumen en formato JSON con el título, fecha, contenido y URL, o un mensaje si es irrelevante.
    """
    try:
        # Ejecutar la cadena para obtener el resultado, incluyendo el tema y la fecha límite en el contexto del prompt
        result = chain.invoke({"text": text_input, "tema": tema, "fecha_limite": fecha_limite_formateada})
        return result
    except Exception as e:
        return f"An error occurred: {e}"
