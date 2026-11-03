# serve.py — inicia la app con Waitress en producción
from waitress import serve
from main import app

if __name__ == '__main__':
    print("Swarm corriendo en http://0.0.0.0:5001")
    serve(app, host='0.0.0.0', port=5001, threads=4)