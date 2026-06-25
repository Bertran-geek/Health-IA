# Health Campaign AI Microservice

Health Campaign AI est un assistant intelligent léger et sécurisé qui se connecte à la base de données MySQL `health_campaign_manager` existante. Il comprend automatiquement le schéma de la base, transforme des questions en langage naturel (français et anglais) en requêtes SQL sécurisées et en lecture seule, les exécute, et retourne des réponses compréhensibles avec des statistiques, des graphiques et une interprétation des tendances.

Le projet est construit avec FastAPI, SQLAlchemy, LangChain, LangGraph et utilise l'IA Groq (modèle `llama-3.3-70b-versatile`) avec une interface React.

## Description du projet

Ce microservice permet aux utilisateurs de poser des questions en français ou en anglais sur les données de santé de la base de données `health_campaign_manager`. Le système génère automatiquement des requêtes SQL sécurisées (SELECT uniquement), les exécute et présente les résultats sous forme de réponses textuelles, de graphiques et d'analyses de tendances.

## Fonctionnalités principales

- Découverte automatique du schéma de la base de données via SQLAlchemy (tables, colonnes, clés étrangères)
- Génération SQL à partir du langage naturel basée sur le schéma en temps réel
- Sécurité SELECT-only : rejette INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE et autres attaques SQL
- Exécution en lecture seule avec limitation stricte des lignes et timeout
- Graphiques (bar/line/pie) retournés en base64 PNG avec spécification structurée
- Interprétation des tendances (direction, min/max, moyenne) en français et anglais
- Authentification JWT + API key, limitation de débit, CORS, prêt pour HTTPS
- Cache Redis optionnel pour les questions répétées
- Fonctionne sur 8 Go RAM / 4 CPU : IA <= 3 Go, API <= 500 Mo

## Architecture

Le pipeline de traitement fonctionne comme suit :

1. Question en français ou anglais
2. Détection de la langue
3. Contexte du schéma (inspection SQLAlchemy + indices de domaine)
4. Génération SQL par LLM (Groq)
5. Validateur SQL (SELECT-only, porte de sécurité stricte) avec retry automatique en cas d'échec
6. Exécution en lecture seule (limite de lignes + timeout)
7. Formatage de la réponse en langage naturel par LLM
8. Analyse : graphique (matplotlib) + description des tendances

Le pipeline est implémenté comme une machine à états LangGraph dans `app/ai/graph.py` avec retry automatique unique si la génération/validation/exécution échoue.

## Structure des dossiers

```
health_campaign_ai/
├── app/
│   ├── api/            # Routes FastAPI
│   ├── ai/             # Client LLM, générateur SQL, formateur, LangGraph
│   ├── database/       # connexion, lecteur de schéma, exécuteur
│   ├── security/       # validateur SQL, auth (JWT/API key), limitation de débit
│   ├── services/       # analytics (graphiques/tendances), cache
│   ├── models/         # Schémas Pydantic
│   ├── config.py
│   └── main.py
├── frontend/        # Frontend React + Vite + TailwindCSS
│   ├── src/
│   │   ├── components/  # Composants UI
│   │   ├── api.ts        # Client API
│   │   ├── types.ts      # Types TypeScript
│   │   └── App.tsx       # Application principale
│   └── dist/         # Frontend buildé (servi par FastAPI)
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### Prérequis

- Docker + Docker Compose
- La base de données Health Campaign déjà en cours d'exécution, exposant le réseau externe `health_campaign_manager_default` et le conteneur `health_campaign_db`

Vérifiez que le réseau existe :

```bash
docker network ls | grep health
```

### 1. Configuration de l'environnement

```bash
cd health_campaign_ai
cp .env.example .env
# Editez .env : changez JWT_SECRET, API_KEYS, ADMIN_PASSWORD, définissez GROQ_API_KEY
```

### 2. Build et démarrage

```bash
docker compose up -d --build
```

Obtenez votre clé API gratuite Groq sur https://console.groq.com/keys et définissez `GROQ_API_KEY` dans `.env`.

### 3. Vérification

```bash
curl http://localhost:8001/health
```

Ouvrez le frontend : http://localhost:8001

Ouvrez la documentation API : http://localhost:8001/docs

## Guide de déploiement

### Choix du modèle Groq

Définissez `GROQ_MODEL` dans `.env` :

1. `llama-3.3-70b-versatile` (par défaut, meilleure qualité)
2. `llama-3.1-8b-instant` (le plus rapide)
3. `mixtral-8x7b-32768` (contexte long)
4. `gemma2-9b-it`

Tous les modèles sont servis en ligne par Groq, pas besoin de GPU local ni de RAM.

### HTTPS

Terminez TLS via un reverse proxy (Nginx/Caddy/Traefik) devant `ai_backend:8001`. Exemple Caddy :

```
ai.example.com {
    reverse_proxy localhost:8001
}
```

### Activer le cache Redis

Dans `.env` :

```
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
```

### Utilisateur DB en lecture seule (recommandé)

Bien que l'application impose SELECT-only, créez un utilisateur DB avec uniquement les privilèges `SELECT` pour une défense en profondeur et pointez `DB_URL` vers lui.

```sql
CREATE USER 'health_ai'@'%' IDENTIFIED BY 'strong_password';
GRANT SELECT ON health_campaign_manager.* TO 'health_ai'@'%';
FLUSH PRIVILEGES;
```

## Référence API

Tous les endpoints except `/health` et `/` nécessitent une authentification via l'un des deux :

- `Authorization: Bearer <JWT>` (obtenu depuis `/auth/login`), ou
- `X-API-Key: <key>` (depuis `API_KEYS` dans `.env`)

### POST /auth/login

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Réponse :

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 7200 }
```

