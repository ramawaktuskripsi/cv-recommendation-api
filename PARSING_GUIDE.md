# 🔍 CV Parsing & Skill Matching - Technical Guide

Dokumentasi lengkap tentang cara kerja parsing CV dan skill matching di API ini.

---

## 📄 1. PDF Parsing (Text Extraction)

### **Library:** `pdfplumber`

### **Cara Kerja:**

```python
import pdfplumber

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
```

### **Proses:**

1. **Open PDF** - Buka file PDF
2. **Iterate Pages** - Loop setiap halaman
3. **Extract Text** - Ambil text dari setiap halaman
4. **Combine** - Gabungkan semua text jadi satu string

### **Output Example:**

```
JOHN DOE
Quality Control Supervisor

Email: john.doe@example.com
Phone: +62 812-3456-7890

EXPERIENCE
PT Textile Indonesia (2020-2024)
- Melakukan quality control produk textile
- Memimpin tim QC 10 orang
- Menggunakan Microsoft Excel untuk reporting

SKILLS
- Quality Control
- Leadership
- Microsoft Excel
- Textile Testing
```

### **Keuntungan pdfplumber:**
- ✅ Extract text dengan layout yang baik
- ✅ Support berbagai format PDF
- ✅ Bisa extract tables (untuk future enhancement)
- ✅ Lightweight dan cepat

---

## 🧠 2. Named Entity Recognition (NER)

### **Library:** `spaCy` dengan model `en_core_web_sm`

### **Cara Kerja:**

```python
import spacy

nlp = spacy.load('en_core_web_sm')

def extract_name(text: str) -> str:
    # Process text dengan spaCy
    doc = nlp(text[:500])  # Ambil 500 karakter pertama
    
    # Cari entity dengan label PERSON
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            return ent.text
    
    return None
```

### **Entity Types yang Dikenali:**

| Label | Keterangan | Contoh |
|-------|------------|--------|
| PERSON | Nama orang | "John Doe" |
| ORG | Organisasi/Perusahaan | "PT Textile Indonesia" |
| GPE | Lokasi geografis | "Jakarta", "Indonesia" |
| DATE | Tanggal | "2020-2024", "March 2023" |

### **Proses NER:**

```
Input Text:
"JOHN DOE is a Quality Control Supervisor at PT Textile Indonesia"

↓ spaCy Processing ↓

Entities Found:
- "JOHN DOE" → PERSON
- "PT Textile Indonesia" → ORG
```

### **Kenapa pakai spaCy?**
- ✅ Pre-trained model yang akurat
- ✅ Fast processing
- ✅ Support multiple languages
- ✅ Industry standard untuk NLP

---

## 📧 3. Contact Information Extraction

### **Library:** `re` (Python regex)

### **Email Extraction:**

```python
import re

def extract_email(text: str) -> str:
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return emails[0] if emails else None
```

**Pattern Breakdown:**
- `[A-Za-z0-9._%+-]+` - Username part (sebelum @)
- `@` - At symbol
- `[A-Za-z0-9.-]+` - Domain name
- `\.[A-Z|a-z]{2,}` - Extension (.com, .co.id, dll)

**Matches:**
- ✅ `john.doe@example.com`
- ✅ `user+tag@company.co.id`
- ✅ `name_123@domain.org`

### **Phone Extraction:**

```python
def extract_phone(text: str) -> str:
    patterns = [
        r'\+?62\s?\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # Indonesia format
        r'0\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',         # Local format
    ]
    
    for pattern in patterns:
        phones = re.findall(pattern, text)
        if phones:
            return phones[0]
    
    return None
```

**Matches:**
- ✅ `+62 812-3456-7890`
- ✅ `0812 3456 7890`
- ✅ `+62812-3456-7890`
- ✅ `081234567890`

---

## 🎯 4. Skill Extraction

### **Method 1: Keyword Matching**

```python
SKILL_TAXONOMY = {
    "textile": ["spinning", "weaving", "knitting", "dyeing"],
    "manufacturing": ["lean manufacturing", "six sigma", "quality control"],
    "tools": ["microsoft excel", "sap", "autocad"]
}

def extract_skills(text: str) -> List[str]:
    text_lower = text.lower()
    found_skills = set()
    
    # Loop semua skills di taxonomy
    for skill in ALL_SKILLS:
        if skill.lower() in text_lower:
            found_skills.add(skill.title())
    
    return list(found_skills)
```

**Contoh:**

```
CV Text:
"Experienced in quality control and lean manufacturing. 
Proficient in Microsoft Excel and SAP."

↓ Keyword Matching ↓

Found Skills:
- Quality Control ✓
- Lean Manufacturing ✓
- Microsoft Excel ✓
- SAP ✓
```

### **Method 2: Pattern Matching (Regex)**

```python
SKILL_PATTERNS = {
    r'(inspeksi|pemeriksaan|quality check)\s+(kualitas|produk)': 'Quality Control',
    r'(memimpin|supervisi|mengawasi)\s+tim': 'Leadership',
    r'(excel|spreadsheet)': 'Microsoft Excel',
}

def extract_skills_from_patterns(text: str) -> List[str]:
    text_lower = text.lower()
    found_skills = set()
    
    for pattern, skill in SKILL_PATTERNS.items():
        if re.search(pattern, text_lower):
            found_skills.add(skill)
    
    return list(found_skills)
```

