import os
import psycopg2
from dotenv import load_dotenv
import streamlit as st

# Cargar variables del archivo .env
load_dotenv()

class DatabaseConnection:
    """Maneja las conexiones a PostgreSQL"""
    
    def __init__(self):
        self.host = os.getenv("host", "")
        self.port = os.getenv("port", "5432") 
        self.dbname = os.getenv("dbname", "")
        self.user = os.getenv("user", "")
        self.password = os.getenv("password", "")
        
    def validate_credentials(self):
        """Valida que todas las credenciales estén presentes"""
        return all([self.host, self.dbname, self.user, self.password])
    
    def get_connection(self):
        """Crea y retorna una nueva conexión a PostgreSQL"""
        try:
            conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user, 
                password=self.password,
                host=self.host,
                port=int(self.port)
            )
            return conn
        except Exception as e:
            st.error(f"❌ Error conectando a PostgreSQL: {e}")
            return None
    
    def test_connection(self):
        """Prueba la conexión y retorna True si es exitosa"""
        conn = self.get_connection()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                conn.close()
                return True
            except:
                return False
        return False
    
    def get_connection_info(self):
        """Retorna información de la conexión para mostrar"""
        return f"{self.user}@{self.host}:{self.port}/{self.dbname}"

# Instancia global
db = DatabaseConnection()

def get_connection():
    """Función helper para obtener conexión"""
    return db.get_connection()

def validate_db_credentials():
    """Valida credenciales y muestra error si faltan"""
    if not db.validate_credentials():
        st.error("❌ Archivo .env no encontrado o incompleto")
        st.info("💡 Asegúrate de tener un archivo .env con: host, port, dbname, user, password")
        st.stop()
    return True