from sqlalchemy import Column, Integer, String
from domain.base import Base # importamos la base central que nos ayudara a crear las demas tablas

class Clasificacion(Base):
    __tablename__ = "Clasificacion"
    IdClasificacion = Column(Integer, primary_key=True, autoincrement=False)
    Nombre = Column(String(100), nullable=False)
