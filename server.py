from flask import Flask, send_from_directory
import os

app = Flask(_name_)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def files(path):
    return send_from_directory('.', path)

if _name_ == '_main_':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
