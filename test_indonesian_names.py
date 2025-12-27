import spacy

# Load English model
nlp = spacy.load('en_core_web_sm')

# Test dengan nama Indonesia
test_texts = [
    "AHMAD RIZKI\nEmail: ahmad@email.com",
    "SITI NURHALIZA\nEmail: siti@email.com",
    "BUDI SANTOSO\nEmail: budi@email.com",
    "JOHN DOE\nEmail: john@email.com",  # English name for comparison
]

print("=" * 60)
print("Testing spaCy NER with Indonesian Names")
print("=" * 60)

for text in test_texts:
    doc = nlp(text[:500])
    
    print(f"\nText: {text.split(chr(10))[0]}")
    print("Entities found:")
    
    found_person = False
    for ent in doc.ents:
        print(f"  - {ent.text} ({ent.label_})")
        if ent.label_ == 'PERSON':
            found_person = True
    
    if not found_person:
        print("  ⚠️  NO PERSON entity found!")
    else:
        print("  ✅ PERSON entity found")

print("\n" + "=" * 60)
