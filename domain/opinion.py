from sqlalchemy import Column, Integer, String, Date, ForeignKey, Float
from domain.base import Base # importamos la base central que nos ayudara a crear las demas tablas


class Opinion(Base):
    __tablename__ = 'Opinion'
    IdOpinion = Column(Integer, primary_key=True)
    IdCliente = Column(Integer, ForeignKey('Cliente.IdCliente'))
    IdProducto = Column(Integer, ForeignKey('Producto.IdProducto'))
    IdClasificacion = Column(Integer, ForeignKey('Clasificacion.IdClasificacion'))
    IdFuente = Column(Integer, ForeignKey('FuenteDatos.IdFuente'))
    Fecha = Column(Date)
    Comentario = Column(String)
    PuntajeSatisfaccion = Column(Float)