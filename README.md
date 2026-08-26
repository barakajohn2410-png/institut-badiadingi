# Institut Badiadingi — Résultats scolaires

Application locale sans dépendance externe (Python 3.10+ et SQLite intégrés).

## Lancer

Dans ce dossier, exécutez :

```powershell
python server.py
```

Ou, sous Windows, double-cliquez sur `lancer.ps1` (ou exécutez `./lancer.ps1`).

Ouvrez ensuite `http://localhost:8000` dans votre navigateur.

Premier accès administrateur : **admin** / **changez-moi**. Modifiez ce mot de passe avant la première exécution avec, par exemple :

```powershell
$env:BADIADINGI_ADMIN_PASSWORD='un-mot-de-passe-solide'; python server.py
```

La base de données est créée dans `badiadingi.db`. Elle ne contient aucune donnée réelle : créez les classes, élèves et matières depuis l’espace d’administration.

## Utilisation

1. Connectez-vous dans **Administration**.
2. Créez une classe, puis ses élèves et matières.
3. Saisissez les notes par période (sur 20).
4. Publiez les résultats de la classe et de la période.
5. Les élèves peuvent rechercher leur bulletin avec leur matricule et l’imprimer.

Les moyennes sont pondérées par les coefficients et ne tiennent compte que des matières notées.
