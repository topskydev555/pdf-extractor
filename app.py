from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from pathlib import Path
import tempfile
import uuid
from werkzeug.utils import secure_filename
from pdf import extract_pdf
from upload import upload_folder_to_dropbox

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    except:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file selected'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'})
    
    if file and allowed_file(file.filename):
        # Generate unique filename using UUID
        unique_id = str(uuid.uuid4())
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{unique_id}.{file_extension}"
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        if validate_pdf(file_path):
            try:
                # Extract PDF using the pdf.py function
                output_folder = extract_pdf(file_path)
                
                # Upload to Dropbox
                try:
                    dropbox_result = upload_folder_to_dropbox(output_folder)
                    
                    return jsonify({
                        'status': 'success', 
                        'message': 'PDF processed and uploaded to Dropbox successfully!',
                        'output_folder': output_folder,
                        'dropbox_folder': dropbox_result['dropbox_folder_path'],
                        'shared_link': dropbox_result['shared_link'],
                        'view_link': dropbox_result['view_link'],
                        'files_uploaded': dropbox_result['total_files'],
                        'clickable_link': dropbox_result['view_link'] or dropbox_result['shared_link']
                    })
                except Exception as dropbox_error:
                    # If Dropbox upload fails, still return success for PDF extraction
                    return jsonify({
                        'status': 'success', 
                        'message': 'PDF processed successfully, but Dropbox upload failed',
                        'output_folder': output_folder,
                        'dropbox_error': str(dropbox_error)
                    })
                    
            except Exception as e:
                return jsonify({
                    'status': 'error', 
                    'message': f'PDF processing failed: {str(e)}'
                })
        else:
            return jsonify({'status': 'error', 'message': 'Invalid PDF file format'})
    
    return jsonify({'status': 'error', 'message': 'Invalid file type. Please upload a PDF file.'})

if __name__ == '__main__':
    try:
        app.run(debug=False, host='127.0.0.1', port=5000)
    except OSError:
        print("Port 5000 is busy, trying port 5001...")
        app.run(debug=False, host='127.0.0.1', port=5001)
