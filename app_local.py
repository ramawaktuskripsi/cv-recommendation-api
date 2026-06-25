import os
import json
import pdfplumber
import re
from rapidfuzz import fuzz

# ============================================
# CV MATCHING SYSTEM CLASS (Local Testing)
# ============================================
class CVMatchingSystem:
    def __init__(self, fuzzy_threshold=75):
        self.fuzzy_threshold = fuzzy_threshold
        self.cv_raw_text = ""
        self.cv_processed_text = ""
        self.job_data = {}
        self.extracted_info = {'nama': '', 'kontak': {}, 'skills': []}
        self.match_result = {}
        
        # Synonym mapping
        self.skill_synonyms = {
            'excel': ['excel', 'microsoft excel', 'ms excel', 'spreadsheet'],
            'ppic': ['ppic', 'production planning', 'inventory control', 'planning control', 'production control', 'material planning'],
            'leadership': ['leadership', 'team leadership', 'people management', 'team lead'],
            'quality control': ['qc', 'quality control', 'quality assurance', 'qa', 'quality inspector', 'quality checker'],
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

    @staticmethod
    def normalize_name_candidate(value):
        """Rapikan kandidat nama tanpa mengubah kapitalisasinya."""
        value = value.replace('‘', '').replace('’', '')
        value = value.replace('“', '').replace('”', '')
        value = re.sub(r'[\[\]\(\)\{\}]', '', value)
        value = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', value)
        return re.sub(r'\s+', ' ', value).strip(" \t:-|")

    @staticmethod
    def strip_trailing_contact_fragment(value):
        """Hapus fragmen nomor telepon yang menempel di belakang nama."""
        return re.sub(
            r'\s+(?:\+?62[-\s]?)?0?\d[\d\-\s]{7,}$',
            '',
            value
        ).strip()

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
            'data', 'developer', 'di', 'education', 'email', 'engineer',
            'experience', 'fresh', 'graduate', 'hormat', 'hp', 'jalan',
            'kab', 'kabupaten', 'kec', 'kecamatan', 'keahlian', 'kelurahan',
            'kontak', 'lahir', 'lulusan', 'manager', 'mobile', 'nomor',
            'objective', 'operator', 'phone', 'pimpinan', 'pendidikan',
            'pengalaman', 'personal', 'phone', 'pribadi', 'profile', 'profil',
            'provinsi', 'resume', 'rt', 'rw', 'skill', 'staff', 'summary',
            'telp', 'telepon', 'tanggal', 'tempat', 'tentang', 'vitae', 'wa',
            'whatsapp', 'ds', 'desa', 'dusun', 'blok',
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
            line = self.normalize_name_candidate(line.strip())
            line = self.strip_trailing_contact_fragment(line)
            
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
                if self.is_valid_name_candidate(line):
                    # Score berdasarkan posisi (lebih atas = lebih prioritas)
                    score = 100 - i
                    candidates.append((score, line))
        
        # Return kandidat dengan score tertinggi
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            return self.normalize_name_candidate(candidates[0][1])
        
        # Fallback: cek 5 baris pertama saja, ambil yang uppercase/title
        for line in lines[:5]:
            line = self.strip_trailing_contact_fragment(
                self.normalize_name_candidate(line.strip())
            )
            if self.is_valid_name_candidate(
                line,
                allow_single_word=True,
                require_name_case=False
            ):
                return self.normalize_name_candidate(line)
        
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
    
    def fuzzy_match_skill(self, cv_text, skill):
        """Fuzzy matching dengan RapidFuzz"""
        cv_text_lower = cv_text.lower()
        variations = self.get_skill_variations(skill)
        
        for variation in variations:
            score = fuzz.token_set_ratio(variation, cv_text_lower)
            if score >= self.fuzzy_threshold:
                    print(
                    f"[FUZZY MATCH] "
                    f"Skill='{skill}' | "
                    f"Variation='{variation}' | "
                    f"Score={score}"
                    )
                    # tampilkan potongan CV
                    print(
                        f"CV Contains? "
                        f"{variation.lower() in cv_text_lower}"
                    )
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
                if self.fuzzy_match_skill(text, skill):
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

        skill_required = self.job_data.get(
            'required_skill', [self.job_data.get('job_title')]
        )
        
        # Jika match > 0
        if self.match_result['match_count'] > 0:
            percentage = self.calculate_percentage()
            response_data.update({
                'skill': self.extracted_info['skills'],
                'skill_required': skill_required,
                'status': 'RECOMMENDED',
                'persentase': f"{percentage}%"
            })
            print(f"\n✅ Status: RECOMMENDED ({percentage}%)")
        else:
            response_data.update({
                'skill': [],
                'skill_required': skill_required,
                'status': 'NOT_RECOMMENDED',
                'persentase': "0%"
            })
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
        'excel', 'word', 'powerpoint',
        # PPIC
        'ppic', 'production planning', 'inventory control', 'planning control', 'production control', 'material planning',
        # Design
        'photoshop', 'illustrator', 'figma', 'canva', 'coreldraw',
        # Soft skills
        'leadership', 'communication', 'teamwork',
        # Industry specific
        'quality control', 'qc', 'qa', 'quality assurance', 'quality inspector', 'quality checker',
        'operator', 'sablon', 'printing'
    ]
    
    found = []
    cv_lower = cv_text.lower()
    
    for skill in all_possible_skills:
        if skill in cv_lower:
            found.append(skill)
    
    return found


