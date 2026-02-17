from flask import jsonify

@app.route('/tables', methods=['GET'])
def view_tables():
    users = [dict(id=u.iduser, nom=u.nom, prenom=u.prenom, role=u.role) for u in User.query.all()]
    themes = [dict(id=t.id_theme, nom=t.nom_theme, admin=t.admin.nom) for t in Theme.query.all()]
    debats = [dict(id=d.id_debat, titre=d.titre, theme=d.theme.nom_theme, createur=d.createur.nom) for d in Debat.query.all()]
    arguments = [dict(
        id=a.id_argument,
        texte=a.texte,
        type=a.type,
        debat=a.debat.titre,
        auteur=a.auteur.nom,
        parent=a.id_parent
    ) for a in Argument.query.all()]
    
    return jsonify({
        "users": users,
        "themes": themes,
        "debats": debats,
        "arguments": arguments
    })
