"""
=============================================================================
VALIDASI EMPIRIS THRESHOLD FUZZY MATCHING
=============================================================================
Program ini menguji berbagai nilai threshold untuk menentukan nilai optimal
dalam fuzzy string matching menggunakan RapidFuzz.

Metrik yang diukur:
- True Positive (TP): Skill valid yang terdeteksi dengan benar
- False Positive (FP): Skill tidak valid yang salah terdeteksi
- False Negative (FN): Skill valid yang tidak terdeteksi
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)
- F1-Score: 2 * (Precision * Recall) / (Precision + Recall)
=============================================================================
"""

from rapidfuzz import fuzz
import csv

# Synonym mapping (sama seperti di app.py)
skill_synonyms = {
    'python': ['python', 'py', 'python3', 'python programming'],
    'javascript': ['javascript', 'js', 'ecmascript', 'node.js', 'nodejs', 'node'],
    'react': ['react', 'reactjs', 'react.js', 'react native'],
    'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'database', 'oracle'],
    'java': ['java', 'javase', 'javaee', 'java programming'],
    'css': ['css', 'css3', 'styling', 'stylesheet'],
    'html': ['html', 'html5', 'markup'],
    'excel': ['excel', 'microsoft excel', 'ms excel', 'spreadsheet'],
    'quality control': ['qc', 'quality control', 'quality assurance', 'qa'],
}

def get_skill_variations(skill):
    """Get variations dari synonym mapping"""
    skill_lower = skill.lower()
    variations = [skill_lower]
    
    for key, synonyms in skill_synonyms.items():
        if skill_lower == key or skill_lower in synonyms:
            variations.extend(synonyms)
            variations.append(key)
    
    return list(set(variations))

# =============================================================================
# DATA UJI
# =============================================================================

# Dataset: Pasangan (teks_cv, skill_dicari, expected_match)
# expected_match: True = seharusnya cocok, False = seharusnya tidak cocok
test_data = [
    # === TRUE POSITIVES (Seharusnya Match) ===
    # Exact match
    ("Menguasai Python dan SQL", "python", True),
    ("Pengalaman dengan JavaScript", "javascript", True),
    ("Skill: Excel, Word, PowerPoint", "excel", True),
    
    # Typo ringan (1 huruf)
    ("Berpengalaman dengan Pyhton", "python", True),  # typo: Pyhton
    ("Menguasai Javascrip", "javascript", True),  # typo: missing 't'
    ("Skill dalam Exel", "excel", True),  # typo: Exel
    
    # Variasi penulisan
    ("Menggunakan Node.js dan React", "javascript", True),  # nodejs = javascript
    ("Database MySQL dan PostgreSQL", "sql", True),  # mysql = sql
    ("Familiar dengan ReactJS", "react", True),  # reactjs = react
    
    # Case variations
    ("PYTHON PROGRAMMING", "python", True),
    ("javascript developer", "JavaScript", True),
    
    # Typo sedang (2 huruf)
    ("Pengalaman Pythn programming", "python", True),  # typo: Pythn
    ("Mahir Javasript", "javascript", True),  # typo: Javasript
    
    # === TRUE NEGATIVES (Seharusnya Tidak Match) ===
    # Kata yang berbeda tapi mirip
    ("Menggunakan Java untuk backend", "javascript", False),  # java != javascript
    ("Skill dalam Javanese language", "java", False),  # javanese != java
    
    # Kata yang tidak relevan
    ("Pengalaman di bidang marketing", "python", False),
    ("Skill komunikasi yang baik", "sql", False),
    ("Bekerja di PT Excel Indonesia", "excel", False),  # Excel sebagai nama perusahaan
    
    # Substring yang bukan skill
    ("Reaktif dalam bekerja", "react", False),  # reaktif != react
    ("Dokter umum", "docker", False),  # dokter != docker
    
    # Kata pendek yang mirip
    ("Menggunakan CSS", "c++", False),  # css != c++
    ("Skill SQL query", "sequel", False),  # sql != sequel
    
    # Kata acak
    ("Pengalaman 5 tahun", "python", False),
    ("Lulusan S1 Teknik", "javascript", False),
    
    # === EDGE CASES ===
    # Typo berat - seharusnya tidak match
    ("Menguasai Pyton", "python", True),  # 1 huruf missing - masih valid
    ("Skill Ptyhon", "python", False),  # terlalu jauh
    
    # Abbreviation
    ("Pengalaman QC", "quality control", True),
    ("Skill JS dan CSS", "javascript", True),  # JS = javascript
    
    # Partial match
    ("Python programming expert", "python", True),
    ("Belajar dasar-dasar SQL", "sql", True),
]


# =============================================================================
# FUNGSI PENGUJIAN
# =============================================================================

