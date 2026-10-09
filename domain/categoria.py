from sqlalchemy import Column, Integer, String
from domain.base import Base # importamos la base central que nos ayudara a crear las demas tablas

class Categoria(Base):
    __tablename__ = "Categoria"
    IdCategoria = Column(Integer, primary_key=True, autoincrement=True)
    Nombre = Column(String(100), nullable=False)
    
