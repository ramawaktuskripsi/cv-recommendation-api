import os
import json
from pathlib import Path
from datetime import datetime
import pdfplumber
import requests
import re
from rapidfuzz import fuzz
import spacy

# ============================================
# CV MATCHING SYSTEM CLASS
# ============================================

class CVMatchingSystem:
    def __init__(self):
        """Inisialisasi CV Matching System"""
        self.cv_raw_text = ""
        self.cv_processed_text = ""
        self.job_data = {}
        self.extracted_info = {
            'nama': '',
            'kontak': {},
            'skills': []
        }
        self.match_result = {}
        
        # Load spaCy model untuk NER
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            print("⚠️  spaCy model belum terinstall. Install dengan: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Synonym mapping untuk skill matching
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
    
    def request_data_from_api(self, api_url):
        """Step 1: Request Data (CV dan Lowongan) dari Website via API"""
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ Error saat request API: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return None
    
    def validate_uri_cv(self, data):
        """Step 2: Cek Kolom uri_cv Ada/Tidak"""
        if not data:
            return False
        
        uri_cv = data.get('uri_cv', '').strip()
        if not uri_cv:
            print("❌ Error: uri_cv kosong")
            return False
        
        return True
    
    def check_required_skills(self, data):
        """Step 3: Cek Required Skills pada Lowongan Ada/Tidak"""
        required_skills = data.get('required_skill', [])
        return len(required_skills) > 0
    
    def extract_job_info(self, data, has_required_skills):
        """Step 4: Ekstrak Job Title (dan Required Skills jika ada)"""
        self.job_data['job_title'] = data.get('job_title', '')
        
        if has_required_skills:
            self.job_data['required_skill'] = data.get('required_skill', [])
        else:
            self.job_data['required_skill'] = []
        
        print(f"✓ Job Title: {self.job_data['job_title']}")
        if has_required_skills:
            print(f"✓ Required Skills: {', '.join(self.job_data['required_skill'])}")
        else:
            print("✓ Required Skills: Tidak ada (akan matching dengan Job Title)")
    
    def extract_cv_raw_text(self, cv_path):
        """
        Step 5: Ekstrak CV (Raw Text) - TANPA preprocessing
        Dengan validasi file corrupt/tidak terbaca
        Hanya support TEXT-BASED PDF (bukan scan/image)
        """
        try:
            with pdfplumber.open(cv_path) as pdf:
                # Validasi 1: Cek jumlah halaman
                if len(pdf.pages) == 0:
                    print(f"❌ Error: PDF tidak memiliki halaman")
                    return False
                
                self.cv_raw_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        self.cv_raw_text += page_text + "\n"
                
                # Validasi 2: Cek minimal karakter yang berhasil diekstrak
                MIN_CHARS = 50  # Minimal 50 karakter untuk CV valid
                
                if len(self.cv_raw_text.strip()) < MIN_CHARS:
                    print(f"❌ Error: CV tidak dapat dibaca")
                    print(f"   Karakter terekstrak: {len(self.cv_raw_text.strip())} (minimal: {MIN_CHARS})")
                    print(f"   Kemungkinan penyebab:")
                    print(f"   • PDF berbasis image/scan (tidak didukung)")
                    print(f"   • File corrupt atau format tidak standar")
                    print(f"   • PDF password-protected")
                    return False
                
                print(f"✓ Berhasil ekstrak CV ({len(self.cv_raw_text)} karakter)")
                return True
        
        except FileNotFoundError:
            print(f"❌ Error: File CV tidak ditemukan: {cv_path}")
            return False
        
        except Exception as e:
            print(f"❌ Error saat ekstrak CV: {e}")
            return False
    
    def preprocess_text(self):
        """
        Step 6: Pre-processing Text
        (Remove whitespace, bullets, normalize)
        """
        text = self.cv_raw_text
        
        # Remove bullets dan karakter khusus dekoratif
        text = re.sub(r'[•○●◦▪▫■□▸▹►▻]', '', text)
        
        # Normalize whitespace (multiple spaces -> single space)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Normalize line breaks (max 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Strip
        self.cv_processed_text = text.strip()
        
        print(f"✓ Pre-processing selesai ({len(self.cv_processed_text)} karakter)")
        return self.cv_processed_text
    
    def extract_name_regex(self, text):
        """Ekstrak nama menggunakan rule-based (heuristic)"""
        lines = text.split('\n')
        for line in lines[:10]:  # Cek 10 baris pertama
            line = line.strip()
            # Nama biasanya 2-4 kata, title case atau uppercase
            if len(line.split()) >= 2 and len(line.split()) <= 4:
                if line.isupper() or line.istitle():
                    # Tidak mengandung angka atau email
                    if not re.search(r'\d{3,}|@', line):
                        return line
        return None
    
    def extract_name_ner(self, text):
        """Ekstrak nama menggunakan NER (spaCy)"""
        if not self.nlp:
            return None
        
        doc = self.nlp(text[:500])  # Proses 500 karakter pertama
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text
        return None
    
    def extract_name(self):
        """Ekstrak nama dengan Regex + NER"""
        # Coba regex dulu
        nama = self.extract_name_regex(self.cv_processed_text)
        
        # Jika gagal, gunakan NER
        if not nama:
            nama = self.extract_name_ner(self.cv_processed_text)
        
        self.extracted_info['nama'] = nama if nama else "Tidak ditemukan"
        return nama
    
    def extract_contact(self):
        """Ekstrak kontak (email dan telepon) menggunakan Regex"""
        text = self.cv_processed_text
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Extract phone (format Indonesia) - dengan berbagai variasi
        phone_patterns = [
            # Format +62-xxx-xxxx-xxxx (dengan tanda hubung)
            r'\+62[-\s]?\d{2,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',  # +62-831-8282-7181
            # Format 62-xxx-xxxx-xxxx (tanpa +)
            r'62[-\s]?\d{2,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',  # 62-831-8282-7181
            # Format 0xxx-xxxx-xxxx atau 0xxx xxxx xxxx
            r'0\d{2,3}[-\s]\d{3,4}[-\s]\d{3,4}',  # 0821-8486-8797 atau 0821 8486 8797
            # Format tanpa pemisah 08xxxxxxxxxx
            r'0\d{9,12}',  # 082112345678
            # Format +62 tanpa pemisah
            r'\+?62\d{9,12}',  # +6282112345678
        ]
        
        phone = None
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                # Pilih yang paling panjang (paling lengkap)
                phone = max(phones, key=len)
                # Clean up: remove newlines dan extra spaces
                phone = re.sub(r'\s+', ' ', phone.replace('\n', ' ')).strip()
                break
        
        self.extracted_info['kontak'] = {
            'email': emails[0] if emails else None,
            'phone': phone
        }
        
        return self.extracted_info['kontak']
    
    def get_skill_variations(self, skill):
        """Dapatkan variasi skill dari synonym mapping"""
        skill_lower = skill.lower()
        variations = [skill_lower]
        
        # Cek di synonym mapping
        for key, synonyms in self.skill_synonyms.items():
            if skill_lower == key or skill_lower in synonyms:
                variations.extend(synonyms)
                variations.append(key)
        
        return list(set(variations))
    
    def fuzzy_match_skill(self, cv_text, skill, threshold=75):
        """
        Fuzzy String Matching untuk skill
        Menggunakan RapidFuzz token_set_ratio
        """
        cv_text_lower = cv_text.lower()
        
        # Get variations
        variations = self.get_skill_variations(skill)
        
        # Cek setiap variation dengan fuzzy matching
        for variation in variations:
            # Token set ratio untuk matching
            score = fuzz.token_set_ratio(variation, cv_text_lower)
            if score >= threshold:
                return True
        
        return False
    
    def extract_skills(self, required_skills_or_job_title):
        """
        Step 7: Ekstrak Skill dari CV
        (Fuzzy String Matching, Synonym Mapping)
        """
        text = self.cv_processed_text
        found_skills = set()
        
        # Jika input adalah list (required skills)
        if isinstance(required_skills_or_job_title, list):
            search_skills = required_skills_or_job_title
        else:
            # Jika string (job title), extract keywords/words dari job title
            job_title = required_skills_or_job_title.lower()
            # Split job title jadi kata-kata individual
            search_skills = [word.strip() for word in job_title.split() if len(word.strip()) > 2]
        
        # Untuk setiap skill yang dicari
        for skill in search_skills:
            # 1. Exact match dengan variations
            variations = self.get_skill_variations(skill)
            text_lower = text.lower()
            
            for variation in variations:
                if variation in text_lower:
                    found_skills.add(skill)
                    break
            
            # 2. Fuzzy matching jika belum ketemu
            if skill not in found_skills:
                if self.fuzzy_match_skill(text, skill, threshold=75):
                    found_skills.add(skill)
        
        self.extracted_info['skills'] = list(found_skills)
        return list(found_skills)
    
    def extract_information_ner(self):
        """
        Step 7: Ekstrak Informasi Nama, Kontak, Skills
        (NER, Regex, Fuzzy String Matching & Synonym Mapping)
        """
        print("\n🔍 Ekstraksi Informasi:")
        
        # Extract nama
        self.extract_name()
        print(f"  ✓ Nama: {self.extracted_info['nama']}")
        
        # Extract kontak
        contact = self.extract_contact()
        print(f"  ✓ Email: {contact.get('email', 'Tidak ditemukan')}")
        print(f"  ✓ Phone: {contact.get('phone', 'Tidak ditemukan')}")
        
        # Extract skills berdasarkan required_skill atau job_title
        if self.job_data.get('required_skill'):
            skills = self.extract_skills(self.job_data['required_skill'])
        else:
            # Jika tidak ada required_skill, gunakan job_title
            skills = self.extract_skills(self.job_data['job_title'])
        
        print(f"  ✓ Skills ditemukan: {', '.join(skills) if skills else 'Tidak ada'}")
    
    def skill_matching(self):
        """Step 8: Skill Matching dengan Job Title ATAU Required Skill"""
        print("\n🎯 Skill Matching:")
        
        cv_skills = self.extracted_info['skills']
        required_skills = self.job_data.get('required_skill', [])
        job_title = self.job_data.get('job_title', '')
        
        matched_skills = []
        match_target = []
        
        # Jika ada required skills, matching dengan required skills
        if required_skills:
            match_target = required_skills
            print(f"  Matching dengan Required Skills: {', '.join(required_skills)}")
        else:
            # Jika tidak ada, matching dengan job title
            match_target = [job_title]
            print(f"  Matching dengan Job Title: {job_title}")
        
        # Hitung matched skills
        for skill in cv_skills:
            if skill in match_target:
                matched_skills.append(skill)
        
        # Jika tidak ada required skills, dan ada match dengan job title
        if not required_skills and cv_skills:
            # Semua skills di CV dianggap match dengan job title
            matched_skills = cv_skills
        
        self.match_result = {
            'match_count': len(matched_skills),
            'matched_skills': matched_skills,
            'total_required': len(match_target) if required_skills else 1
        }
        
        print(f"  ✓ Matched: {len(matched_skills)}/{self.match_result['total_required']}")
        print(f"  ✓ Skills: {', '.join(matched_skills) if matched_skills else 'Tidak ada'}")
    
    def calculate_percentage(self):
        """Step 9: Hitung Persentase Skill Match (jika match_count > 0)"""
        if self.match_result['match_count'] > 0:
            percentage = (self.match_result['match_count'] / 
                         self.match_result['total_required']) * 100
            self.match_result['percentage'] = round(percentage, 2)
            return percentage
        return 0
    
    def prepare_response(self):
        """Step 10: Response Data ke Website via API"""
        response_data = {
            'nama': self.extracted_info['nama'],
            'kontak': self.extracted_info['kontak']
        }
        
        # Jika ada match (match_count > 0)
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
            # Tidak ada match - hanya nama dan kontak
            print(f"\n❌ Status: NOT RECOMMENDED (0 skills match)")
        
        return response_data
    
    def send_response_to_api(self, api_url, response_data):
        """Kirim response ke API"""
        try:
            response = requests.post(api_url, json=response_data, timeout=10)
            response.raise_for_status()
            print(f"✓ Response berhasil dikirim ke API")
            return True
        except Exception as e:
            print(f"❌ Error kirim response: {e}")
            return False
    
    def process(self, api_url=None, cv_path=None, job_data=None):
        """Main process sesuai flowchart lengkap"""
        print("=" * 70)
        print("🚀 CV MATCHING SYSTEM")
        print("=" * 70)
        
        # Step 1 & 2: Request dan validasi data
        if api_url:
            data = self.request_data_from_api(api_url)
            if not self.validate_uri_cv(data):
                return {
                    'success': False,
                    'error': 'uri_cv kosong',
                    'error_code': 'INVALID_URI'
                }
            cv_path = data.get('uri_cv')
            job_data = data
        else:
            if not job_data:
                print("❌ Error: Data lowongan tidak ada")
                return {
                    'success': False,
                    'error': 'Data lowongan kosong',
                    'error_code': 'MISSING_JOB_DATA'
                }
        
        # Step 3 & 4: Check required skills dan extract job info
        has_skills = self.check_required_skills(job_data)
        self.extract_job_info(job_data, has_skills)
        
        # Step 5: Extract CV (Raw Text) - DENGAN VALIDASI
        if not self.extract_cv_raw_text(cv_path):
            return {
                'success': False,
                'error': 'CV tidak dapat dibaca',
                'error_code': 'UNREADABLE_CV',
                'details': 'File PDF tidak dapat diekstrak. Kemungkinan: PDF scan/image (tidak didukung), file corrupt, atau password-protected.',
                'suggestion': 'Silakan upload ulang CV dalam format PDF text-based'
            }
        
        # Step 6: Pre-processing Text
        self.preprocess_text()
        
        # Step 7: Extract informasi (Nama, Kontak, Skills)
        self.extract_information_ner()
        
        # Step 8: Skill matching
        self.skill_matching()
        
        # Step 9 & 10: Prepare response
        response_data = self.prepare_response()
        response_data['success'] = True
        
        print("=" * 70)
        
        return response_data


# ============================================
# BATCH CV PROCESSOR CLASS
# ============================================

class BatchCVProcessor:
    def __init__(self, cv_folder, job_data):
        """
        Inisialisasi Batch CV Processor
        
        Args:
            cv_folder: Path ke folder yang berisi CV-CV (PDF)
            job_data: Data lowongan kerja (job_title, required_skill)
        """
        self.cv_folder = cv_folder
        self.job_data = job_data
        self.results = []
        self.summary = {
            'total_cv': 0,
            'processed': 0,
            'recommended': 0,
            'not_recommended': 0,
            'errors': 0
        }
    
    def get_cv_files(self):
        """Ambil semua file PDF di folder"""
        cv_folder_path = Path(self.cv_folder)
        
        if not cv_folder_path.exists():
            print(f"❌ Error: Folder '{self.cv_folder}' tidak ditemukan!")
            return []
        
        # Ambil semua file .pdf
        pdf_files = list(cv_folder_path.glob('*.pdf'))
        
        if not pdf_files:
            print(f"❌ Error: Tidak ada file PDF di folder '{self.cv_folder}'")
            return []
        
        print(f"📁 Ditemukan {len(pdf_files)} file CV dalam folder")
        return pdf_files
    
    def process_single_cv(self, cv_path, index):
        """Process single CV"""
        print(f"\n{'='*70}")
        print(f"🔄 [{index}] Processing: {cv_path.name}")
        print(f"{'='*70}")
        
        try:
            # Buat instance baru untuk setiap CV
            system = CVMatchingSystem()
            
            # Process CV
            result = system.process(cv_path=str(cv_path), job_data=self.job_data)
            
            # Tambahkan metadata
            result['cv_filename'] = cv_path.name
            result['cv_index'] = index
            
            # Update summary
            if result.get('success'):
                self.summary['processed'] += 1
                
                # Check jika recommended atau tidak
                if result.get('status') == 'RECOMMENDED':
                    self.summary['recommended'] += 1
                    print(f"✅ [{index}] RECOMMENDED - {result.get('nama', 'N/A')}")
                else:
                    self.summary['not_recommended'] += 1
                    print(f"⚠️  [{index}] NOT RECOMMENDED - {result.get('nama', 'N/A')}")
            else:
                self.summary['errors'] += 1
                print(f"❌ [{index}] ERROR - {result.get('error', 'Unknown error')}")
            
            return result
        
        except Exception as e:
            self.summary['errors'] += 1
            error_result = {
                'success': False,
                'cv_filename': cv_path.name,
                'cv_index': index,
                'error': str(e),
                'error_code': 'PROCESSING_ERROR'
            }
            print(f"❌ [{index}] EXCEPTION - {str(e)}")
            return error_result
    
    def process_all(self):
        """Process semua CV di folder"""
        print("=" * 70)
        print("🚀 BATCH CV PROCESSING - START")
        print("=" * 70)
        print(f"📋 Job Title: {self.job_data.get('job_title')}")
        print(f"📋 Required Skills: {', '.join(self.job_data.get('required_skill', [])) if self.job_data.get('required_skill') else 'Tidak ada'}")
        print("=" * 70)
        
        # Get all CV files
        cv_files = self.get_cv_files()
        
        if not cv_files:
            return
        
        self.summary['total_cv'] = len(cv_files)
        
        # Process each CV
        for idx, cv_path in enumerate(cv_files, start=1):
            result = self.process_single_cv(cv_path, idx)
            self.results.append(result)
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print ringkasan hasil processing"""
        print("\n" + "=" * 70)
        print("📊 SUMMARY - BATCH PROCESSING")
        print("=" * 70)
        print(f"Total CV: {self.summary['total_cv']}")
        print(f"Berhasil Diproses: {self.summary['processed']}")
        print(f"Recommended: {self.summary['recommended']} ({self.summary['recommended']/self.summary['total_cv']*100:.1f}%)")
        print(f"Not Recommended: {self.summary['not_recommended']} ({self.summary['not_recommended']/self.summary['total_cv']*100:.1f}%)")
        print(f"Error: {self.summary['errors']}")
        print("=" * 70)
    
    def get_recommended_candidates(self):
        """Get list kandidat yang recommended"""
        recommended = [
            r for r in self.results 
            if r.get('success') and r.get('status') == 'RECOMMENDED'
        ]
        return recommended
    
    def get_not_recommended_candidates(self):
        """Get list kandidat yang not recommended"""
        not_recommended = [
            r for r in self.results 
            if r.get('success') and r.get('status') != 'RECOMMENDED'
        ]
        return not_recommended
    
    def save_results(self, output_file='batch_results.json'):
        """Simpan hasil ke file JSON"""
        output_data = {
            'job_info': self.job_data,
            'processing_date': datetime.now().isoformat(),
            'summary': self.summary,
            'results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Hasil disimpan ke: {output_file}")
    
    def save_recommended_only(self, output_file='recommended_candidates.json'):
        """Simpan hanya kandidat yang recommended"""
        recommended = self.get_recommended_candidates()
        
        output_data = {
            'job_info': self.job_data,
            'processing_date': datetime.now().isoformat(),
            'total_recommended': len(recommended),
            'candidates': recommended
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Kandidat recommended disimpan ke: {output_file}")
    
    def print_recommended_list(self):
        """Print list kandidat yang recommended"""
        recommended = self.get_recommended_candidates()
        
        if not recommended:
            print("\n⚠️  Tidak ada kandidat yang recommended")
            return
        
        print("\n" + "=" * 70)
        print(f"✅ KANDIDAT RECOMMENDED ({len(recommended)} orang)")
        print("=" * 70)
        
        for idx, candidate in enumerate(recommended, start=1):
            print(f"\n{idx}. {candidate.get('nama', 'N/A')}")
            print(f"   File: {candidate.get('cv_filename')}")
            print(f"   Email: {candidate.get('kontak', {}).get('email', 'N/A')}")
            print(f"   Phone: {candidate.get('kontak', {}).get('phone', 'N/A')}")
            print(f"   Skills: {', '.join(candidate.get('skill', []))}")
            print(f"   Match: {candidate.get('persentase', 'N/A')}")
        
        print("=" * 70)


# ============================================
# MAIN - CONTOH PENGGUNAAN
# ============================================

if __name__ == "__main__":
    
    # ========================================
    # KONFIGURASI
    # ========================================
    
    # 1. Folder yang berisi CV-CV (PDF)
    CV_FOLDER = "dataset/train"  # Ganti dengan nama folder Anda
    
    # 2. Data lowongan kerja
    job_data = {
        'job_title': 'Operator Sablon',
        'required_skill': []  # Kosongkan jika hanya match dengan job title
    }
    
    # Atau dengan required skills:
    # job_data = {
    #     'job_title': 'Backend Developer',
    #     'required_skill': ['Python', 'JavaScript', 'SQL', 'Docker']
    # }
    
    # ========================================
    # PROCESSING
    # ========================================
    
    # Buat instance processor
    processor = BatchCVProcessor(CV_FOLDER, job_data)
    
    # Process semua CV
    results = processor.process_all()
    
    # Print list kandidat recommended
    processor.print_recommended_list()
    
    # Simpan hasil
    processor.save_results('batch_results.json')
    processor.save_recommended_only('recommended_candidates.json')
    
    print("\n✅ Batch processing selesai!")