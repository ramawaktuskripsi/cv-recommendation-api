import os
import json
import pdfplumber
import requests
import re
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from rapidfuzz import fuzz
import spacy

# ============================================
# INITIALIZE FLASK APP
# ============================================
app = Flask(__name__)
CORS(app)

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    nlp = None

# ============================================
# CV MATCHING SYSTEM CLASS
# ============================================
class CVMatchingSystem:
    def __init__(self):
        self.cv_raw_text = ""
        self.cv_processed_text = ""
        self.job_data = {}
        self.extracted_info = {'nama': '', 'kontak': {}, 'skills': []}
        self.match_result = {}
        self.nlp = nlp
        
        # Synonym mapping
        self.skill_synonyms = {
            'python': ['python', 'py', 'python3', 'python programming'],
            'javascript': ['javascript', 'js', 'ecmascript', 'node.js', 'nodejs', 'node'],
            'react': ['react', 'reactjs', 'react.js', 'react native'],
            'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'database', 'oracle'],
            'java': ['java', 'javase', 'javaee', 'java programming'],
            'css': ['css', 'css3', 'styling', 'stylesheet'],
            'html': ['html', 'html5', 'markup'],
            'git': ['git', 'github', 'gitlab', 'version control', 'bitbucket'],
            'docker': ['docker', 'containerization', 'container'],
            'api': ['api', 'rest api', 'restful', 'rest'],
            'excel': ['excel', 'microsoft excel', 'ms excel', 'spreadsheet'],
            'leadership': ['leadership', 'team leadership', 'people management', 'team lead'],
            'quality control': ['qc', 'quality control', 'quality assurance', 'qa', 'quality inspector'],
            'operator': ['operator', 'machine operator', 'production operator'],
            'sablon': ['sablon', 'screen printing', 'printing'],
        }
    
    def download_cv_from_url(self, cv_url):
        """Download CV dari URL Supabase"""
        try:
            print(f"📥 Downloading CV from: {cv_url}")
            response = requests.get(cv_url, timeout=30)
            response.raise_for_status()
            
            # Simpan ke temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.close()
            
            print(f"✓ CV downloaded to: {temp_file.name}")
            return temp_file.name
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Error downloading CV: {e}")
            return None
    
    def extract_cv_raw_text(self, cv_path):
        """Extract raw text dari PDF"""
        try:
            with pdfplumber.open(cv_path) as pdf:
                if len(pdf.pages) == 0:
                    return False
                
                self.cv_raw_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        self.cv_raw_text += page_text + "\n"
                
                MIN_CHARS = 50
                if len(self.cv_raw_text.strip()) < MIN_CHARS:
                    print(f"❌ CV tidak dapat dibaca (hanya {len(self.cv_raw_text.strip())} karakter)")
                    return False
                
                print(f"✓ CV extracted ({len(self.cv_raw_text)} karakter)")
                return True
        
        except Exception as e:
            print(f"❌ Error extracting CV: {e}")
            return False
    
    def preprocess_text(self):
        """Pre-processing text"""
        text = self.cv_raw_text
        
        # Remove bullets
        text = re.sub(r'[•○●◦▪▫■□▸▹►▻]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        self.cv_processed_text = text.strip()
        print(f"✓ Pre-processing done ({len(self.cv_processed_text)} karakter)")
        return self.cv_processed_text
    
    def extract_name_regex(self, text):
        """Extract nama dengan regex"""
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if len(line.split()) >= 2 and len(line.split()) <= 4:
                if line.isupper() or line.istitle():
                    if not re.search(r'\d{3,}|@', line):
                        return line
        return None
    
    def extract_name_ner(self, text):
        """Extract nama dengan NER"""
        if not self.nlp:
            return None
        
        doc = self.nlp(text[:500])
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text
        return None
    
    def extract_name(self):
        """Extract nama (Regex + NER)"""
        nama = self.extract_name_regex(self.cv_processed_text)
        if not nama:
            nama = self.extract_name_ner(self.cv_processed_text)
        
        self.extracted_info['nama'] = nama if nama else "Tidak ditemukan"
        return nama
    
    def extract_contact(self):
        """Extract email dan phone"""
        text = self.cv_processed_text
        
        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Phone
        phone_patterns = [
            r'\+62[-\s]?\d{2,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',  # +62-831-8282-7181
            r'62[-\s]?\d{2,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',
            r'0\d{2,3}[-\s]\d{3,4}[-\s]\d{3,4}',
            r'0\d{9,12}',
            r'\+?62\d{9,12}',
        ]
        
        phone = None
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                phone = max(phones, key=len)
                phone = re.sub(r'\s+', ' ', phone.replace('\n', ' ')).strip()
                break
        
        self.extracted_info['kontak'] = {
            'email': emails[0] if emails else None,
            'phone': phone
        }
        
        return self.extracted_info['kontak']
    
    def get_skill_variations(self, skill):
        """Get variations dari synonym mapping"""
        skill_lower = skill.lower()
        variations = [skill_lower]
        
        for key, synonyms in self.skill_synonyms.items():
            if skill_lower == key or skill_lower in synonyms:
                variations.extend(synonyms)
                variations.append(key)
        
        return list(set(variations))
    
    def fuzzy_match_skill(self, cv_text, skill, threshold=75):
        """Fuzzy matching dengan RapidFuzz"""
        cv_text_lower = cv_text.lower()
        variations = self.get_skill_variations(skill)
        
        for variation in variations:
            score = fuzz.token_set_ratio(variation, cv_text_lower)
            if score >= threshold:
                return True
        
        return False
    
    def extract_skills(self, required_skills_or_job_title):
        """Extract skills dari CV"""
        text = self.cv_processed_text
        found_skills = set()
        
        # Jika list = required skills
        if isinstance(required_skills_or_job_title, list):
            search_skills = required_skills_or_job_title
        else:
            # Jika string = job title, split jadi kata-kata
            job_title = required_skills_or_job_title.lower()
            search_skills = [word.strip() for word in job_title.split() if len(word.strip()) > 2]
        
        # Match skills
        for skill in search_skills:
            variations = self.get_skill_variations(skill)
            text_lower = text.lower()
            
            # Exact match
            for variation in variations:
                if variation in text_lower:
                    found_skills.add(skill)
                    break
            
            # Fuzzy match
            if skill not in found_skills:
                if self.fuzzy_match_skill(text, skill, threshold=75):
                    found_skills.add(skill)
        
        self.extracted_info['skills'] = list(found_skills)
        return list(found_skills)
    
    def extract_information(self):
        """Extract semua informasi (Nama, Kontak, Skills)"""
        print("\n🔍 Extracting information...")
        
        self.extract_name()
        print(f"  ✓ Nama: {self.extracted_info['nama']}")
        
        contact = self.extract_contact()
        print(f"  ✓ Email: {contact.get('email', 'N/A')}")
        print(f"  ✓ Phone: {contact.get('phone', 'N/A')}")
        
        # Extract skills
        if self.job_data.get('required_skill'):
            skills = self.extract_skills(self.job_data['required_skill'])
        else:
            skills = self.extract_skills(self.job_data['job_title'])
        
        print(f"  ✓ Skills: {', '.join(skills) if skills else 'None'}")
    
    def skill_matching(self):
        """Skill matching"""
        print("\n🎯 Skill matching...")
        
        cv_skills = self.extracted_info['skills']
        required_skills = self.job_data.get('required_skill', [])
        job_title = self.job_data.get('job_title', '')
        
        matched_skills = []
        
        if required_skills:
            # Match dengan required skills
            for skill in cv_skills:
                if skill in required_skills:
                    matched_skills.append(skill)
            total_required = len(required_skills)
        else:
            # Match dengan job title
            matched_skills = cv_skills
            total_required = 1
        
        self.match_result = {
            'match_count': len(matched_skills),
            'matched_skills': matched_skills,
            'total_required': total_required
        }
        
        print(f"  ✓ Matched: {len(matched_skills)}/{total_required}")
    
    def calculate_percentage(self):
        """Calculate percentage"""
        if self.match_result['match_count'] > 0:
            percentage = (self.match_result['match_count'] / 
                         self.match_result['total_required']) * 100
            return round(percentage, 2)
        return 0
    
    def prepare_response(self):
        """Prepare response"""
        response_data = {
            'nama': self.extracted_info['nama'],
            'kontak': self.extracted_info['kontak']
        }
        
        # Jika match > 0
        if self.match_result['match_count'] > 0:
            percentage = self.calculate_percentage()
            response_data.update({
                'skill': self.extracted_info['skills'],
                'skill_required': self.job_data.get('required_skill', [self.job_data.get('job_title')]),
                'status': 'RECOMMENDED',
                'persentase': f"{percentage}%"
            })
            print(f"\n✅ Status: RECOMMENDED ({percentage}%)")
        else:
            print(f"\n❌ Status: NOT RECOMMENDED")
        
        return response_data
    
    def process_from_url(self, cv_url, job_data):
        """
        Main process: Download CV dari URL dan proses matching
        
        Args:
            cv_url: URL CV dari Supabase
            job_data: Dict dengan job_title dan required_skill
        
        Returns:
            dict: Response data
        """
        print("=" * 70)
        print("🚀 CV MATCHING PROCESS")
        print("=" * 70)
        print(f"Job Title: {job_data.get('job_title')}")
        print(f"Required Skills: {job_data.get('required_skill', [])}")
        print("=" * 70)
        
        self.job_data = job_data
        
        # Step 1: Download CV
        cv_path = self.download_cv_from_url(cv_url)
        if not cv_path:
            return {
                'success': False,
                'error': 'Gagal download CV',
                'error_code': 'DOWNLOAD_FAILED'
            }
        
        try:
            # Step 2: Extract raw text
            if not self.extract_cv_raw_text(cv_path):
                return {
                    'success': False,
                    'error': 'CV tidak dapat dibaca',
                    'error_code': 'UNREADABLE_CV',
                    'details': 'PDF mungkin scan/image, corrupt, atau password-protected'
                }
            
            # Step 3: Preprocess
            self.preprocess_text()
            
            # Step 4: Extract information
            self.extract_information()
            
            # Step 5: Skill matching
            self.skill_matching()
            
            # Step 6: Prepare response
            response_data = self.prepare_response()
            response_data['success'] = True
            
            print("=" * 70)
            
            return response_data
        
        finally:
            # Cleanup: hapus temporary file
            try:
                if cv_path and os.path.exists(cv_path):
                    os.remove(cv_path)
                    print(f"🗑️  Temp file deleted: {cv_path}")
            except Exception as e:
                print(f"⚠️  Failed to delete temp file: {e}")


# ============================================
# API ROUTES
# ============================================

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        'message': 'CV Matching API is running',
        'version': '1.0.0',
        'status': 'healthy',
        'endpoints': {
            'match': '/api/match (POST)',
            'health': '/api/health (GET)'
        }
    })

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'spacy_model': 'loaded' if nlp else 'not loaded'
    })

