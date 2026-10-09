from sqlalchemy import Column, Integer, String, ForeignKey
from domain.base import Base # importamos la base central que nos ayudara a crear las demas tablas

class Producto(Base):
    __tablename__ = 'Producto'
    IdProducto = Column(Integer, primary_key=True, autoincrement=False)
    Nombre = Column(String(150), nullable=False)
    IdCategoria = Column(Integer, ForeignKey('Categoria.IdCategoria'))