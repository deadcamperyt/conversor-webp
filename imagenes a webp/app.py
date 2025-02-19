from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session
from PIL import Image
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Necesario para usar sesiones

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'static/webp'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Diccionario para almacenar el progreso de cada usuario
progress_data = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convertir_a_webp(task_id, ruta_entrada, ruta_salida, calidad=80, resize=100, crop=None):
    try:
        with Image.open(ruta_entrada) as img:
            progress_data[task_id] = 20

            # Recorte
            if crop and len(crop.split(',')) == 4:
                x, y, w, h = map(int, crop.split(','))
                img = img.crop((x, y, x + w, y + h))
            
            progress_data[task_id] = 40

            # Redimensionar
            if resize < 100:
                new_size = (int(img.width * resize / 100), int(img.height * resize / 100))
                img = img.resize(new_size, Image.LANCZOS)
            
            progress_data[task_id] = 70

            # Convertir a WebP
            if img.mode in ('RGBA', 'LA'):
                img = img.convert('RGB')
            
            img.save(ruta_salida, 'WEBP', quality=calidad, method=6)
            progress_data[task_id] = 100
            
            return True
    except Exception as e:
        progress_data[task_id] = -1  # Error
        print(f"Error: {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No se seleccionó archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if file and allowed_file(file.filename):
            # Generar ID único para esta tarea
            task_id = str(uuid.uuid4())
            progress_data[task_id] = 0
            
            filename = secure_filename(file.filename)
            ruta_entrada = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(ruta_entrada)
            
            # Parámetros del formulario
            calidad = int(request.form.get('quality', 80))
            resize = int(request.form.get('resize', 100))
            crop = request.form.get('crop', '')
            
            # Nombre de salida
            nombre_salida = os.path.splitext(filename)[0] + '.webp'
            ruta_salida = os.path.join(app.config['OUTPUT_FOLDER'], nombre_salida)
            
            # Ejecutar conversión (en hilo para no bloquear)
            from threading import Thread
            thread = Thread(target=convertir_a_webp, args=(task_id, ruta_entrada, ruta_salida, calidad, resize, crop))
            thread.start()
            
            return jsonify({'task_id': task_id, 'filename': nombre_salida})
    
    return render_template('index.html')

@app.route('/progress/<task_id>')
def get_progress(task_id):
    return jsonify({'progress': progress_data.get(task_id, 0)})

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    app.run(debug=True)