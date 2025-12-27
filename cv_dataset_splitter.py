import os
import shutil
import random
from pathlib import Path
import json
from datetime import datetime

class CVDatasetSplitter:
    def __init__(self, source_folder, output_folder='dataset', train_ratio=0.7, random_seed=42):
        """
        Split CV dataset menjadi training dan testing
        
        Args:
            source_folder: Folder berisi semua CV (100 files)
            output_folder: Folder output untuk dataset
            train_ratio: Rasio data training (default 0.7 = 70%)
            random_seed: Seed untuk reproducibility
        """
        self.source_folder = source_folder
        self.output_folder = output_folder
        self.train_ratio = train_ratio
        self.test_ratio = 1 - train_ratio
        self.random_seed = random_seed
        
        # Set random seed untuk reproducibility
        random.seed(random_seed)
        
        # Folders
        self.train_folder = os.path.join(output_folder, 'train')
        self.test_folder = os.path.join(output_folder, 'test')
        
        self.stats = {
            'total_files': 0,
            'train_count': 0,
            'test_count': 0,
            'train_files': [],
            'test_files': []
        }
    
    def create_folders(self):
        """Buat folder struktur untuk dataset"""
        # Buat folder utama
        os.makedirs(self.train_folder, exist_ok=True)
        os.makedirs(self.test_folder, exist_ok=True)
        
        print(f"✓ Folder struktur dibuat:")
        print(f"  📁 {self.train_folder}")
        print(f"  📁 {self.test_folder}")
    
    def get_all_cv_files(self):
        """Ambil semua file PDF dari source folder"""
        source_path = Path(self.source_folder)
        
        if not source_path.exists():
            print(f"❌ Error: Folder '{self.source_folder}' tidak ditemukan!")
            return []
        
        # Ambil semua file .pdf
        pdf_files = list(source_path.glob('*.pdf'))
        
        if not pdf_files:
            print(f"❌ Error: Tidak ada file PDF di folder '{self.source_folder}'")
            return []
        
        print(f"✓ Ditemukan {len(pdf_files)} file CV")
        return pdf_files
    
    def split_dataset(self, cv_files):
        """
        Split files menjadi train dan test
        
        Args:
            cv_files: List of Path objects
        
        Returns:
            tuple: (train_files, test_files)
        """
        total = len(cv_files)
        train_count = int(total * self.train_ratio)
        
        # Shuffle files secara random
        shuffled_files = cv_files.copy()
        random.shuffle(shuffled_files)
        
        # Split
        train_files = shuffled_files[:train_count]
        test_files = shuffled_files[train_count:]
        
        self.stats['total_files'] = total
        self.stats['train_count'] = len(train_files)
        self.stats['test_count'] = len(test_files)
        
        print(f"\n✓ Dataset split:")
        print(f"  Training: {len(train_files)} files ({len(train_files)/total*100:.1f}%)")
        print(f"  Testing: {len(test_files)} files ({len(test_files)/total*100:.1f}%)")
        
        return train_files, test_files
    
    def copy_files(self, files, destination_folder, dataset_type):
        """
        Copy files ke destination folder
        
        Args:
            files: List of file paths
            destination_folder: Destination folder
            dataset_type: 'train' or 'test'
        """
        print(f"\n🔄 Copying {dataset_type} files...")
        
        copied_files = []
        for idx, file_path in enumerate(files, start=1):
            try:
                # Copy file
                dest_path = os.path.join(destination_folder, file_path.name)
                shutil.copy2(file_path, dest_path)
                
                copied_files.append(file_path.name)
                
                # Progress
                if idx % 10 == 0 or idx == len(files):
                    print(f"  Progress: {idx}/{len(files)} files", end='\r')
            
            except Exception as e:
                print(f"\n  ❌ Error copying {file_path.name}: {e}")
        
        print(f"\n✓ {len(copied_files)} files copied to {dataset_type}")
        return copied_files
    
    def save_split_info(self):
        """Simpan informasi split ke JSON"""
        split_info = {
            'split_date': datetime.now().isoformat(),
            'random_seed': self.random_seed,
            'train_ratio': self.train_ratio,
            'test_ratio': self.test_ratio,
            'statistics': {
                'total_files': self.stats['total_files'],
                'train_count': self.stats['train_count'],
                'test_count': self.stats['test_count']
            },
            'train_files': self.stats['train_files'],
            'test_files': self.stats['test_files']
        }
        
        info_file = os.path.join(self.output_folder, 'split_info.json')
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(split_info, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Split info disimpan: {info_file}")
    
    def process(self):
        """Main process untuk split dataset"""
        print("=" * 70)
        print("🚀 CV DATASET SPLITTER")
        print("=" * 70)
        print(f"Source: {self.source_folder}")
        print(f"Output: {self.output_folder}")
        print(f"Split: {int(self.train_ratio*100)}% train / {int(self.test_ratio*100)}% test")
        print(f"Random seed: {self.random_seed}")
        print("=" * 70)
        
        # Step 1: Create folder structure
        self.create_folders()
        
        # Step 2: Get all CV files
        cv_files = self.get_all_cv_files()
        if not cv_files:
            return
        
        # Step 3: Split dataset
        train_files, test_files = self.split_dataset(cv_files)
        
        # Step 4: Copy files
        self.stats['train_files'] = self.copy_files(train_files, self.train_folder, 'train')
        self.stats['test_files'] = self.copy_files(test_files, self.test_folder, 'test')
        
        # Step 5: Save split info
        self.save_split_info()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary hasil split"""
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        print(f"Total CV: {self.stats['total_files']}")
        print(f"\n📁 Training Set:")
        print(f"   Count: {self.stats['train_count']} files ({self.stats['train_count']/self.stats['total_files']*100:.1f}%)")
        print(f"   Location: {self.train_folder}")
        print(f"\n📁 Testing Set:")
        print(f"   Count: {self.stats['test_count']} files ({self.stats['test_count']/self.stats['total_files']*100:.1f}%)")
        print(f"   Location: {self.test_folder}")
        print("=" * 70)
        print("✅ Dataset split selesai!")


# ============================================
# BATCH PROCESSOR UNTUK TRAIN/TEST
# ============================================

class DatasetProcessor:
    """Process train dan test dataset secara terpisah"""
    
    def __init__(self, dataset_folder, job_data):
        self.dataset_folder = dataset_folder
        self.job_data = job_data
        self.train_folder = os.path.join(dataset_folder, 'train')
        self.test_folder = os.path.join(dataset_folder, 'test')
    
    def process_train(self):
        """Process training dataset"""
        print("\n" + "=" * 70)
        print("🎓 PROCESSING TRAINING DATASET")
        print("=" * 70)
        
        # Import BatchCVProcessor dari file sebelumnya
        # Atau copy class BatchCVProcessor ke sini
        
        from batch_cv_processor import BatchCVProcessor
        
        processor = BatchCVProcessor(self.train_folder, self.job_data)
        results = processor.process_all()
        
        # Save results
        processor.save_results('train_results.json')
        processor.save_recommended_only('train_recommended.json')
        
        return results
    
    def process_test(self):
        """Process testing dataset"""
        print("\n" + "=" * 70)
        print("🧪 PROCESSING TESTING DATASET")
        print("=" * 70)
        
        from batch_cv_processor import BatchCVProcessor
        
        processor = BatchCVProcessor(self.test_folder, self.job_data)
        results = processor.process_all()
        
        # Save results
        processor.save_results('test_results.json')
        processor.save_recommended_only('test_recommended.json')
        
        return results


# ============================================
# MAIN - CONTOH PENGGUNAAN
# ============================================

if __name__ == "__main__":
    
    # ========================================
    # STEP 1: SPLIT DATASET
    # ========================================
    
    print("\n" + "=" * 70)
    print("STEP 1: SPLIT DATASET 70/30")
    print("=" * 70)
    
    # Konfigurasi
    SOURCE_FOLDER = "cv_100"        # Folder berisi 100 CV
    OUTPUT_FOLDER = "dataset"       # Output folder
    TRAIN_RATIO = 0.7              # 70% training, 30% testing
    RANDOM_SEED = 42               # Untuk reproducibility
    
    # Split dataset
    splitter = CVDatasetSplitter(
        source_folder=SOURCE_FOLDER,
        output_folder=OUTPUT_FOLDER,
        train_ratio=TRAIN_RATIO,
        random_seed=RANDOM_SEED
    )
    
    splitter.process()
    
    # ========================================
    # STEP 2: PROCESS TRAIN & TEST (OPTIONAL)
    # ========================================
    
    # Jika ingin langsung process training dan testing:
    
    # job_data = {
    #     'job_title': 'Operator Sablon',
    #     'required_skill': []
    # }
    # 
    # dataset_processor = DatasetProcessor(OUTPUT_FOLDER, job_data)
    # 
    # # Process training
    # train_results = dataset_processor.process_train()
    # 
    # # Process testing
    # test_results = dataset_processor.process_test()
    
    print("\n" + "=" * 70)
    print("✅ SEMUA PROSES SELESAI")
    print("=" * 70)
    print("\nStruktur folder hasil:")
    print("dataset/")
    print("├── train/              (70 CV)")
    print("├── test/               (30 CV)")
    print("└── split_info.json     (Detail split)")