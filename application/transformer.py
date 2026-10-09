import pandas as pd
import re
from typing import Tuple
from application.interfaces import ITransformer

class DataTransformer(ITransformer):
    def __init__(self, columnas_obligatorias: list, columnas_duplicados: list = None, es_opinion: bool = False, renombrar_cols: dict = None, id_fuente_default: int = None):
        self.columnas_obligatorias = columnas_obligatorias
        self.columnas_duplicados = columnas_duplicados if columnas_duplicados else columnas_obligatorias
        self.es_opinion = es_opinion
        self.renombrar_cols = renombrar_cols if renombrar_cols else {}
        self.ids_validos = {}
        self.id_fuente_default = id_fuente_default # Para asignar el IdFuente según el archivo

        self.palabras_positivas = ['excelente', 'bueno', 'me encanta', 'genial', 'recomendado', 'rápido', 'satisfecho', 'mejor', 'superior']
        self.palabras_negativas = ['malo', 'pésimo', 'lento', 'roto', 'no funciona', 'horrible', 'decepción', 'terrible', 'peor', 'insatisfecho']

    def _limpiar_texto(self, texto):
        if not isinstance(texto, str): return texto
        return re.sub(r'[^a-zA-Z0-9\s.,!?ñÑáéíóúÁÉÍÓÚ]', '', texto).strip()

    def _clasificar_y_puntuar(self, fila):
        texto = str(fila.get('Comentario', '')).lower()
        score = 0
        for p in self.palabras_positivas:
            if p in texto: score += 1
        for p in self.palabras_negativas:
            if p in texto: score -= 1
        
        if score > 0: return pd.Series(['Positiva', 5.0])
        elif score < 0: return pd.Series(['Negativa', 1.0])
        else: return pd.Series(['Neutra', 3.0])

    def _calcular_metricas(self, df: pd.DataFrame):
        total = len(df)
        if total == 0: return
        positivas = len(df[df['Clasificacion_Texto'] == 'Positiva'])
        print(f"\n--- MÉTRICAS (Opiniones) ---")
        print(f"Total procesados: {total} | Satisfacción: {(positivas/total)*100:.2f}%")
        print("----------------------------\n")

    def transformar(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        if df.empty: return df, 0
        total_inicial = len(df)
        
        # 0. Renombrar columnas (Ej: Rating -> PuntajeSatisfaccion)
        df_limpio = df.rename(columns=self.renombrar_cols)

        # 1. Limpieza de duplicados y nulos 
        df_limpio = df_limpio.drop_duplicates(subset=self.columnas_duplicados)
        df_limpio = df_limpio.dropna(subset=self.columnas_obligatorias)

        # 2. LIMPIEZA DE IDS Y CAMPOS DE TEXTO
        # Extrae solo los dígitos y los convierte en números para que SQL los acepte
        for col in ['IdCliente', 'IdProducto', 'IdFuente']:
            if col in df_limpio.columns:
                df_limpio[col] = df_limpio[col].astype(str).str.replace(r'\D', '', regex=True)
                df_limpio[col] = pd.to_numeric(df_limpio[col], errors='coerce')

        # Evita que una referencia foránea inexistente invalide todo el INSERT masivo.
        for columna, ids_permitidos in self.ids_validos.items():
            if columna in df_limpio.columns:
                df_limpio = df_limpio[df_limpio[columna].isin(ids_permitidos)]

        for col in ['Nombre', 'Email']:
            if col in df_limpio.columns:
                df_limpio[col] = df_limpio[col].astype(str).str.strip()
                if col == 'Email': df_limpio[col] = df_limpio[col].str.lower()

        if self.es_opinion:
            if 'Comentario' in df_limpio.columns:
                df_limpio['Comentario'] = df_limpio['Comentario'].apply(self._limpiar_texto)
                df_limpio = df_limpio[df_limpio['Comentario'] != ''] 

            if 'Fecha' in df_limpio.columns:
                df_limpio['Fecha'] = pd.to_datetime(df_limpio['Fecha'], errors='coerce').dt.date
                df_limpio = df_limpio.dropna(subset=['Fecha'])

            if 'Comentario' in df_limpio.columns:
                df_limpio[['Clasificacion_Texto', 'PuntajeSatisfaccion_Calculado']] = df_limpio.apply(self._clasificar_y_puntuar, axis=1)
                
                # Si el CSV no trajo puntaje (como social_comments), usamos el calculado por tu NLP
                if 'PuntajeSatisfaccion' not in df_limpio.columns:
                    df_limpio['PuntajeSatisfaccion'] = df_limpio['PuntajeSatisfaccion_Calculado']
                
                # Mapear a Llave Foránea de Clasificacion (1=Positiva, 2=Negativa, 3=Neutra)
                mapa_clas = {'Positiva': 1, 'Negativa': 2, 'Neutra': 3}
                df_limpio['IdClasificacion'] = df_limpio['Clasificacion_Texto'].map(mapa_clas)
                
                # Asignar IdFuente duro según el archivo
                if self.id_fuente_default:
                    df_limpio['IdFuente'] = self.id_fuente_default

                self._calcular_metricas(df_limpio)
                
                # Eliminar columnas extrañas del CSV para que el Insert de SQL no explote
                cols_basura = ['Fuente', 'Clasificación', 'Clasificacion_Texto', 'PuntajeSatisfaccion_Calculado', 'IdComment', 'IdOpinion', 'IdReview']
                df_limpio = df_limpio.drop(columns=[c for c in cols_basura if c in df_limpio.columns])

        rechazados = total_inicial - len(df_limpio)
        return df_limpio, rechazados
