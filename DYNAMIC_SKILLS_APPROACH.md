# 🎯 Dynamic Skills Matching Approach

## Masalah dengan Static Taxonomy

### **Current Approach (Manual):**
```python
# Harus maintain manual di code
SKILL_TAXONOMY = {
    "textile": ["spinning", "weaving", "knitting", ...],  # 100+ skills
    "manufacturing": ["lean", "six sigma", ...],          # 100+ skills
    "tools": ["excel", "sap", "oracle", ...],             # 100+ skills
}

# Setiap ada skill baru, harus update code & redeploy!
```

**Masalah:**
- ❌ Harus update code setiap ada skill baru
- ❌ Redeploy API setiap ada perubahan
- ❌ Tidak scalable
- ❌ Duplikasi data (sudah ada di Prisma)

---

## ✅ Solution: Dynamic Matching

### **Konsep:**

```
Frontend (Prisma DB)          CV Parser API
     │                              │
     │  required_skills dari DB     │
     ├─────────────────────────────>│
     │  ["Quality Control",          │
     │   "Leadership",               │
     │   "SAP"]                      │
     │                              │
     │                         Hanya cari
     │                         3 skills ini
     │                         di CV!
     │                              │
     │<─────────────────────────────┤
     │  Return match results        │
```

### **Keuntungan:**
- ✅ **Zero maintenance** di API
- ✅ **Auto-scale** dengan Prisma
- ✅ **Single source of truth** (Prisma)
- ✅ **Faster processing** (hanya scan required skills)

---

## 🔧 Implementation

### **1. Simplified Skill Extraction**

**OLD (Scan semua skills):**
```python
SKILL_TAXONOMY = {
    "textile": ["spinning", "weaving", ...],  # 500+ skills
    # ...
}

def extract_skills(text: str) -> List[str]:
    # Scan ALL 500+ skills
    for skill in ALL_SKILLS:
        if skill in text:
            found_skills.add(skill)
```

**NEW (Scan hanya required skills):**
```python
def extract_skills_dynamic(text: str, required_skills: List[str]) -> List[str]:
    """
    Hanya cari skills yang ada di required_skills
    """
    text_lower = text.lower()
    found_skills = set()
    
    for skill in required_skills:
        # Simple keyword search
        if skill.lower() in text_lower:
            found_skills.add(skill)
    
    return list(found_skills)
```

### **2. Built-in Synonym Mapping (Minimal)**

Tetap perlu synonym mapping minimal untuk common variations:

```python
# Minimal synonyms untuk common cases
COMMON_SYNONYMS = {
    "excel": ["microsoft excel", "ms excel", "spreadsheet"],
    "word": ["microsoft word", "ms word"],
    "powerpoint": ["microsoft powerpoint", "ms powerpoint", "ppt"],
    "quality control": ["qc", "quality assurance", "qa"],
    "leadership": ["team leadership", "people management", "team lead"],
}

def expand_skill_variations(skill: str) -> List[str]:
    """
    Expand skill dengan common variations
    """
    skill_lower = skill.lower()
    variations = [skill_lower]
    
    # Check common synonyms
    for key, synonyms in COMMON_SYNONYMS.items():
        if skill_lower == key or skill_lower in synonyms:
            variations.extend(synonyms)
            variations.append(key)
    
    return list(set(variations))
```

### **3. Enhanced Matching**

```python
def match_skill_dynamic(required: str, cv_text: str) -> Dict:
    """
    Match single skill dengan variations
    """
    # Get variations
    variations = expand_skill_variations(required)
    
    cv_text_lower = cv_text.lower()
    
    # Check each variation
    for variation in variations:
        if variation in cv_text_lower:
            return {
                'required': required,
                'matched': variation,
                'is_match': True,
                'match_type': 'Exact' if variation == required.lower() else 'Synonym'
            }
    
    # Fuzzy matching as fallback
    best_score = 0
    best_match = None
    
    # Extract potential skills from CV (simple word extraction)
    cv_words = cv_text_lower.split()
    
    for variation in variations:
        for word in cv_words:
            score = fuzz.ratio(variation, word)
            if score > best_score:
                best_score = score
                best_match = word
    
    if best_score >= 75:
        return {
            'required': required,
            'matched': best_match,
            'is_match': True,
            'match_type': 'Fuzzy'
        }
    
    return {
        'required': required,
        'matched': None,
        'is_match': False,
        'match_type': None
    }
```

---

## 📊 Comparison

### **Scenario: New Job Posting**

