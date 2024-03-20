from flask import Flask, render_template, request, redirect, url_for ,session
from pymongo import MongoClient, ReturnDocument
from werkzeug.security import check_password_hash

from werkzeug.utils import secure_filename
import os
app = Flask(__name__)
app.config['SECRET_KEY'] = 'aymanmady'

# Connect to MongoDB
client = MongoClient('localhost', 27017)
db = client['mini']
candidats = db['candidat']
electeurs = db['electeur']

# Définir le répertoire de téléchargement des images
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/home')
def home():
    # Initialisation du dictionnaire pour stocker le nombre de votes par candidat
    votes_par_candidat = {}

    # Récupération de tous les candidats depuis la collection "candidats"
    candidats_list = candidats.find()

    # Calcul du nombre total des candidats
    nombre_total_candidats = candidats.count_documents({})

    # Calcul du nombre total d'électeurs éligibles
    nombre_total_electeurs = electeurs.count_documents({})

    # Calcul du nombre total de votes
    total_votes = 0

    # Calcul du nombre de votes pour chaque candidat
    for candidat in candidats_list:
        # Récupération de la liste des électeurs qui ont voté pour ce candidat
        electeurs_votants = candidat.get('electeurs', [])
        # Nombre de votes pour ce candidat est la longueur de cette liste
        nombre_votes = len(electeurs_votants)
        # Stockage dans le dictionnaire avec le nom du candidat au lieu de son NNI
        votes_par_candidat[candidat['nom'] + " " + candidat['prenom']] = {
            'nombre_votes': nombre_votes,
            'image': candidat.get('image', ''),  # Assurez-vous que 'image' est un champ de votre modèle de données candidat
            'parti': candidat.get('parti', '')  # Assurez-vous que 'parti' est un champ de votre modèle de données candidat
        }
        # Ajout du nombre de votes pour ce candidat au total des votes
        total_votes += nombre_votes

    # Calcul du pourcentage de participation
    taux_participation = (total_votes / nombre_total_electeurs) * 100 if nombre_total_electeurs != 0 else 0

    # Calcul du pourcentage de votes pour chaque candidat
    pourcentage_votes_par_candidat = {}
    for candidat, info in votes_par_candidat.items():
        pourcentage_votes_par_candidat[candidat] = (info['nombre_votes'] / total_votes) * 100 if total_votes != 0 else 0

    # Trier les candidats par nombre de votes (en ordre décroissant)
    candidats_tries = sorted(votes_par_candidat.items(), key=lambda x: x[1]['nombre_votes'], reverse=True)

    # Récupérer le candidat gagnant
    candidat_gagnant = candidats_tries[0][0] if candidats_tries else None

    # Rendu du modèle avec les données calculées
    return render_template('home.html', votes_par_candidat=votes_par_candidat,
                           pourcentage_votes_par_candidat=pourcentage_votes_par_candidat,
                           taux_participation=taux_participation,
                           candidats_tries=candidats_tries,
                           candidat_gagnant=candidat_gagnant,
                           nombre_total_candidats=nombre_total_candidats,
                           nombre_total_electeurs=nombre_total_electeurs)

@app.route('/index')
def index():
    nombre_total_candidats = candidats.count_documents({})

    nombre_total_electeurs = electeurs.count_documents({})

    return render_template('index.html',nombre_total_candidats=nombre_total_candidats,nombre_total_electeurs=nombre_total_electeurs)


#--------------------------------------------------------------- authentification -------------------------------------------------------------------#

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        nni = request.form['nni']
        user = electeurs.find_one({'NNI': nni})
        if nni == "4197446810" and password == "admin" :
            session['password'] = password
            session['NNI'] = nni
            return redirect(url_for('home'))
        if user  :
            session['password'] = "admin"
            session['NNI'] = "4197446810"
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

#------------------------------------------------------- candidat ----------------------------------------------------------#


@app.route('/candidats')
def candidat():
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    
    all_candidats = candidats.find({})
    return render_template('candidats.html', candidats=all_candidats)

