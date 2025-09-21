from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
import PyPDF2
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

if not os.path.exists('uploads'):
    os.makedirs('uploads')

@app.route('/')
def index():
    session.pop('merged_file', None)
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    uploaded_files = []
    file_info = []
    
    for i, file in enumerate(files):
        if file and file.filename.endswith('.pdf'):
            name, ext = os.path.splitext(secure_filename(file.filename))
            filename = f"{i:02d}_{name}{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_files.append(filepath)
            file_info.append({'name': file.filename, 'path': filepath, 'index': i})
    
    if uploaded_files:
        uploaded_files.sort()
        session['uploaded_files'] = uploaded_files
        session['file_info'] = file_info
        return jsonify({'success': True, 'files': file_info})
    return jsonify({'success': False, 'error': 'No valid PDF files uploaded'})

@app.route('/reorder', methods=['POST'])
def reorder_files():
    if 'uploaded_files' not in session:
        return jsonify({'success': False, 'error': 'No files to reorder'})
    
    new_order = request.json.get('order', [])
    if not new_order:
        return jsonify({'success': False, 'error': 'No order specified'})
    
    try:
        # Reorder files based on new indices
        original_files = session['uploaded_files']
        reordered_files = [original_files[i] for i in new_order if i < len(original_files)]
        session['uploaded_files'] = reordered_files
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/merge', methods=['POST'])
def merge_pdfs():
    if 'uploaded_files' not in session or not session['uploaded_files']:
        return jsonify({'success': False, 'error': 'No files to merge'})
    
    try:
        merged_filename = 'merged_document.pdf'
        merged_path = os.path.join(app.config['UPLOAD_FOLDER'], merged_filename)
        pdf_writer = PyPDF2.PdfWriter()
        
        # Sequential merge in user-specified order
        for filepath in session['uploaded_files']:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
        
        with open(merged_path, 'wb') as output_file:
            pdf_writer.write(output_file)
        
        # Clean up
        for filepath in session['uploaded_files']:
            if os.path.exists(filepath):
                os.remove(filepath)
        
        session.pop('uploaded_files', None)
        session['merged_file'] = merged_filename
        return jsonify({'success': True, 'filename': merged_filename})
    
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error merging PDFs: {str(e)}'})

@app.route('/download')
def download_file():
    if 'merged_file' not in session:
        return redirect(url_for('index'))
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], session['merged_file'])
    return send_file(filepath, as_attachment=True, download_name='merged_document.pdf')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