**Static Taxonomy Approach:**
```
1. HR buat lowongan baru di Prisma
   Required Skills: ["Autocad", "3D Modeling", "Rendering"]

2. ❌ API tidak recognize "3D Modeling" & "Rendering"
   (belum ada di SKILL_TAXONOMY)

3. Developer harus:
   - Update SKILL_TAXONOMY di code
   - Commit & push
   - Redeploy API
   - Wait 5-10 minutes

4. ✅ Baru bisa match skills
```

**Dynamic Approach:**
```
1. HR buat lowongan baru di Prisma
   Required Skills: ["Autocad", "3D Modeling", "Rendering"]

2. Frontend kirim ke API:
   required_skills: ["Autocad", "3D Modeling", "Rendering"]

3. ✅ API langsung bisa match!
   (tidak perlu update code)
```

---

## 🎯 Recommended Architecture

### **Data Flow:**

```
┌─────────────────────────────────────┐
│         Prisma Database             │
│                                     │
│  Job {                              │
│    id: "job-123"                    │
│    title: "QC Supervisor"           │
│    requiredSkills: [                │
│      "Quality Control",             │
│      "Leadership",                  │
│      "SAP"                          │
│    ]                                │
│  }                                  │
└──────────────┬──────────────────────┘
               │
               │ Frontend query
               ▼
┌─────────────────────────────────────┐
│      Frontend API Route             │
│                                     │
│  const job = await prisma.job       │
│    .findUnique({ id: jobId })       │
│                                     │
│  // Send to CV Parser API           │
│  fetch('/api/process-complete', {   │
│    body: {                          │
│      required_skills:               │
│        job.requiredSkills  ◄────────┼─── Single source of truth!
│    }                                │
│  })                                 │
└──────────────┬──────────────────────┘
               │
               │ HTTP Request
               ▼
┌─────────────────────────────────────┐
│       CV Parser API (Anda)          │
│                                     │
│  def process_complete():            │
│    required_skills = request.json   │
│      .get('required_skills')        │
│                                     │
│    # Hanya scan skills ini!         │
│    for skill in required_skills:    │
│      match_skill(skill, cv_text)    │
│                                     │
└─────────────────────────────────────┘
```

---

## 🔧 Hybrid Approach (Alternative)

Jika tetap ingin taxonomy untuk skill discovery:

### **Use Case:**

```python
# Minimal taxonomy untuk DISCOVERY saja
SKILL_CATEGORIES = {
    "technical": ["excel", "sap", "autocad"],
    "soft_skills": ["leadership", "communication"],
}

def extract_all_skills(cv_text: str) -> List[str]:
    """
    Extract SEMUA skills dari CV (untuk display/analytics)
    """
    # Scan dengan taxonomy
    pass

def match_required_skills(cv_text: str, required_skills: List[str]) -> Dict:
    """
    Match HANYA required skills (untuk recommendation)
    """
    # Scan hanya required_skills
    pass
```

### **Workflow:**

```
1. Extract ALL skills dari CV (untuk display di UI)
   → Kandidat punya: ["QC", "Excel", "Leadership", "SAP"]

2. Match dengan required skills (untuk recommendation)
   → Required: ["Quality Control", "Leadership"]
   → Matched: ["QC" (synonym), "Leadership"]
   → Status: RECOMMENDED
```

---

## 💡 Recommendation

### **Best Practice:**

1. **Minimal Common Synonyms** (built-in di API)
   ```python
   COMMON_SYNONYMS = {
       "excel": ["microsoft excel", "ms excel"],
       "qc": ["quality control", "quality assurance"],
       # 20-30 common variations saja
   }
   ```

2. **Dynamic Required Skills** (dari Prisma)
   ```python
   # Frontend kirim exact skills dari database
   required_skills = job.requiredSkills
   ```

3. **Fuzzy Matching** (untuk handle typos & variations)
   ```python
   # RapidFuzz handle sisanya
   score = fuzz.ratio(required, candidate)
   ```

---

## 🎯 Summary

| Aspect | Static Taxonomy | Dynamic Approach |
|--------|----------------|------------------|
| Maintenance | ❌ Manual update code | ✅ Zero maintenance |
| Scalability | ❌ Limited | ✅ Unlimited |
| Deployment | ❌ Redeploy untuk skill baru | ✅ No redeploy needed |
| Source of Truth | ❌ Duplikasi (API + Prisma) | ✅ Single (Prisma) |
| Performance | ❌ Scan 500+ skills | ✅ Scan only required |
| Flexibility | ❌ Developer-dependent | ✅ HR self-service |

**Recommendation:** **Dynamic Approach** dengan minimal common synonyms!

---

Mau saya implement pendekatan dynamic ini ke API Anda? 😊
