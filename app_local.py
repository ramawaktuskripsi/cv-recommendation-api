import os
import json
import pdfplumber
import re
from rapidfuzz import fuzz

# ============================================
# CV MATCHING SYSTEM CLASS (Local Testing)
# ============================================
class CVMatchingSystem:
    def __init__(self):
        self.cv_raw_text = ""
        self.cv_processed_text = ""
        self.job_data = {}
        self.extracted_info = {'nama': '', 'kontak': {}, 'skills': []}
        self.match_result = {}
        
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
    
    def extract_cv_raw_text(self, cv_path):
        """Extract raw text dari PDF"""
        try:
            with pdfplumber.open(cv_path) as pdf:
                if len(pdf.pages) == 0:
                    print("❌ Error: PDF tidak memiliki halaman")
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
        
        except FileNotFoundError:
            print(f"❌ Error: File tidak ditemukan: {cv_path}")
            return False
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
        """Extract nama dengan enhanced regex"""
        lines = text.split('\n')
        
        # Skip keywords yang umum di CV
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
            
            # Skip jika ada angka banyak
            if re.search(r'\d{3,}', line):
                continue
            
            # Skip jika ada email atau URL
            if re.search(r'@|http|www\.', line):
                continue
            
            # Cek pattern nama (2-4 kata)
            words = line.split()
            if 2 <= len(words) <= 4:
                # Harus title case atau uppercase
                if line.isupper() or line.istitle():
                    # Tidak boleh ada simbol aneh
                    if not re.search(r'[|:;#$%^&*()+=\[\]{}]', line):
                        score = 100 - i
                        candidates.append((score, line))
        
        # Return kandidat dengan score tertinggi
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            return candidates[0][1]
        
        # Fallback
        for line in lines[:5]:
            line = line.strip()
            words = line.split()
            if 2 <= len(words) <= 4:
                if line.isupper() or line.istitle():
                    if not re.search(r'\d{3,}|@', line):
                        return line
        
        return None
    
    def extract_name(self):
        """Extract nama"""
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
            r'\+62[-\s]?\d{2,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',
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
        """Extract semua informasi"""
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
        
        matched_skills = []
        
        if required_skills:
            for skill in cv_skills:
                if skill in required_skills:
                    matched_skills.append(skill)
            total_required = len(required_skills)
        else:
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
    
    def process_from_file(self, cv_path, job_data):
        """
        Main process untuk local testing
        
        Args:
            cv_path: Path lokal ke file PDF
            job_data: Dict dengan job_title dan required_skill
        
        Returns:
            dict: Response data
        """
        print("=" * 70)
        print("🚀 CV MATCHING PROCESS (LOCAL TEST)")
        print("=" * 70)
        print(f"CV File: {cv_path}")
        print(f"Job Title: {job_data.get('job_title')}")
        print(f"Required Skills: {job_data.get('required_skill', [])}")
        print("=" * 70)
        
        self.job_data = job_data
        
        # Step 1: Extract raw text
        if not self.extract_cv_raw_text(cv_path):
            return {
                'success': False,
                'error': 'CV tidak dapat dibaca',
                'error_code': 'UNREADABLE_CV'
            }
        
        # Step 2: Preprocess
        self.preprocess_text()
        
        # Step 3: Extract information
        self.extract_information()
        
        # Step 4: Skill matching
        self.skill_matching()
        
        # Step 5: Prepare response
        response_data = self.prepare_response()
        response_data['success'] = True
        
        print("=" * 70)
        
        return response_data


# ============================================
# MAIN - BATCH EVALUATION 70 CV
# ============================================

import csv
from datetime import datetime

def extract_all_skills_from_cv(cv_text):
    """
    Ekstrak SEMUA skill yang mungkin ada di CV (untuk ground truth otomatis)
    """
    all_possible_skills = [
        # Office
        'excel', 'word', 'powerpoint'
        # Design
        'photoshop', 'illustrator', 'figma', 'canva', 'coreldraw',
        # Soft skills
        'leadership', 'communication', 'teamwork',
        # Industry specific
        'quality control', 'qc', 'qa', 'operator', 'sablon', 'printing',
        'network', 'cisco', 'router', 'mikrotik', 'firewall',
        'accounting', 'marketing', 'sales',
    ]
    
    found = []
    cv_lower = cv_text.lower()
    
    for skill in all_possible_skills:
        if skill in cv_lower:
            found.append(skill)
    
    return found