def batch_process_cv(cv_folder, job_data, max_cv=None, fuzzy_threshold=75):
    """Process semua CV dalam folder; jika max_cv diisi, batasi jumlah CV unik yang diproses."""
    results = []
    skipped_files = []
    duplicate_files = []
    required_skills = job_data.get('required_skill', [])
    seen_name_files = {}
    
    if not os.path.exists(cv_folder):
        print(f"❌ Folder '{cv_folder}' tidak ditemukan!")
        return [], []
    
    pdf_files = [f for f in os.listdir(cv_folder) if f.lower().endswith('.pdf')]
    pdf_files.sort()
    
    if not pdf_files:
        print(f"❌ Tidak ada file PDF di folder '{cv_folder}'")
        return [], []
    
    print(f"\n📁 Ditemukan {len(pdf_files)} file PDF")
    target_text = "semua" if max_cv is None else str(max_cv)
    print(f"🎯 Target: {target_text} CV yang bisa dibaca")
    print("=" * 70)
    
    readable_count = 0
    processed_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        # Stop jika mencapai batas CV unik, bila batasnya diaktifkan
        if max_cv is not None and processed_count >= max_cv:
            print(f"\n✅ Sudah mencapai {max_cv} CV yang valid, menghentikan proses...")
            break
        
        cv_path = os.path.join(cv_folder, pdf_file)
        print(f"\n[{i:03d}] Checking: {pdf_file}")
        
        matcher = CVMatchingSystem(
            fuzzy_threshold=fuzzy_threshold
            )
        matcher.job_data = job_data
        
        # Cek apakah CV bisa dibaca
        if not matcher.extract_cv_raw_text(cv_path):
            print(f"       ⏭️ SKIP - Format gambar/tidak bisa dibaca")
            skipped_files.append(pdf_file)
            continue
        
        # CV bisa dibaca - proses
        readable_count += 1
        readable_suffix = f"/{max_cv}" if max_cv is not None else ""
        print(f"       ✅ Valid [{readable_count}{readable_suffix}]")
        
        matcher.preprocess_text()
        nama = matcher.extract_name_regex(matcher.cv_processed_text)

        name_key = (
            matcher.normalize_name_candidate(nama).casefold()
            if nama else ''
        )
        if name_key and name_key in seen_name_files:
            duplicate_files.append({
                'file': pdf_file,
                'nama': nama,
                'duplicate_of': seen_name_files[name_key],
            })
            print(
                f"       ⏭️ SKIP - Duplicate name: {nama} "
                f"(same as {seen_name_files[name_key]})"
            )
            continue
        if name_key:
            seen_name_files[name_key] = pdf_file

        processed_count += 1
        matcher.extract_contact()
        email = matcher.extracted_info['kontak'].get('email')
        phone = matcher.extracted_info['kontak'].get('phone')
        detected_skills = matcher.extract_skills(required_skills)
        all_skills = extract_all_skills_from_cv(matcher.cv_processed_text)
        matcher.skill_matching()
        response_data = matcher.prepare_response()
        recommendation = response_data.get('status', 'NOT_RECOMMENDED')
        percentage = response_data.get('persentase', '0%')
        
        print(f"       Nama: {nama or 'N/A'}")
        print(f"       Detected Skills: {detected_skills}")
        print(f"       All Skills in CV: {all_skills}")
        print(f"       Recommendation: {recommendation} ({percentage})")
        
        results.append({
            'no': processed_count, 'file': pdf_file, 'status': 'OK',
            'nama': nama, 'email': email, 'phone': phone,
            'detected_skills': detected_skills, 'all_skills_in_cv': all_skills,
            'recommendation': recommendation, 'persentase': percentage,
        })
    
    return results, skipped_files, duplicate_files


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