@app.route('/api/match', methods=['POST'])
def match_cv():
    """
    Endpoint untuk matching CV
    
    Request Body (JSON):
    {
        "uri_cv": "https://supabase.storage.url/cv.pdf",
        "job_title": "Operator Sablon",
        "required_skill": ["Operator", "Sablon"]  // Optional
    }
    
    Response:
    {
        "success": true,
        "nama": "John Doe",
        "kontak": {
            "email": "john@example.com",
            "phone": "0821-xxxx-xxxx"
        },
        "skill": ["operator", "sablon"],
        "skill_required": ["Operator", "Sablon"],
        "status": "RECOMMENDED",
        "persentase": "100.0%"
    }
    """
    try:
        # Get data dari request
        data = request.get_json()
        
        # Validasi input
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is empty',
                'error_code': 'EMPTY_REQUEST'
            }), 400
        
        if 'uri_cv' not in data:
            return jsonify({
                'success': False,
                'error': 'uri_cv is required',
                'error_code': 'MISSING_URI_CV'
            }), 400
        
        if 'job_title' not in data:
            return jsonify({
                'success': False,
                'error': 'job_title is required',
                'error_code': 'MISSING_JOB_TITLE'
            }), 400
        
        # Extract data
        cv_url = data.get('uri_cv')
        job_data = {
            'job_title': data.get('job_title'),
            'required_skill': data.get('required_skill', [])
        }
        
        # Process CV
        matcher = CVMatchingSystem()
        result = matcher.process_from_url(cv_url, job_data)
        
        # Return response
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'SERVER_ERROR'
        }), 500


# ============================================
# VERCEL HANDLER (PENTING!)
# ============================================

# JANGAN gunakan app.run() untuk Vercel
# Export app langsung tanpa handler wrapper

# Untuk local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)