def batch_process_cv(cv_folder, required_skills, max_cv=70):
    """Process CV dalam folder - HANYA yang bisa dibaca, maksimal max_cv"""
    results = []
    skipped_files = []
    
    if not os.path.exists(cv_folder):
        print(f"❌ Folder '{cv_folder}' tidak ditemukan!")
        return [], []
    
    pdf_files = [f for f in os.listdir(cv_folder) if f.lower().endswith('.pdf')]
    pdf_files.sort()
    
    if not pdf_files:
        print(f"❌ Tidak ada file PDF di folder '{cv_folder}'")
        return [], []
    
    print(f"\n📁 Ditemukan {len(pdf_files)} file PDF")
    print(f"🎯 Target: {max_cv} CV yang bisa dibaca")
    print("=" * 70)
    
    success_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        # Stop jika sudah dapat 70 CV yang valid
        if success_count >= max_cv:
            print(f"\n✅ Sudah mencapai {max_cv} CV yang valid, menghentikan proses...")
            break
        
        cv_path = os.path.join(cv_folder, pdf_file)
        print(f"\n[{i:03d}] Checking: {pdf_file}")
        
        matcher = CVMatchingSystem()
        
        # Cek apakah CV bisa dibaca
        if not matcher.extract_cv_raw_text(cv_path):
            print(f"       ⏭️ SKIP - Format gambar/tidak bisa dibaca")
            skipped_files.append(pdf_file)
            continue
        
        # CV bisa dibaca - proses
        success_count += 1
        print(f"       ✅ Valid [{success_count}/{max_cv}]")
        
        matcher.preprocess_text()
        nama = matcher.extract_name_regex(matcher.cv_processed_text)
        matcher.extract_contact()
        email = matcher.extracted_info['kontak'].get('email')
        phone = matcher.extracted_info['kontak'].get('phone')
        detected_skills = matcher.extract_skills(required_skills)
        all_skills = extract_all_skills_from_cv(matcher.cv_processed_text)
        
        print(f"       Nama: {nama or 'N/A'}")
        print(f"       Detected Skills: {detected_skills}")
        print(f"       All Skills in CV: {all_skills}")
        
        results.append({
            'no': success_count, 'file': pdf_file, 'status': 'OK',
            'nama': nama, 'email': email, 'phone': phone,
            'detected_skills': detected_skills, 'all_skills_in_cv': all_skills,
        })
    
    return results, skipped_files


def calculate_metrics(results, required_skills):
    """Hitung metrik evaluasi"""
    total_tp, total_fp, total_fn, total_tn = 0, 0, 0, 0
    
    for r in results:
        if r['status'] != 'OK':
            continue
        
        detected = set([s.lower() for s in r['detected_skills']])
        ground_truth = set(r['all_skills_in_cv']) & set([s.lower() for s in required_skills])
        all_skills = set([s.lower() for s in required_skills])
        
        tp = len(detected & ground_truth)
        fp = len(detected - ground_truth)
        fn = len(ground_truth - detected)
        tn = len(all_skills - detected - ground_truth)
        
        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn
        
        r['tp'], r['fp'], r['fn'], r['tn'] = tp, fp, fn, tn
    
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (total_tp + total_tn) / (total_tp + total_tn + total_fp + total_fn) if (total_tp + total_tn + total_fp + total_fn) > 0 else 0
    
    return {
        'total_tp': total_tp, 'total_fp': total_fp,
        'total_fn': total_fn, 'total_tn': total_tn,
        'precision': round(precision * 100, 2),
        'recall': round(recall * 100, 2),
        'f1_score': round(f1 * 100, 2),
        'accuracy': round(accuracy * 100, 2),
    }


