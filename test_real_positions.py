"""
Test script untuk validasi keyword extraction dengan 4 posisi real:
1. PPIC
2. Painting
3. Sablon Manual
4. QC
"""

import sys
sys.path.insert(0, '.')

from app import extract_keywords_from_job_title, COMMON_SYNONYMS

print("=" * 70)
print("TEST: Keyword Extraction untuk 4 Posisi Real")
print("=" * 70)

# Test cases
test_cases = [
    ("PPIC", ["ppic"]),
    ("Painting", ["painting"]),
    ("Sablon Manual", ["sablon", "manual"]),
    ("QC", ["qc"]),
    ("Staff QC", ["qc"]),  # Filter "staff"
    ("Operator Sablon", ["operator", "sablon"]),
    ("Quality Control Inspector", ["quality", "control", "inspector"]),
]

print("\n1. KEYWORD EXTRACTION TEST")
print("-" * 70)

for job_title, expected in test_cases:
    result = extract_keywords_from_job_title(job_title)
    status = "✅" if result == expected else "❌"
    
    print(f"\nJob Title: '{job_title}'")
    print(f"Expected:  {expected}")
    print(f"Got:       {result}")
    print(f"Status:    {status}")

print("\n" + "=" * 70)
print("\n2. SYNONYM EXPANSION TEST")
print("-" * 70)

# Test synonym expansion
test_synonyms = [
    ("ppic", ["ppic", "production planning", "inventory control", "planning control", "production control"]),
    ("painting", ["painting", "cat", "pengecatan", "finishing", "spray painting", "pewarnaan"]),
    ("sablon", ["sablon", "screen printing", "printing", "cetak sablon", "sablon manual", "sablon otomatis"]),
    ("quality control", ["qc", "quality assurance", "qa", "quality inspector", "quality checker", "inspeksi kualitas"]),
]

for skill, expected_synonyms in test_synonyms:
    if skill in COMMON_SYNONYMS:
        synonyms = COMMON_SYNONYMS[skill]
        status = "✅" if set(synonyms) == set(expected_synonyms) else "⚠️"
        
        print(f"\nSkill: '{skill}'")
        print(f"Synonyms: {synonyms}")
        print(f"Status: {status}")
    else:
        print(f"\n❌ Skill '{skill}' NOT FOUND in COMMON_SYNONYMS")

print("\n" + "=" * 70)
print("\n3. MATCHING SIMULATION")
print("-" * 70)

# Simulate CV matching
cv_examples = [
    ("PPIC", "Pengalaman PPIC 3 tahun di PT Manufacturing"),
    ("PPIC", "Production planning and inventory control"),
    ("Painting", "Operator pengecatan sepatu"),
    ("Painting", "Finishing dan cat produk"),
    ("Sablon Manual", "Operator sablon manual 5 tahun"),
    ("Sablon Manual", "Screen printing manual"),
    ("QC", "Quality Control Inspector"),
    ("QC", "Inspeksi kualitas produk"),
]

for job_title, cv_text in cv_examples:
    keywords = extract_keywords_from_job_title(job_title)
    cv_lower = cv_text.lower()
    
    matches = []
    for keyword in keywords:
        # Check direct match
        if keyword in cv_lower:
            matches.append(f"{keyword} (direct)")
        # Check synonyms
        elif keyword in COMMON_SYNONYMS:
            for syn in COMMON_SYNONYMS[keyword]:
                if syn in cv_lower:
                    matches.append(f"{keyword} (via '{syn}')")
                    break
    
    match_pct = (len(matches) / len(keywords) * 100) if keywords else 0
    status = "✅ RECOMMENDED" if len(matches) > 0 else "❌ NOT RECOMMENDED"
    
    print(f"\nJob: '{job_title}' → Keywords: {keywords}")
    print(f"CV: '{cv_text}'")
    print(f"Matches: {matches} ({match_pct:.0f}%)")
    print(f"Result: {status}")

print("\n" + "=" * 70)
print("TEST COMPLETE!")
print("=" * 70)