@app.route('/electeurs')
def electeur():
    if 'NNI' not in session and session["NNI"]!="4197446810" :  
        return redirect(url_for('login'))
    
    all_electeurs = electeurs.find({})
    return render_template('electeurs.html', electeurs=all_electeurs)


@app.route('/ajouter_candidat')
def ajouter_candidat():
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    return render_template('addcandidat.html')

@app.route('/add_candidat', methods=['POST'])
def add_candidat():
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    
    candidat_data = {
        'NNI': request.form['NNI'],
        'nom': request.form['nom'],
        'prenom': request.form['prenom'],
        'age': request.form['age'],
        'parti': request.form['parti'],
        'image': ''  # Champ pour stocker le chemin de l'image
    }

    # Vérifier si un fichier image a été envoyé
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename != '':
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            filepath = filepath.replace('\\', '/')
            image_file.save(filepath)
            candidat_data['image'] = filepath

    candidats.insert_one(candidat_data)
    return redirect(url_for('candidat'))


@app.route('/modifier_candidat/<nni>', methods=['GET', 'POST'])
def modifier_candidat(nni):
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    if request.method == 'GET':
        candidat = candidats.find_one({'NNI': nni})
        return render_template('editcandidat.html', candidat=candidat)
    elif request.method == 'POST':
        candidats.update_one({'NNI': request.form['NNI']}, {'$set': {
            "NNI": request.form['NNI'],
            "nom": request.form['nom'],
            "prenom": request.form['prenom'],
            "age": request.form['age'],
            "parti": request.form['parti']
        }})
        
        return redirect(url_for('candidat'))


@app.route('/supprimer_candidat/<nni>')
def supprimer_candidat(nni):
    candidats.delete_one({'NNI': nni})
    return redirect(url_for('candidat'))


#------------------------------------------- electeur -------------------------------------------------------#


@app.route('/ajouter_electeur')
def ajouter_electeur():
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    return render_template('addelecteur.html')


@app.route('/add_electeur', methods=['POST'])
def add_electeur():
    if 'NNI' not in session :  
        return redirect(url_for('login'))
    
    electeur_data = {
        'NNI': request.form['NNI'],
        'nom': request.form['nom'],
        'prenom': request.form['prenom'],
        'age': request.form['age'],
    }
    electeurs.insert_one(electeur_data)
    return redirect(url_for('electeur'))


@app.route('/modifier_electeur/<nni>', methods=['GET', 'POST'])
def modifier_electeur(nni):
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    if request.method == 'GET':
        electeur = electeurs.find_one({'NNI': nni})
        return render_template('editelecteur.html', electeur=electeur)
    elif request.method == 'POST':
        electeurs.update_one({'NNI': request.form['NNI']}, {'$set': {
            "NNI": request.form['NNI'],
            "nom": request.form['nom'],
            "prenom": request.form['prenom'],
            "age": request.form['age'],
        }})
        return redirect(url_for('electeur'))


@app.route('/supprimer_electeur/<nni>')
def supprimer_electeur(nni):
    electeurs.delete_one({'NNI': nni})
    return redirect(url_for('electeur'))

#----------------------------------------------------------- voter -------------------------------------------------------------------

@app.route('/vote')
def vote():
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    all_candidats = candidats.find({})
    message = request.args.get('message', None)
    return render_template('vote.html', candidats=all_candidats, message=message)


@app.route('/add_vote', methods=['POST'])
def add_vote():
    if 'NNI' not in session:  
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        candidats_votants = candidats.count_documents({'electeurs': request.form['electeur']})
        if candidats_votants > 0:
            return redirect(url_for('vote', message="Vous avez déjà voté et vous ne pouvez voter qu'une seule fois."))

        candidats.update_one({'NNI': request.form['candidat']}, {'$push': {
            'electeurs': request.form['electeur']
        }})

    return redirect(url_for('vote'))

if __name__ == '__main__':
    app.run(debug=True)