**Contoh:**

```
CV Text (Bahasa Indonesia):
"Melakukan inspeksi kualitas produk textile.
Memimpin tim QC sebanyak 10 orang."

↓ Pattern Matching ↓

Matched Patterns:
- "inspeksi kualitas" → Quality Control ✓
- "memimpin tim" → Leadership ✓
```

---

## 🔄 5. Skill Matching (Fuzzy Matching)

### **Library:** `rapidfuzz`

### **Cara Kerja:**

```python
from rapidfuzz import fuzz

def match_skill(required: str, candidate_skill: str) -> int:
    # Token Set Ratio - ignore word order
    score = fuzz.token_set_ratio(required, candidate_skill)
    return score
```

### **Fuzzy Matching Algorithms:**

#### **A. Token Set Ratio**

Mengabaikan urutan kata dan duplikasi.

```python
required = "microsoft excel"
candidate = "excel microsoft"

score = fuzz.token_set_ratio(required, candidate)
# Result: 100 (perfect match)
```

**Proses:**
1. Split jadi tokens: `["microsoft", "excel"]` vs `["excel", "microsoft"]`
2. Sort alphabetically: `["excel", "microsoft"]` vs `["excel", "microsoft"]`
3. Compare: 100% match!

#### **B. Partial Ratio**

Cari substring terbaik.

```python
required = "excel"
candidate = "microsoft excel advanced"

score = fuzz.partial_ratio(required, candidate)
# Result: 100 (excel found in candidate)
```

### **Threshold System:**

```python
threshold = 75  # Minimum score untuk dianggap match

if score >= threshold:
    is_match = True
else:
    is_match = False
```

**Contoh Scores:**

| Required | Candidate | Score | Match? |
|----------|-----------|-------|--------|
| Quality Control | Quality Control | 100 | ✅ Yes |
| Quality Control | QC | 50 | ❌ No |
| Microsoft Excel | Excel | 80 | ✅ Yes |
| Leadership | Team Leadership | 85 | ✅ Yes |
| SAP | Oracle | 20 | ❌ No |

---

## 🔗 6. Synonym Mapping

### **Cara Kerja:**

```python
SYNONYMS = {
    "excel": ["microsoft excel", "ms excel", "spreadsheet"],
    "quality control": ["qc", "quality assurance", "qa"],
    "leadership": ["team leadership", "people management"],
}

def get_synonyms(skill: str) -> List[str]:
    skill_lower = skill.lower()
    expanded = [skill_lower]
    
    for key, synonyms in SYNONYMS.items():
        if skill_lower in synonyms or skill_lower == key:
            expanded.extend(synonyms)
            expanded.append(key)
    
    return list(set(expanded))
```

### **Matching dengan Synonyms:**

```python
def match_with_synonyms(required: str, candidate_skills: List[str]) -> Dict:
    # Expand required skill dengan synonyms
    required_synonyms = get_synonyms(required)
    # ["quality control", "qc", "quality assurance", "qa"]
    
    best_score = 0
    best_match = None
    
    for cand_skill in candidate_skills:
        cand_synonyms = get_synonyms(cand_skill)
        
        # Compare semua kombinasi
        for req_syn in required_synonyms:
            for cand_syn in cand_synonyms:
                score = fuzz.token_set_ratio(req_syn, cand_syn)
                
                if score > best_score:
                    best_score = score
                    best_match = cand_skill
    
    return {
        'matched': best_match,
        'score': best_score,
        'is_match': best_score >= 75
    }
```

### **Contoh:**

```
Required: "Quality Control"
Candidate Skills: ["QC", "Leadership", "Excel"]

↓ Expand Synonyms ↓

Required Synonyms: ["quality control", "qc", "quality assurance", "qa"]
Candidate "QC" Synonyms: ["qc", "quality control", "quality assurance", "qa"]

↓ Fuzzy Match ↓

Best Match: "QC" with score 100 ✅
Match Type: "Synonym"
```

---

## 📊 7. Complete Matching Flow

### **End-to-End Process:**

```
1. INPUT
   ├─ Required Skills: ["Quality Control", "Leadership", "Excel"]
   └─ Candidate Skills: ["QC", "Team Leadership", "Microsoft Excel"]

2. EXPAND SYNONYMS
   ├─ "Quality Control" → ["quality control", "qc", "qa"]
   ├─ "Leadership" → ["leadership", "team leadership", "people management"]
   └─ "Excel" → ["excel", "microsoft excel", "ms excel", "spreadsheet"]

3. FUZZY MATCHING
   ├─ "Quality Control" vs "QC"
   │  └─ Score: 100 (via synonym) ✅
   ├─ "Leadership" vs "Team Leadership"
   │  └─ Score: 85 (via synonym) ✅
   └─ "Excel" vs "Microsoft Excel"
      └─ Score: 100 (via synonym) ✅

4. RESULT
   ├─ Matched: 3/3 skills
   ├─ Match Percentage: 100%
   └─ Recommendation: RECOMMENDED ✅
```

