from flask import Flask, render_template, request, redirect
import os, csv, datetime

app = Flask(_name_)

# Page d'accueil
@app.route('/')
def index():
    return render_template('index.html')

# Page d'inscription
@app.route('/inscription')
def inscription_page():
    return render_template('inscription.html')

# Quand parent envoie le formulaire
@app.route('/envoyer', methods=['POST'])
def envoyer():
    nom_parent = request.form.get('nom_parent')
    tel = request.form.get('tel')
    nom_enfant = request.form.get('nom_enfant')
    classe = request.form.get('classe')
    date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # On sauvegarde dans un fichier CSV
    fichier = 'inscriptions.csv'
    existe = os.path.exists(fichier)
    with open(fichier, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Date','Parent','Telephone','Enfant','Classe'])
        writer.writerow([date, nom_parent, tel, nom_enfant, classe])

    return """
    <html><body style="font-family:Arial;text-align:center;padding:50px">
    <h1 style="color:green">✅ Inscription reçue !</h1>
    <p>Merci """ + nom_parent + """, nous avons bien reçu l'inscription de """ + nom_enfant + """ en """ + classe + """.</p>
    <p>Nous vous appelons au """ + tel + """ dans 24h.</p>
    <a href="/" style="background:#0a3d62;color:#fff;padding:10px 20px;text-decoration:none;border-radius:5px">Retour à l'accueil</a>
    </body></html>
    """

# Pour toi: voir toutes les inscriptions
@app.route('/admin-badiadingi-0836')
def admin():
    fichier = 'inscriptions.csv'
    if not os.path.exists(fichier):
        return "Aucune inscription encore"
    with open(fichier, 'r', encoding='utf-8') as f:
        contenu = f.read().replace('\n','<br>')
    return f"<h1>Liste des inscriptions</h1><p>{contenu}</p><a href='/'>Accueil</a>"

if _name_ == '_main_':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
