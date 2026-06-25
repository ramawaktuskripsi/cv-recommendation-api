# CV Parser & Skill Matcher API

API untuk parsing CV dan skill matching menggunakan NLP.

## Features
- CV Parsing (PDF/DOCX)
- Named Entity Recognition
- Fuzzy String Matching
- Synonym Mapping
- Skill Matching Algorithm

## Tech Stack
- Python 3.9
- Flask
- spaCy
- NLTK
- RapidFuzz

## Deployment
- Platform: Railway
- URL: https://your-app.up.railway.app

## API Endpoints
- `GET /api/health` - Health check
- `POST /api/process-complete` - Process CV from URL

## Local Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```