def save_results(results, metrics, job_data, skipped_files):
    """Simpan hasil ke CSV dan JSON"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    csv_file = f'evaluation_results_{timestamp}.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['JOB TITLE', job_data['job_title']])
        w.writerow(['REQUIRED SKILLS', ', '.join(job_data['required_skill'])])
        w.writerow([])
        w.writerow(['No', 'File', 'Status', 'Nama', 'Email', 'Phone', 
                    'Detected Skills', 'All Skills in CV', 'TP', 'FP', 'FN', 'TN'])
        for r in results:
            w.writerow([
                r['no'], r['file'], r['status'], r['nama'] or '', r['email'] or '', r['phone'] or '',
                ', '.join(r['detected_skills']), ', '.join(r['all_skills_in_cv']),
                r.get('tp', ''), r.get('fp', ''), r.get('fn', ''), r.get('tn', '')
            ])
        w.writerow([])
        w.writerow(['METRICS'])
        w.writerow(['Accuracy', f"{metrics['accuracy']}%"])
        w.writerow(['Precision', f"{metrics['precision']}%"])
        w.writerow(['Recall', f"{metrics['recall']}%"])
        w.writerow(['F1-Score', f"{metrics['f1_score']}%"])
    print(f"\n💾 CSV: {csv_file}")
    
    json_file = f'evaluation_results_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp, 
            'job_data': job_data,
            'total_cv_processed': len(results),
            'total_cv_skipped': len(skipped_files),
            'skipped_files': skipped_files,
            'metrics': metrics, 
            'results': results
        }, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON: {json_file}")


def print_final_report(results, metrics, job_data, skipped_count):
    """Print laporan akhir"""
    
    print("\n" + "=" * 70)
    print("📊 HASIL EVALUASI AKURASI".center(70))
    print("=" * 70)
    print(f"""
JOB DATA:
  Job Title             : {job_data['job_title']}
  Required Skills       : {', '.join(job_data['required_skill'])}

JUMLAH DATA:
  CV Diproses           : {len(results)}
  CV Dilewati (gambar)  : {skipped_count}

CONFUSION MATRIX:
  True Positive  (TP)   : {metrics['total_tp']}
  False Positive (FP)   : {metrics['total_fp']}
  False Negative (FN)   : {metrics['total_fn']}
  True Negative  (TN)   : {metrics['total_tn']}

╔══════════════════════════════════════════╗
║         METRIK EVALUASI                  ║
╠══════════════════════════════════════════╣
║  Accuracy             :  {metrics['accuracy']:>6.2f}%        ║
║  Precision            :  {metrics['precision']:>6.2f}%        ║
║  Recall               :  {metrics['recall']:>6.2f}%        ║
║  F1-Score             :  {metrics['f1_score']:>6.2f}%        ║
╚══════════════════════════════════════════╝
""")


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🔬 EVALUASI AKURASI - BATCH 70 CV".center(70))
    print("=" * 70)
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ========================================
    # KONFIGURASI
    # ========================================
    
    # Folder berisi CV PDF (akan diambil 70 yang bisa dibaca)
    CV_FOLDER = "test_cv"
    MAX_CV = 70  # Maksimal CV yang diproses
    
    # Data lowongan (seperti sebelumnya)
    JOB_DATA = {
        'job_title': 'Operator Sablon',
        'required_skill': ['Menyablon', 'Sablon Manual', 'Operator']
    }
    
    print(f"\nFolder CV: {CV_FOLDER}")
    print(f"Max CV: {MAX_CV}")
    print(f"Job Title: {JOB_DATA['job_title']}")
    print(f"Required Skills: {JOB_DATA['required_skill']}")
    
    # ========================================
    # PROSES BATCH (hanya 70 CV yang valid)
    # ========================================
    
    results, skipped_files = batch_process_cv(CV_FOLDER, JOB_DATA['required_skill'], MAX_CV)
    
    if not results:
        print("\n❌ Tidak ada hasil untuk diproses")
        exit(1)
    
    # ========================================
    # HITUNG METRIK
    # ========================================
    
    metrics = calculate_metrics(results, JOB_DATA['required_skill'])
    
    # ========================================
    # PRINT & SAVE
    # ========================================
    
    print_final_report(results, metrics, JOB_DATA, len(skipped_files))
    save_results(results, metrics, JOB_DATA, skipped_files)
    
    print(f"\n📋 Total CV dilewati (format gambar): {len(skipped_files)}")
    print("\n✅ Evaluasi selesai!")