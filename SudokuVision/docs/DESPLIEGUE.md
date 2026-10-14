# Poner la demo en Internet

La entrega contiene una aplicación funcional validada en Windows. Aún no tiene una URL pública.

## Servidor Python

En un servicio que permita ejecutar Python 3.12 y TensorFlow:

1. Sube el contenido del proyecto conservando las carpetas.
2. Instalación: python -m pip install -r requirements.txt.
3. Inicio: python app.py.
4. Configura HOST=0.0.0.0 y el PORT asignado por el proveedor.
5. Configura el acceso público por HTTPS y usa /health como comprobación de proceso.
6. Prueba desde una ventana privada ambos ejemplos y una imagen propia antes de enlazar la demo.

El modelo se carga con la primera lectura; /health confirma que el proceso responde, no que el modelo ya se haya cargado. Para comprobar el modelo hay que enviar una imagen.

TensorFlow necesita más recursos que una página estática. Mide la memoria con el proveedor elegido y evita prometer disponibilidad permanente en servicios que suspenden procesos inactivos.

## Docker

Se incluye un Dockerfile para preparar el despliegue:

    docker build -t sudokuvision .
    docker run --rm -p 8000:8000 sudokuvision

Abre http://127.0.0.1:8000. El contenedor escucha en todas sus interfaces y ejecuta la aplicación con un usuario sin privilegios.

La validación entregada corresponde a Windows/Python 3.12; la construcción y ejecución del contenedor Linux están pendientes de comprobar en el servidor de destino.

## Configuración de red

El límite de 20 peticiones por minuto se aplica por dirección remota y proceso. Detrás de un proxy sin configurar, varios visitantes pueden compartir ese límite. Para una publicación con proxy, configura explícitamente la IP del proxy de confianza y los encabezados que tu infraestructura controla. No aceptes cualquier X-Forwarded-For enviado por el visitante.

Mantén el límite de tamaño también en el proxy. Si necesitas conservar la política de procesamiento en memoria, revisa que ese proxy no guarde cuerpos de peticiones ni subidas. La aplicación y su configuración de Waitress no escriben imágenes subidas en archivos.

Referencias oficiales: [despliegue Flask con Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/) y [configuración de Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/arguments.html).

## En Notion

La ficha puede contener una captura, una descripción, el enlace al código y el enlace público **Probar SudokuVision**. No pegues una dirección localhost: solo funciona en el equipo donde se está ejecutando.

Conserva la estructura de carpetas al subir a GitHub. Sube los archivos descomprimidos para que el README y el código sean navegables. El ZIP es una copia de distribución.
