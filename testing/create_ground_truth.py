# create_ground_truth.py
# Interactive tool untuk membuat ground truth data

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_cv_files(directory: str) -> List[str]:
    """Get all PDF files from directory"""
    path = Path(directory)
    if not path.exists():
        return []
    return sorted([f.name for f in path.glob('*.pdf')])

def load_existing_ground_truth(filepath: str) -> Dict:
    """Load existing ground truth if exists"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "job_position": "",
        "required_skills": [],
        "cvs": []
    }

def save_ground_truth(data: Dict, filepath: str):
    """Save ground truth to JSON file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Ground truth saved to: {filepath}")

def input_with_default(prompt: str, default: Optional[str] = None) -> str:
    """Get input with optional default value"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()

def input_yes_no(prompt: str, default: bool = False) -> bool:
    """Get yes/no input"""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    if not response:
        return default
    return response in ['y', 'yes', 'ya']

def input_skills() -> List[str]:
    """Input skills as comma-separated list"""
    print("\nMasukkan skills yang ada di CV (pisahkan dengan koma)")
    print("Contoh: SABLON, MENYABLON, QUALITY CONTROL")
    skills_input = input("Skills: ").strip()
    if not skills_input:
        return []
    return [s.strip().upper() for s in skills_input.split(',')]

def create_cv_entry(filename: str, job_position: str, required_skills: List[str]) -> Dict:
    """Create ground truth entry for one CV"""
    clear_screen()
    print("=" * 60)
    print(f"📄 Creating Ground Truth for: {filename}")
    print("=" * 60)
    print(f"\nJob Position: {job_position}")
    print(f"Required Skills: {', '.join(required_skills)}")
    print("\n" + "-" * 60)
    
    # Basic information
    print("\n📋 BASIC INFORMATION")
    name = input_with_default("Nama kandidat", "")
    email = input_with_default("Email", "")
    phone = input_with_default("Phone", "")
    
    # Skills
    print("\n🎯 SKILLS")
    skills = input_skills()
    
    # Calculate expected match
    if skills and required_skills:
        matched = set(skills) & set(required_skills)
        match_pct = (len(matched) / len(required_skills)) * 100
    else:
        match_pct = 0.0
    
    # Recommendation
    print(f"\n📊 EXPECTED RESULTS")
    print(f"Skills found: {', '.join(skills) if skills else 'None'}")
    print(f"Matched skills: {match_pct:.1f}%")
    
    expected_recommendation = input_yes_no(
        "\nApakah CV ini seharusnya RECOMMENDED?",
        default=(match_pct > 0)
    )
    
    # Notes
    notes = input_with_default("\nNotes (optional)", "")
    
    return {
        "filename": filename,
        "name": name if name else None,
        "email": email if email else None,
        "phone": phone if phone else None,
        "skills": skills,
        "expected_recommendation": expected_recommendation,
        "expected_match_percentage": round(match_pct, 1),
        "notes": notes if notes else ""
    }

def main():
    """Main function"""
    clear_screen()
    print("=" * 60)
    print("🏗️  GROUND TRUTH CREATOR")
    print("=" * 60)
    
    # Select dataset type
    print("\nPilih dataset:")
    print("1. Development (70 CV)")
    print("2. Test (30 CV)")
    choice = input("\nPilihan [1/2]: ").strip()
    
    if choice == "1":
        cv_dir = "test_data/development"
        gt_file = "test_data/ground_truth/development_gt.json"
        dataset_name = "Development"
    elif choice == "2":
        cv_dir = "test_data/test"
        gt_file = "test_data/ground_truth/test_gt.json"
        dataset_name = "Test"
    else:
        print("❌ Invalid choice!")
        return
    
    # Get CV files
    cv_files = get_cv_files(cv_dir)
    if not cv_files:
        print(f"\n❌ No PDF files found in {cv_dir}")
        print(f"Please add CV files to {cv_dir} first!")
        return
    
    print(f"\n✅ Found {len(cv_files)} CV files in {cv_dir}")
    
    # Load existing ground truth
    gt_data = load_existing_ground_truth(gt_file)
    existing_files = {cv['filename'] for cv in gt_data.get('cvs', [])}
    
    # Setup job info
    if not gt_data.get('job_position'):
        clear_screen()
        print("=" * 60)
        print("📋 JOB INFORMATION")
        print("=" * 60)
        
        job_position = input("\nJob Position (contoh: OPERATOR SABLON): ").strip().upper()
        
        print("\nRequired Skills (pisahkan dengan koma)")
        print("Contoh: SABLON, MENYABLON")
        skills_input = input("Required Skills: ").strip()
        required_skills = [s.strip().upper() for s in skills_input.split(',')]
        
        gt_data['job_position'] = job_position
        gt_data['required_skills'] = required_skills
        gt_data['cvs'] = []
    
    job_position = gt_data['job_position']
    required_skills = gt_data['required_skills']
    
    # Process each CV
    print(f"\n" + "=" * 60)
    print(f"Processing {dataset_name} Dataset")
    print(f"Job: {job_position}")
    print(f"Required Skills: {', '.join(required_skills)}")
    print("=" * 60)
    
    for idx, cv_file in enumerate(cv_files, 1):
        # Skip if already processed
        if cv_file in existing_files:
            print(f"\n⏭️  Skipping {cv_file} (already processed)")
            continue
        
        print(f"\n📄 Processing {idx}/{len(cv_files)}: {cv_file}")
        
        # Create entry
        cv_entry = create_cv_entry(cv_file, job_position, required_skills)
        gt_data['cvs'].append(cv_entry)
        
        # Save after each entry
        save_ground_truth(gt_data, gt_file)
        
        # Ask to continue
        if idx < len(cv_files):
            if not input_yes_no("\nContinue to next CV?", default=True):
                break
    
    # Final summary
    clear_screen()
    print("=" * 60)
    print("✅ GROUND TRUTH CREATION COMPLETE")
    print("=" * 60)
    print(f"\nDataset: {dataset_name}")
    print(f"Total CVs processed: {len(gt_data['cvs'])}")
    print(f"Saved to: {gt_file}")
    
    # Statistics
    recommended = sum(1 for cv in gt_data['cvs'] if cv['expected_recommendation'])
    not_recommended = len(gt_data['cvs']) - recommended
    
    print(f"\n📊 Statistics:")
    print(f"  - RECOMMENDED: {recommended}")
    print(f"  - NOT RECOMMENDED: {not_recommended}")
    print(f"  - Balance: {recommended/len(gt_data['cvs'])*100:.1f}% recommended")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
