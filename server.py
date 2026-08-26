from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def home():
    # Cherche index.html partout
    if os.path.exists('index.html'):
        return send_from_directory('.', 'index.html')
    # Si dans un dossier
    for root, dirs, files in os.walk('.'):
        if 'index.html' in files:
            return send_from_directory(root, 'index.html')
    # Sinon liste les fichiers
    files = os.listdir('.')
    return f"Site en ligne mais index.html non trouvé.<br>Fichiers présents: {files}"

@app.route('/<path:path>')
def serve_files(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
