# 🧪 CV Parser Testing Tools

Tools untuk testing CV Parser dengan 100 CV lokal (70 development, 30 test).

---

## 📁 Struktur Folder

```
cv-parser-api/
├── app.py                          # CV Parser utama
├── testing/
│   ├── create_ground_truth.py      # Tool buat ground truth
│   ├── test_parser.py              # Testing script
│   └── README.md                   # Dokumentasi ini
├── test_data/
│   ├── development/                # 70 CV untuk tuning
│   │   ├── cv_001.pdf
│   │   ├── cv_002.pdf
│   │   └── ...
│   ├── test/                       # 30 CV untuk final test
│   │   ├── cv_071.pdf
│   │   └── ...
│   └── ground_truth/
│       ├── development_gt.json     # Ground truth development
│       └── test_gt.json            # Ground truth test
└── results/
    ├── development_results.json    # Hasil testing development
    └── test_results.json           # Hasil testing final
```

---

## 🚀 Cara Menggunakan

### **Step 1: Persiapan CV**

1. Kumpulkan 100 CV dalam format PDF
2. Copy 70 CV ke folder `test_data/development/`
3. Copy 30 CV ke folder `test_data/test/`

**Naming convention:**
- `cv_001.pdf`, `cv_002.pdf`, ..., `cv_070.pdf` (development)
- `cv_071.pdf`, `cv_072.pdf`, ..., `cv_100.pdf` (test)

---

### **Step 2: Buat Ground Truth**

Jalankan tool untuk membuat ground truth:

```bash
# Untuk development set (70 CV)
python testing/create_ground_truth.py
# Pilih: 1 (Development)

# Untuk test set (30 CV)
python testing/create_ground_truth.py
# Pilih: 2 (Test)
```

**Proses:**
1. Input job position: `OPERATOR SABLON`
2. Input required skills: `SABLON, MENYABLON`
3. Untuk setiap CV, input:
   - Nama kandidat
   - Email
   - Phone
   - Skills yang ada di CV
   - Expected recommendation (Y/N)
   - Notes (optional)

**Output:**
- `test_data/ground_truth/development_gt.json`
- `test_data/ground_truth/test_gt.json`

---

### **Step 3: Run Testing**

#### **Development Testing (Iterative)**

```bash
# Test pada 70 CV development
python testing/test_parser.py --dataset dev
```

**Output:**
- Console: Metrics summary
- File: `results/development_results.json`

**Analisis hasil:**
1. Lihat metrics (Precision, Recall, F1)
2. Identifikasi error patterns
3. Update `app.py`:
   - Tambah synonym di `COMMON_SYNONYMS`
   - Adjust threshold di `SkillMatcher`
4. Test lagi
5. Ulangi sampai hasil memuaskan

#### **Final Testing (One-time)**

```bash
# Test pada 30 CV test (JANGAN dijalankan sampai development selesai!)
python testing/test_parser.py --dataset test
```

**Output:**
- Console: Final metrics
- File: `results/test_results.json`

---

## 📊 Metrics yang Dihitung

### **1. Information Extraction Accuracy**

```
Name Accuracy  = Correct Names / Total CVs
Email Accuracy = Correct Emails / Total CVs
Phone Accuracy = Correct Phones / Total CVs
```

### **2. Recommendation Performance**

```
Confusion Matrix:
                Predicted YES | Predicted NO
Actual YES         TP         |     FN
Actual NO          FP         |     TN

Accuracy  = (TP + TN) / Total
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
```

### **3. Skills Extraction**

```
Per CV:
  Precision = True Positives / (TP + FP)
  Recall    = True Positives / (TP + FN)
  F1-Score  = 2 * (Precision * Recall) / (Precision + Recall)

Aggregate:
  Avg Precision, Avg Recall, Avg F1-Score
```

---

## 📝 Contoh Ground Truth

```json
{
  "job_position": "OPERATOR SABLON",
  "required_skills": ["SABLON", "MENYABLON"],
  "cvs": [
    {
      "filename": "cv_001.pdf",
      "name": "Budi Santoso",
      "email": "budi@example.com",
      "phone": "+6281234567890",
      "skills": ["SABLON", "MENYABLON", "QUALITY CONTROL"],
      "expected_recommendation": true,
      "expected_match_percentage": 100.0,
      "notes": "Pengalaman sablon 5 tahun"
    }
  ]
}
```

---

## 🔧 Troubleshooting

### **Error: Ground truth file not found**
```bash
# Buat ground truth dulu
python testing/create_ground_truth.py
```

### **Error: No PDF files found**
```bash
# Copy CV files ke folder yang benar
# Development: test_data/development/
# Test: test_data/test/
```

### **Error: Module not found**
```bash
# Pastikan run dari root directory cv-parser-api
cd cv-parser-api
python testing/test_parser.py --dataset dev
```

---

## 💡 Tips

### **Membuat Ground Truth yang Baik:**

1. **Konsisten:** Gunakan UPPERCASE untuk skills
2. **Realistic:** Jangan expect 100% accuracy untuk semua field
3. **Balanced:** Mix 50% RECOMMENDED, 50% NOT RECOMMENDED
4. **Edge Cases:** Include CV dengan typo, variasi penulisan

### **Development Phase:**

1. Start dengan threshold 75%
2. Jika banyak false negative → turunkan threshold
3. Jika banyak false positive → naikkan threshold
4. Tambah synonym untuk skill yang sering muncul tapi tidak terdeteksi

### **Example Synonyms untuk SABLON:**

```python
COMMON_SYNONYMS = {
    # Tambahkan di app.py
    "sablon": ["menyablon", "penyablonan", "operator sablon", "screen printing"],
    # ...
}
```

---

## 📈 Expected Results

Target metrics untuk production:

- **Name Accuracy:** ≥ 85%
- **Email Accuracy:** ≥ 80%
- **Recommendation Accuracy:** ≥ 85%
- **Skills F1-Score:** ≥ 75%

---

## 🎯 Next Steps

Setelah testing selesai:

1. ✅ Review final metrics
2. ✅ Document findings
3. ✅ Update synonym dictionary
4. ✅ Deploy ke production
5. ✅ Monitor real-world performance

---

## 📞 Support

Jika ada masalah:
1. Check error message di console
2. Verify file paths
3. Check ground truth JSON format
4. Review `results/*.json` untuk detail error
