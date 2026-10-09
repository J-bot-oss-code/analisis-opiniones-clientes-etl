import pandas as pd
import requests
from application.interfaces import IExtractor

class ApiRestExtractor(IExtractor):
    """Extrae datos consumiendo un endpoint de una API REST (JSON)."""
    
    def __init__(self, url_api: str):
        self.url_api = url_api

    def extraer(self) -> pd.DataFrame:
        try:
            # Hacemos la petición GET a la API
            respuesta = requests.get(self.url_api)
            
            # Validamos que la API haya respondido con un código 200 (OK)
            respuesta.raise_for_status() 
            
            # Convertimos la respuesta JSON a un diccionario de Python
            datos_json = respuesta.json()
            
            # Convertimos el diccionario a DataFrame de Pandas
            df = pd.DataFrame(datos_json)
            
            print(f"[EXTRACTOR API] Éxito: Se extrajeron {len(df)} registros de {self.url_api}.")
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR EXTRACTOR API] Problema de red o HTTP al consumir la API: {e}")
            return pd.DataFrame()
        except ValueError as e:
            print(f"[ERROR EXTRACTOR API] El formato de la API no es un JSON válido: {e}")
            return pd.DataFrame()