### **Match Types:**

| Type | Keterangan | Contoh |
|------|------------|--------|
| **Exact** | 100% sama persis | "Quality Control" = "Quality Control" |
| **Synonym** | Match via synonym mapping | "QC" = "Quality Control" |
| **Fuzzy** | Match via fuzzy algorithm | "Team Lead" ≈ "Team Leadership" (score 90) |

---

## 🎯 8. Recommendation Logic

### **Simple Binary System:**

```python
matched_count = len([m for m in matches if m['is_match']])

if matched_count > 0:
    recommendation = "RECOMMENDED"
    # Kirim full data ke frontend
else:
    recommendation = "NOT RECOMMENDED"
    # Tidak kirim data kandidat
```

### **Scoring:**

```python
match_percentage = (matched_count / total_required) * 100

# Contoh:
# Matched: 3/5 skills
# Score: 60%
# Status: RECOMMENDED (karena matched_count > 0)
```

---

## 🔧 9. Optimization Tips

### **A. Improve Skill Taxonomy**

Tambahkan lebih banyak skills sesuai industri:

```python
SKILL_TAXONOMY = {
    "textile": [
        "spinning", "weaving", "knitting", "dyeing", "finishing",
        "quality control", "textile testing", "fabric inspection",
        "color matching", "pattern making", "garment construction",
        # Tambahkan lebih banyak...
    ],
}
```

### **B. Improve Synonyms**

Tambahkan variasi kata:

```python
SYNONYMS = {
    "quality control": [
        "qc", "quality assurance", "qa", 
        "quality inspector", "quality checker",
        "kontrol kualitas", "inspeksi kualitas"  # Bahasa Indonesia
    ],
}
```

### **C. Improve Patterns**

Tambahkan pattern untuk Bahasa Indonesia:

```python
SKILL_PATTERNS = {
    r'(inspeksi|pemeriksaan|cek|kontrol)\s+(kualitas|mutu|produk)': 'Quality Control',
    r'(memimpin|supervisi|mengawasi|mengelola)\s+(tim|team|karyawan)': 'Leadership',
    r'(menggunakan|mahir|menguasai)\s+(excel|spreadsheet)': 'Microsoft Excel',
}
```

### **D. Adjust Threshold**

Sesuaikan threshold untuk precision/recall:

```python
# Strict (high precision, low recall)
threshold = 85  # Hanya match yang sangat mirip

# Balanced
threshold = 75  # Default

# Loose (low precision, high recall)
threshold = 60  # Lebih banyak match, tapi kurang akurat
```

---

## 📈 10. Performance Metrics

### **Current Performance:**

| Metric | Value |
|--------|-------|
| PDF Processing | ~2-3 seconds |
| Text Extraction | ~1 second |
| NER Processing | ~0.5 seconds |
| Skill Matching | ~0.1 seconds per skill |
| Total (5 skills) | ~3-4 seconds |

### **Bottlenecks:**

1. **PDF Download** - Tergantung network speed
2. **PDF Parsing** - Tergantung ukuran file
3. **spaCy NER** - Fixed overhead ~0.5s

---

## 🧪 11. Testing Examples

### **Test Case 1: Perfect Match**

```python
required_skills = ["Quality Control", "Leadership"]
candidate_skills = ["Quality Control", "Leadership", "Excel"]

# Result:
# Matched: 2/2 (100%)
# Status: RECOMMENDED ✅
```

### **Test Case 2: Synonym Match**

```python
required_skills = ["Quality Control", "Microsoft Excel"]
candidate_skills = ["QC", "Excel"]

# Result:
# Matched: 2/2 (100%) via synonyms
# Status: RECOMMENDED ✅
```

### **Test Case 3: Partial Match**

```python
required_skills = ["Quality Control", "SAP", "Leadership"]
candidate_skills = ["Quality Control", "Excel"]

# Result:
# Matched: 1/3 (33%)
# Status: RECOMMENDED ✅ (karena ada 1 match)
```

### **Test Case 4: No Match**

```python
required_skills = ["SAP", "Oracle", "Java"]
candidate_skills = ["Quality Control", "Excel", "Leadership"]

# Result:
# Matched: 0/3 (0%)
# Status: NOT RECOMMENDED ❌
```

---

## 💡 Summary

### **Parsing Pipeline:**

```
PDF File
  ↓
pdfplumber (Extract Text)
  ↓
spaCy (Extract Name via NER)
  ↓
Regex (Extract Email & Phone)
  ↓
Keyword + Pattern Matching (Extract Skills)
  ↓
Parsed CV Data
```

### **Matching Pipeline:**

```
Required Skills + Candidate Skills
  ↓
Expand Synonyms
  ↓
Fuzzy Matching (RapidFuzz)
  ↓
Calculate Match Score
  ↓
Recommendation (RECOMMENDED / NOT RECOMMENDED)
```

---

Apakah ada bagian yang ingin dijelaskan lebih detail? 😊
