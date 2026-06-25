import os
import ipaddress
import pdfplumber
import requests
import re
import socket
import tempfile
from urllib.parse import urljoin, urlparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from rapidfuzz import fuzz

# ============================================
# INITIALIZE FLASK APP
# ============================================
app = Flask(__name__)

# CORS Configuration
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",  # Local development
            "https://prototypesiapkerja.vercel.app",   # Vercel deployments
        ],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

MAX_CV_SIZE_BYTES = 10 * 1024 * 1024
MAX_CV_REDIRECTS = 3
DEFAULT_ALLOWED_CV_HOSTS = "supabase.co"


class CVURLValidationError(ValueError):
    pass


class CVDownloadError(Exception):
    pass

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
        self.target_skills = []
        self.download_error = None
        
        # Synonym mapping
        self.skill_synonyms = {
            'excel': ['excel', 'microsoft excel', 'ms excel', 'spreadsheet'],
            'leadership': ['leadership', 'team leadership', 'people management', 'team lead'],
            'quality control': ['qc', 'quality control', 'quality assurance', 'qa', 'quality inspector'],
            'operator': ['operator', 'machine operator', 'production operator'],
            'sablon': ['sablon', 'screen printing', 'printing'],
            'ppic': ['ppic','production planning','production planner','production scheduling','production control','inventory control','material planning','material requirement planning','mrp'],
        }
    
    @staticmethod
    def validate_cv_url(cv_url):
        """Validasi URL agar downloader hanya mengakses storage publik yang diizinkan."""
        if not isinstance(cv_url, str) or not cv_url.strip():
            raise CVURLValidationError("uri_cv harus berupa URL")

        try:
            parsed_url = urlparse(cv_url.strip())
            port = parsed_url.port
        except ValueError as exc:
            raise CVURLValidationError("Format uri_cv tidak valid") from exc

        if parsed_url.scheme != "https":
            raise CVURLValidationError("uri_cv harus menggunakan HTTPS")
        if not parsed_url.hostname or parsed_url.username or parsed_url.password:
            raise CVURLValidationError("Host uri_cv tidak valid")
        if port not in (None, 443):
            raise CVURLValidationError("Port uri_cv tidak diizinkan")

        hostname = parsed_url.hostname.lower().rstrip(".")
        configured_hosts = os.getenv(
            "CV_ALLOWED_HOSTS",
            DEFAULT_ALLOWED_CV_HOSTS
        )
        allowed_hosts = [
            host.strip().lower().lstrip(".").rstrip(".")
            for host in configured_hosts.split(",")
            if host.strip()
        ]
        if not any(
            hostname == allowed_host or hostname.endswith(f".{allowed_host}")
            for allowed_host in allowed_hosts
        ):
            raise CVURLValidationError("Host uri_cv tidak diizinkan")

        try:
            addresses = socket.getaddrinfo(
                hostname,
                port or 443,
                type=socket.SOCK_STREAM
            )
        except socket.gaierror as exc:
            raise CVURLValidationError("Host uri_cv tidak dapat ditemukan") from exc

        if not addresses:
            raise CVURLValidationError("Host uri_cv tidak memiliki alamat IP")

        for address in addresses:
            ip_value = address[4][0].split("%", 1)[0]
            if not ipaddress.ip_address(ip_value).is_global:
                raise CVURLValidationError(
                    "Host uri_cv mengarah ke jaringan internal"
                )

        return parsed_url.geturl()

    @staticmethod
    def _save_pdf_response(response):
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_CV_SIZE_BYTES:
                    raise CVDownloadError("Ukuran CV melebihi batas 10 MB")
            except ValueError as exc:
                raise CVDownloadError("Content-Length CV tidak valid") from exc

        temp_path = None
        total_size = 0
        signature = bytearray()

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_path = temp_file.name
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue

                    total_size += len(chunk)
                    if total_size > MAX_CV_SIZE_BYTES:
                        raise CVDownloadError("Ukuran CV melebihi batas 10 MB")

                    if len(signature) < 5:
                        signature.extend(chunk[:5 - len(signature)])
                    temp_file.write(chunk)

            if total_size == 0 or bytes(signature) != b"%PDF-":
                raise CVDownloadError("File dari uri_cv bukan PDF yang valid")

            return temp_path
        except Exception:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def download_cv_from_url(self, cv_url):
        """Download CV dari URL storage yang sudah tervalidasi."""
        self.download_error = None
        current_url = cv_url

        try:
            for redirect_count in range(MAX_CV_REDIRECTS + 1):
                current_url = self.validate_cv_url(current_url)
                print(f" Downloading CV from: {current_url}")

                response = requests.get(
                    current_url,
                    timeout=30,
                    allow_redirects=False,
                    stream=True
                )
                with response:
                    if response.is_redirect or response.is_permanent_redirect:
                        location = response.headers.get("Location")
                        if not location:
                            raise CVDownloadError(
                                "Redirect CV tidak memiliki tujuan"
                            )
                        if redirect_count >= MAX_CV_REDIRECTS:
                            raise CVDownloadError(
                                "Redirect CV melebihi batas"
                            )
                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()
                    temp_path = self._save_pdf_response(response)
                    print(f"CV downloaded to: {temp_path}")
                    return temp_path

        except CVURLValidationError as e:
            print(f"Invalid CV URL: {e}")
            self.download_error = {
                'success': False,
                'error': str(e),
                'error_code': 'INVALID_CV_URL'
            }
        except (CVDownloadError, requests.exceptions.RequestException, OSError) as e:
            print(f"Error downloading CV: {e}")
            self.download_error = {
                'success': False,
                'error': 'Gagal download CV',
                'error_code': 'DOWNLOAD_FAILED',
                'details': str(e)
            }

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
                    print(f"CV tidak dapat dibaca (hanya {len(self.cv_raw_text.strip())} karakter)")
                    return False
                
                print(f"CV extracted ({len(self.cv_raw_text)} karakter)")
                return True
        
        except Exception as e:
            print(f"Error extracting CV: {e}")
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
        print(f"Pre-processing done ({len(self.cv_processed_text)} karakter)")
        return self.cv_processed_text

    @staticmethod
    def normalize_name_candidate(value):
        """Rapikan kandidat nama tanpa mengubah kapitalisasinya."""
        return re.sub(r'\s+', ' ', value).strip(" \t:-|")

    def is_valid_name_candidate(
        self,
        value,
        allow_single_word=False,
        require_name_case=True
    ):
        """Validasi kandidat nama dan tolak headline/section CV."""
        candidate = self.normalize_name_candidate(value)
        words = candidate.split()
        min_words = 1 if allow_single_word else 2

        if not min_words <= len(words) <= 5:
            return False
        if len(candidate) > 60:
            return False
        if re.search(r'\d|@|https?://|www\.', candidate, re.IGNORECASE):
            return False
        if any(
            not (
                character.isalpha()
                or character.isspace()
                or character in ".'-"
            )
            for character in candidate
        ):
            return False
        if require_name_case and not (
            candidate.isupper() or candidate.istitle()
        ):
            return False

        blocked_phrases = {
            'curriculum vitae',
            'daftar riwayat hidup',
            'fresh graduate',
            'lulusan baru',
            'personal profile',
            'profil pribadi',
            'tentang saya',
        }
        blocked_words = {
            'about', 'address', 'alamat', 'baru', 'contact', 'curriculum',
            'data', 'developer', 'education', 'email', 'engineer',
            'experience', 'fresh', 'graduate', 'keahlian', 'kontak',
            'lulusan', 'manager', 'objective', 'operator', 'pendidikan',
            'pengalaman', 'personal', 'phone', 'pribadi', 'profile',
            'profil', 'resume', 'skill', 'staff', 'summary', 'tentang',
            'vitae',
        }
        normalized_words = {
            word.lower().strip(".'-") for word in words
        }

        if candidate.lower() in blocked_phrases:
            return False
        if normalized_words & blocked_words:
            return False

        return True

    def extract_labeled_name(self, lines):
        """Prioritaskan nama dari field eksplisit seperti 'Nama: ...'."""
        label_pattern = re.compile(
            r'^(?:nama(?:\s+lengkap)?|name)\s*[:\-]\s*(.+)$',
            re.IGNORECASE
        )

        for line in lines[:30]:
            match = label_pattern.match(line.strip())
            if not match:
                continue

            candidate = self.normalize_name_candidate(match.group(1))
            if self.is_valid_name_candidate(
                candidate,
                allow_single_word=True,
                require_name_case=False
            ):
                return candidate

        return None

    def extract_split_header_name(self, lines):
        """Gabungkan nama header yang diekstrak menjadi beberapa baris."""
        header_lines = [line.strip() for line in lines[:8] if line.strip()]

        for start_index in range(min(5, len(header_lines))):
            name_parts = []

            for line in header_lines[start_index:start_index + 5]:
                if len(line.split()) != 1:
                    break
                if not self.is_valid_name_candidate(
                    line,
                    allow_single_word=True
                ):
                    break
                name_parts.append(line)

            if len(name_parts) >= 2:
                candidate = self.normalize_name_candidate(
                    ' '.join(name_parts)
                )
                if self.is_valid_name_candidate(candidate):
                    return candidate

        return None
    
    def extract_name_regex(self, text):
        """Extract nama dengan enhanced regex - multiple heuristics"""
        lines = text.split('\n')

        labeled_name = self.extract_labeled_name(lines)
        if labeled_name:
            return labeled_name

        split_header_name = self.extract_split_header_name(lines)
        if split_header_name:
            return split_header_name
        
        # Skip keywords yang umum di CV (bukan nama)
        skip_keywords = [
            'cv', 'curriculum', 'resume', 'contact', 'email', 'phone', 'address',
            'experience', 'education', 'skill', 'objective', 'summary', 'profile',
            'tentang', 'profil', 'kontak', 'alamat', 'pendidikan', 'pengalaman',
            'keahlian', 'portofolio', 'sertifikat', 'about', 'personal', 'data'
        ]
        
        candidates = []
        
        # Cek 15 baris pertama CV
        for i, line in enumerate(lines[:15]):
            line = line.strip()
            
            # Skip baris kosong atau terlalu pendek/panjang
            if len(line) < 5 or len(line) > 50:
                continue
            
            # Skip jika mengandung keyword CV umum
            if any(kw in line.lower() for kw in skip_keywords):
                continue
            
            # Skip jika ada angka banyak (kemungkinan phone/date)
            if re.search(r'\d{3,}', line):
                continue
            
            # Skip jika ada email atau URL
            if re.search(r'@|http|www\.', line):
                continue
            
            # Cek pattern nama Indonesia (2-4 kata)
            words = line.split()
            if 2 <= len(words) <= 4:
                if self.is_valid_name_candidate(line):
                    # Score berdasarkan posisi (lebih atas = lebih prioritas)
                    score = 100 - i  # Baris 1 = score 100, baris 2 = score 99, dst
                    candidates.append((score, line))
        
        # Return kandidat dengan score tertinggi
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            return candidates[0][1]
        
        # Fallback: cek 5 baris pertama saja, ambil yang uppercase/title
        for line in lines[:5]:
            line = line.strip()
            if self.is_valid_name_candidate(line):
                return line
        
        return None
    
    def extract_name(self):
        """Extract nama (Enhanced Regex Only - optimized untuk Vercel)"""
        nama = self.extract_name_regex(self.cv_processed_text)
        
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
        found_skills = []
        
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
                    found_skills.append(skill)
                    break
            
            # Fuzzy match
            if skill not in found_skills:
                if self.fuzzy_match_skill(text, skill, threshold=75):
                    found_skills.append(skill)
        
        self.extracted_info['skills'] = found_skills
        return found_skills

    def get_target_skills(self):
        """Ambil daftar skill pembanding dari request atau judul pekerjaan."""
        required_skills = self.job_data.get('required_skill', [])
        if required_skills:
            return [
                skill.strip()
                for skill in required_skills
                if isinstance(skill, str) and skill.strip()
            ]

        job_title = self.job_data.get('job_title', '').strip().lower()
        title_skills = [
            word for word in job_title.split()
            if len(word) > 2
        ]
        return title_skills or ([job_title] if job_title else [])
    
    def extract_information(self):
        """Extract semua informasi (Nama, Kontak, Skills)"""
        print("\n Extracting information...")
        
        self.extract_name()
        print(f"  Nama: {self.extracted_info['nama']}")
        
        contact = self.extract_contact()
        print(f"  Email: {contact.get('email', 'N/A')}")
        print(f"  Phone: {contact.get('phone', 'N/A')}")
        
        # Gunakan daftar target yang sama untuk ekstraksi dan perhitungan.
        self.target_skills = self.get_target_skills()
        skills = self.extract_skills(self.target_skills)
        
        print(f"  Skills: {', '.join(skills) if skills else 'None'}")
    
    def skill_matching(self):
        """Skill matching"""
        print("\n Skill matching...")
        
        cv_skills = self.extracted_info['skills']
        if not self.target_skills:
            self.target_skills = self.get_target_skills()

        matched_skills = [
            skill for skill in cv_skills
            if skill in self.target_skills
        ]
        total_required = len(self.target_skills)
        
        self.match_result = {
            'match_count': len(matched_skills),
            'matched_skills': matched_skills,
            'total_required': total_required
        }
        
        print(f"  Matched: {len(matched_skills)}/{total_required}")
    
    def calculate_percentage(self):
        """Calculate percentage"""
        if (
            self.match_result['match_count'] > 0
            and self.match_result['total_required'] > 0
        ):
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
                'skill_required': self.target_skills,
                'status': 'RECOMMENDED',
                'persentase': f"{percentage}%"
            })
            print(f"\nStatus: RECOMMENDED ({percentage}%)")
        else:
            response_data.update({
                'skill': [],
                'skill_required': self.target_skills,
                'status': 'NOT_RECOMMENDED',
                'persentase': "0%"
            })
            print(f"\nStatus: NOT RECOMMENDED")
        
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
            return self.download_error or {
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
                    print(f"Temp file deleted: {cv_path}")
            except Exception as e:
                print(f" Failed to delete temp file: {e}")


# ============================================
# API ROUTES
# ============================================

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        'message': 'Hello Sir, CV Matcher API is running',
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
        'name_extractor': 'regex'
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
        "nama": "Ade Rama",
        "kontak": {
            "email": "aderama@example.com",
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

        if not isinstance(data.get('job_title'), str) or not data['job_title'].strip():
            return jsonify({
                'success': False,
                'error': 'job_title must be a non-empty string',
                'error_code': 'INVALID_JOB_TITLE'
            }), 400

        required_skills = data.get('required_skill', [])
        if (
            not isinstance(required_skills, list)
            or any(
                not isinstance(skill, str) or not skill.strip()
                for skill in required_skills
            )
        ):
            return jsonify({
                'success': False,
                'error': 'required_skill must be a list of non-empty strings',
                'error_code': 'INVALID_REQUIRED_SKILL'
            }), 400
        
        # Extract data
        cv_url = data.get('uri_cv')
        job_data = {
            'job_title': data['job_title'].strip(),
            'required_skill': [skill.strip() for skill in required_skills]
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
        print(f"Unexpected error: {e}")
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