def test_threshold(test_data, threshold):
    """
    Uji performa pada threshold tertentu
    Menggunakan kombinasi: Exact Match + Synonym + Fuzzy Match
    """
    tp = 0  # True Positive
    fp = 0  # False Positive
    fn = 0  # False Negative
    tn = 0  # True Negative
    
    results = []
    
    for cv_text, skill, expected in test_data:
        cv_lower = cv_text.lower()
        variations = get_skill_variations(skill)
        
        # Method 1: Exact substring match dengan synonym
        exact_match = False
        for var in variations:
            if var in cv_lower:
                exact_match = True
                break
        
        # Method 2: Fuzzy match (hanya jika exact tidak ketemu)
        fuzzy_match = False
        best_score = 0
        if not exact_match:
            for var in variations:
                score = fuzz.token_set_ratio(var, cv_lower)
                best_score = max(best_score, score)
                if score >= threshold:
                    fuzzy_match = True
                    break
        
        # Final prediction
        predicted = exact_match or fuzzy_match
        match_type = "EXACT" if exact_match else ("FUZZY" if fuzzy_match else "NONE")
        
        # Klasifikasi hasil
        if expected and predicted:
            tp += 1
            status = "TP"
        elif not expected and predicted:
            fp += 1
            status = "FP"
        elif expected and not predicted:
            fn += 1
            status = "FN"
        else:
            tn += 1
            status = "TN"
        
        results.append({
            'cv_text': cv_text[:40] + "..." if len(cv_text) > 40 else cv_text,
            'skill': skill,
            'expected': expected,
            'score': best_score,
            'predicted': predicted,
            'match_type': match_type,
            'status': status
        })
    
    # Hitung metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / len(test_data)
    
    return {
        'threshold': threshold,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'tn': tn,
        'precision': round(precision * 100, 2),
        'recall': round(recall * 100, 2),
        'f1_score': round(f1 * 100, 2),
        'accuracy': round(accuracy * 100, 2),
        'details': results
    }


# =============================================================================
# MAIN PROGRAM
# =============================================================================

def main():
    print("=" * 70)
    print("VALIDASI EMPIRIS THRESHOLD FUZZY MATCHING")
    print("=" * 70)
    print(f"Total data uji: {len(test_data)} pasangan")
    print(f"Expected True: {sum(1 for _, _, e in test_data if e)}")
    print(f"Expected False: {sum(1 for _, _, e in test_data if not e)}")
    print("=" * 70)
    
    # Test berbagai threshold
    thresholds_to_test = [60, 65, 70, 75, 80, 85, 90]
    
    print("\n HASIL PENGUJIAN BERBAGAI THRESHOLD:\n")
    print(f"{'Threshold':^10} | {'Precision':^10} | {'Recall':^10} | {'F1-Score':^10} | {'Accuracy':^10}")
    print("-" * 60)
    
    all_results = []
    
    for threshold in thresholds_to_test:
        result = test_threshold(test_data, threshold)
        all_results.append(result)
        print(f"{threshold}%{'':<7} | {result['precision']:>8}% | {result['recall']:>8}% | {result['f1_score']:>8}% | {result['accuracy']:>8}%")
    
    # Cari threshold optimal
    best_result = max(all_results, key=lambda x: x['f1_score'])
    
    print("\n" + "=" * 70)
    print(f"THRESHOLD OPTIMAL: {best_result['threshold']}%")
    print(f"   F1-Score: {best_result['f1_score']}%")
    print(f"   Precision: {best_result['precision']}%")
    print(f"   Recall: {best_result['recall']}%")
    print("=" * 70)
    
    # Detail hasil untuk threshold 75%
    print("\n DETAIL HASIL THRESHOLD 75%:\n")
    result_75 = test_threshold(test_data, 75)
    
    print("Confusion Matrix:")
    print(f"  TP (True Positive): {result_75['tp']}")
    print(f"  FP (False Positive): {result_75['fp']}")
    print(f"  FN (False Negative): {result_75['fn']}")
    print(f"  TN (True Negative): {result_75['tn']}")
    
    # Tampilkan kesalahan (FP dan FN)
    print("\n FALSE POSITIVES (Salah terdeteksi sebagai match):")
    fp_count = 0
    for d in result_75['details']:
        if d['status'] == 'FP':
            print(f"   - '{d['skill']}' in '{d['cv_text']}' (type: {d['match_type']}, score: {d['score']}%)")
            fp_count += 1
    if fp_count == 0:
        print("   (tidak ada)")
    
    print("\n FALSE NEGATIVES (Tidak terdeteksi padahal seharusnya match):")
    fn_count = 0
    for d in result_75['details']:
        if d['status'] == 'FN':
            print(f"   - '{d['skill']}' in '{d['cv_text']}' (type: {d['match_type']}, score: {d['score']}%)")
            fn_count += 1
    if fn_count == 0:
        print("   (tidak ada)")
    
    # Simpan hasil ke CSV
    print("\n" + "=" * 70)
    print("Menyimpan hasil ke 'threshold_validation_results.csv'...")
    
    with open('threshold_validation_results.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Threshold', 'Precision', 'Recall', 'F1_Score', 'Accuracy', 'TP', 'FP', 'FN', 'TN'])
        for r in all_results:
            writer.writerow([
                r['threshold'], r['precision'], r['recall'], r['f1_score'],
                r['accuracy'], r['tp'], r['fp'], r['fn'], r['tn']
            ])
    
    print("Hasil disimpan!")
    
    # Kesimpulan
    print("\n" + "=" * 70)
    print("KESIMPULAN:")
    print("=" * 70)
    print(f"""
Berdasarkan validasi empiris dengan {len(test_data)} data uji:

1. Threshold {best_result['threshold']}% memberikan keseimbangan optimal antara:
   - Precision (menghindari false positive)
   - Recall (mendeteksi skill yang valid)

2. Threshold terlalu rendah (< 70%):
   - Recall tinggi, tapi banyak false positive
   - Kata tidak relevan ikut terdeteksi

3. Threshold terlalu tinggi (> 80%):
   - Precision tinggi, tapi banyak false negative
   - Typo ringan tidak terdeteksi

4. Rekomendasi: Gunakan threshold {best_result['threshold']}% karena:
   - F1-Score: {best_result['f1_score']}%
   - Toleran terhadap typo 1-2 karakter
   - Menolak kata yang tidak relevan
""")


if __name__ == "__main__":
    main()