### POST /ai/query

Corps :

```json
{ "question": "Combien d'enfants ont été vaccinés dans la région du Centre ?", "include_chart": true }
```

Exemple avec API key :

```bash
curl -X POST http://localhost:8001/ai/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-api-key-change-me" \
  -d '{"question":"Quel ASBC a vacciné le plus de personnes ?"}'
```

Réponse :

```json
{
  "answer": "L'ASBC Jean Ouédraogo a vacciné 320 personnes, soit le total le plus élevé.",
  "sql": "SELECT ch.nom, ch.prenom, SUM(t.vaccinate) AS vaccinated FROM chw ch LEFT JOIN target t ON t.chw_id = ch.id_chw GROUP BY ch.id_chw ORDER BY vaccinated DESC LIMIT 10",
  "columns": ["nom", "prenom", "vaccinated"],
  "rows": [{"nom": "Ouédraogo", "prenom": "Jean", "vaccinated": 320}],
  "row_count": 10,
  "chart": { "type": "bar", "title": "vaccinated by nom", "image_base64": "iVBORw0..." },
  "trend": "Trend is decreasing for 'vaccinated': from 320 to 12 (min 12, max 320, avg 95.4).",
  "language": "fr",
  "cached": false,
  "elapsed_ms": 1840
}
```

Le `chart.image_base64` est un PNG que vous pouvez rendre directement : `<img src="data:image/png;base64,{image_base64}">`.

### GET /ai/schema

```bash
curl http://localhost:8001/ai/schema?counts=true \
  -H "X-API-Key: demo-api-key-change-me"
```

### GET /health

```bash
curl http://localhost:8001/health
```

### Exemples de questions

- "Montre-moi la couverture vaccinale par campagne"
- "How many vaccinated children are in the Centre region?"
- "Quelle est la répartition des cibles par tranche d'âge ?"
- "List active campaigns with their regions"
- "Top 5 départements par nombre de bénéficiaires"

## Bonnes pratiques de sécurité

- Application stricte SELECT-only dans `app/security/sql_validator.py` (liste de refus, suppression de commentaires, exécution d'instruction unique, blocage INTO/OUTFILE)
- Transaction en lecture seule + MAX_EXECUTION_TIME + limite LIMIT stricte sur chaque requête
- Authentification : JWT (HS256) et/ou API keys ; comparaison à temps constant
- Limitation de débit par IP client (RATE_LIMIT, par défaut 30/minute)
- Utilisateur conteneur non-root, image de base minimale, healthchecks
- Secrets via `.env` — jamais codés en dur. Changez JWT_SECRET, API_KEYS, ADMIN_PASSWORD avant la production
- Utilisateur DB avec privilèges minimum (GRANT SELECT uniquement) recommandé
- HTTPS via reverse proxy

## Développement du frontend

Le frontend React se trouve dans `frontend/`. Pour le développement avec hot-reload :

```bash
cd frontend
npm install
npm run dev
```

Cela démarre un serveur de développement sur http://localhost:5173 qui proxy `/api/*` vers le backend FastAPI sur le port 8001.

Pour build pour la production (servi par FastAPI) :

```bash
cd frontend
npm run build
```

Les fichiers buildés vont dans `frontend/dist/` et sont servis automatiquement par FastAPI lorsque le répertoire existe.

## Exécution des tests

Le validateur SQL a des tests de régression (le composant le plus critique pour la sécurité) :

```bash
pip install -r requirements.txt
pytest -q
```

## Dépannage

| Symptôme | Solution |
|---------|----------|
| `health.database = down` | Vérifiez `DB_URL`, assurez-vous que le conteneur DB est sur le même réseau |
| `health.llm = down` | `GROQ_API_KEY` non défini ou invalide ; vérifiez `.env` |
| Réseau non trouvé | Démarrez d'abord la stack DB principale pour que `health_campaign_manager_default` existe |
| Première requête lente | Démarrage à froid de Groq ; les appels suivants sont plus rapides |
| Mémoire insuffisante | Réduisez les workers API ou utilisez une machine plus petite |

## Identifiants par défaut

Pour tester l'application :

- Login JWT : username `admin`, password `admin123`
- API Key : `demo-api-key-change-me`

## Licence

Projet interne — adaptez selon vos besoins.
