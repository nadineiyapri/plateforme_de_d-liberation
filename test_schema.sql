-- ==========================================
-- 1. NETTOYAGE (Pour éviter les erreurs "table already exists")
-- ==========================================
DROP TABLE IF EXISTS admin;
DROP TABLE IF EXISTS prof;
DROP TABLE IF EXISTS etudiant;
DROP TABLE IF EXISTS users;

-- ==========================================
-- 2. CRÉATION DES TABLES (Héritage)
-- ==========================================
CREATE TABLE users (
    iduser INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL
); 

CREATE TABLE etudiant (
    idetu INTEGER PRIMARY KEY,
    filliere TEXT,
    FOREIGN KEY (idetu) REFERENCES users(iduser) ON DELETE CASCADE
);

CREATE TABLE prof (
    idprof INTEGER PRIMARY KEY,
    module TEXT,
    FOREIGN KEY (idprof) REFERENCES users(iduser) ON DELETE CASCADE
);

CREATE TABLE admin (
    idadmin INTEGER PRIMARY KEY,
    FOREIGN KEY (idadmin) REFERENCES users(iduser) ON DELETE CASCADE
);

-- ==========================================
-- 3. INSERTION DE TEST (L'ordre est crucial !)
-- ==========================================

-- On crée d'abord l'humain dans 'users'
INSERT INTO users (nom, prenom) VALUES ('Sekher', 'Nadine'); -- Aura l'ID 1
INSERT INTO users (nom, prenom) VALUES ('Do', 'Cécilia');     -- Aura l'ID 2

-- On lui donne son rôle dans 'etudiant' ou 'prof' en utilisant le même ID
INSERT INTO etudiant (idetu, filliere) VALUES (1, 'Informatique');
INSERT INTO prof (idprof, module) VALUES (2, 'Base de données');

-- ==========================================
-- 4. LE TEST DE RÉUSSITE (La Jointure)
-- ==========================================
SELECT 
    u.iduser, 
    u.nom, 
    u.prenom, 
    e.filliere AS specialite_ou_module
FROM users u
JOIN etudiant e ON u.iduser = e.idetu

UNION ALL

SELECT 
    u.iduser, 
    u.nom, 
    u.prenom, 
    p.module
FROM users u
JOIN prof p ON u.iduser = p.idprof;