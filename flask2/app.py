import os
import uuid
import json
import hashlib
from datetime import datetime
from mimetypes import guess_extension
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Необходимо для flash сообщений

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx'}
BANNED_EXTENSIONS = {'exe', 'sh', 'php', 'js', 'py', 'bat', 'cmd'}
METADATA_FILE = 'file_metadata.json'

# Создаем папку для загрузок, если ее нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_metadata():
    """Загружает метаданные файлов из JSON"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Сохраняет метаданные файлов в JSON"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)

def allowed_file(filename):
    """Проверяет, что файл имеет разрешенное расширение"""
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return (file_ext in ALLOWED_EXTENSIONS) and (file_ext not in BANNED_EXTENSIONS)

def generate_file_path(filename):
    """Генерирует путь для сохранения файла на основе UUID"""
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    file_uuid = str(uuid.uuid4().hex)
    
    # Создаем подкаталоги на основе первых двух символов UUID
    subdir1 = file_uuid[:2]
    subdir2 = file_uuid[2:4]
    full_path = os.path.join(UPLOAD_FOLDER, subdir1, subdir2)
    
    os.makedirs(full_path, exist_ok=True)
    return os.path.join(full_path, f"{file_uuid}.{file_ext}"), file_uuid

def calculate_file_hash(filepath):
    """Вычисляет MD5 хэш файла"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_duplicate(filepath):
    """Проверяет, есть ли уже такой файл (по хэшу)"""
    file_hash = calculate_file_hash(filepath)
    metadata = load_metadata()
    
    for file_data in metadata.values():
        if file_data.get('hash') == file_hash:
            return True
    return False

@app.route('/')
def index():
    """Главная страница с формой загрузки и списком файлов"""
    metadata = load_metadata()
    return render_template('index.html', files=metadata.values())

@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки файла"""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('File type not allowed', 'error')
        return redirect(url_for('index'))
    
    # Сохраняем временный файл для проверки дубликатов
    temp_path = os.path.join(UPLOAD_FOLDER, f"temp_{uuid.uuid4().hex}")
    file.save(temp_path)
    
    if check_duplicate(temp_path):
        os.remove(temp_path)
        flash('File already exists (duplicate)', 'error')
        return redirect(url_for('index'))
    
    # Генерируем путь и сохраняем файл
    file_path, file_uuid = generate_file_path(file.filename)
    os.rename(temp_path, file_path)
    
    # Добавляем метаданные
    metadata = load_metadata()
    file_hash = calculate_file_hash(file_path)
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    metadata[file_uuid] = {
        'uuid': file_uuid,
        'original_name': file.filename,
        'upload_date': datetime.now().isoformat(),
        'server_path': file_path,
        'extension': file_ext,
        'hash': file_hash
    }
    
    save_metadata(metadata)
    flash('File successfully uploaded', 'success')
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def download_file(filename):
    """Отдает загруженный файл"""
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)