def save_results(results, metrics, job_data, skipped_files, duplicate_files):
    """Simpan hasil ke CSV dan JSON"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    recommended_count = sum(
        1 for result in results
        if result.get('recommendation') == 'RECOMMENDED'
    )
    not_recommended_count = len(results) - recommended_count
    duplicate_count = len(duplicate_files)
    
    csv_file = f'evaluation_results_{timestamp}.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['JOB TITLE', job_data['job_title']])
        w.writerow(['REQUIRED SKILLS', ', '.join(job_data['required_skill'])])
        w.writerow([])
        w.writerow(['No', 'File', 'Status', 'Nama', 'Email', 'Phone',
                    'Recommendation', 'Persentase', 'Detected Skills',
                    'All Skills in CV', 'TP', 'FP', 'FN', 'TN'])
        for r in results:
            w.writerow([
                r['no'], r['file'], r['status'], r['nama'] or '', r['email'] or '', r['phone'] or '',
                r.get('recommendation', ''), r.get('persentase', ''),
                ', '.join(r['detected_skills']), ', '.join(r['all_skills_in_cv']),
                r.get('tp', ''), r.get('fp', ''), r.get('fn', ''), r.get('tn', '')
            ])
        w.writerow([])
        w.writerow(['SUMMARY'])
        w.writerow(['Total CV Files', len(results) + len(skipped_files) + duplicate_count])
        w.writerow(['Readable CV', len(results) + duplicate_count])
        w.writerow(['Unique Processed CV', len(results)])
        w.writerow(['Duplicate Skipped', duplicate_count])
        w.writerow(['Invalid / Skipped CV', len(skipped_files)])
        w.writerow(['Recommended', recommended_count])
        w.writerow(['Not Recommended', not_recommended_count])
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
            'total_cv_files': len(results) + len(skipped_files) + duplicate_count,
            'total_readable_cv': len(results) + duplicate_count,
            'total_duplicate_skipped': duplicate_count,
            'total_recommended': recommended_count,
            'total_not_recommended': not_recommended_count,
            'skipped_files': skipped_files,
            'duplicate_files': duplicate_files,
            'metrics': metrics, 
            'results': results
        }, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON: {json_file}")


def print_final_report(results, metrics, job_data, skipped_count, duplicate_files):
    """Print laporan akhir"""
    recommended_count = sum(
        1 for result in results
        if result.get('recommendation') == 'RECOMMENDED'
    )
    not_recommended_count = len(results) - recommended_count
    duplicate_count = len(duplicate_files)
    total_files = len(results) + skipped_count + duplicate_count
    readable_count = len(results) + duplicate_count
    
    print("\n" + "=" * 70)
    print("📊 HASIL EVALUASI AKURASI".center(70))
    print("=" * 70)
    print(f"""
JOB DATA:
  Job Title             : {job_data['job_title']}
  Required Skills       : {', '.join(job_data['required_skill'])}

JUMLAH DATA:
    Total CV File         : {total_files}
    Readable CV           : {readable_count}
    Unique Processed CV   : {len(results)}
    Duplicate Skipped     : {duplicate_count}
    Invalid / Skipped CV  : {skipped_count}
    Recommended           : {recommended_count}
    Not Recommended       : {not_recommended_count}

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

    if duplicate_files:
        print("\nDUPLICATE SKIPPED:")
        for duplicate in duplicate_files:
            print(
                f"  - {duplicate['nama']} | {duplicate['file']} "
                f"(same as {duplicate['duplicate_of']})"
            )


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🔬 EVALUASI AKURASI - SEMUA CV".center(70))
    print("=" * 70)
    print(f"Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ========================================
    # KONFIGURASI
    # ========================================
    
    # Folder berisi CV PDF (semua file yang bisa dibaca akan diproses)
    CV_FOLDER = "test_cv"
    MAX_CV = None  # None = proses semua CV valid yang ditemukan
    
    # Data lowongan (seperti sebelumnya)
    JOB_DATA = {
        'job_title': 'QC',
        'required_skill': ['QC', 'Quality Control']
    }
    
    print(f"\nFolder CV: {CV_FOLDER}")
    print(f"Max CV: {MAX_CV}")
    print(f"Job Title: {JOB_DATA['job_title']}")
    print(f"Required Skills: {JOB_DATA['required_skill']}")
    
    # ========================================
    # PROSES BATCH (hanya 70 CV yang valid)
    # ========================================
    
    results, skipped_files, duplicate_files = batch_process_cv(
        CV_FOLDER,
        JOB_DATA,
        MAX_CV
    )
    
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
    
    print_final_report(
        results,
        metrics,
        JOB_DATA,
        len(skipped_files),
        duplicate_files
    )
    save_results(results, metrics, JOB_DATA, skipped_files, duplicate_files)
    
    print(f"\n📋 Total CV dilewati (format gambar): {len(skipped_files)}")
    print("\n✅ Evaluasi selesai!")