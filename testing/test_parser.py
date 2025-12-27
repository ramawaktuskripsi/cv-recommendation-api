# test_parser.py
# Batch testing script untuk CV Parser

import json
import os
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import CVParser, SkillMatcher

class CVParserTester:
    def __init__(self, ground_truth_file: str, cv_directory: str):
        self.ground_truth_file = ground_truth_file
        self.cv_directory = cv_directory
        self.parser = CVParser()
        self.matcher = SkillMatcher(threshold=75)
        
        # Load ground truth
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            self.ground_truth = json.load(f)
        
        self.results = []
        
    def test_single_cv(self, cv_data: Dict) -> Dict:
        """Test single CV and compare with ground truth"""
        filename = cv_data['filename']
        cv_path = os.path.join(self.cv_directory, filename)
        
        print(f"\n📄 Testing: {filename}")
        
        if not os.path.exists(cv_path):
            print(f"  ❌ File not found: {cv_path}")
            return {
                'filename': filename,
                'error': 'File not found',
                'skipped': True
            }
        
        try:
            # Parse CV
            required_skills = self.ground_truth['required_skills']
            parsed = self.parser.parse(cv_path, required_skills)
            
            # Match skills
            match_result = self.matcher.match_all(required_skills, parsed['skills'])
            
            # Determine recommendation
            matched_count = match_result['statistics']['matched_count']
            is_recommended = matched_count > 0
            match_percentage = match_result['statistics']['match_percentage']
            
            # Compare with ground truth
            result = {
                'filename': filename,
                'ground_truth': cv_data,
                'parsed': {
                    'name': parsed['name'],
                    'email': parsed['email'],
                    'phone': parsed['phone'],
                    'skills': parsed['skills']
                },
                'matching': {
                    'is_recommended': is_recommended,
                    'match_percentage': match_percentage,
                    'matched_count': matched_count,
                    'total_required': len(required_skills)
                },
                'evaluation': self._evaluate_result(cv_data, parsed, is_recommended, match_percentage)
            }
            
            # Print summary
            self._print_result_summary(result)
            
            return result
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return {
                'filename': filename,
                'error': str(e),
                'skipped': True
            }
    
    def _evaluate_result(self, gt: Dict, parsed: Dict, is_recommended: bool, match_pct: float) -> Dict:
        """Evaluate parsed result against ground truth"""
        eval_result = {
            'name_correct': self._compare_strings(gt.get('name'), parsed.get('name')),
            'email_correct': self._compare_strings(gt.get('email'), parsed.get('email')),
            'phone_correct': self._compare_strings(gt.get('phone'), parsed.get('phone')),
            'recommendation_correct': gt['expected_recommendation'] == is_recommended,
            'skills_evaluation': self._evaluate_skills(gt['skills'], parsed['skills'])
        }
        
        return eval_result
    
    def _compare_strings(self, gt_value, parsed_value) -> bool:
        """Compare two string values (case-insensitive, None-safe)"""
        if gt_value is None and parsed_value is None:
            return True
        if gt_value is None or parsed_value is None:
            return False
        return str(gt_value).lower().strip() == str(parsed_value).lower().strip()
    
    def _evaluate_skills(self, gt_skills: List[str], parsed_skills: List[str]) -> Dict:
        """Evaluate skill extraction"""
        gt_set = set(s.upper() for s in gt_skills)
        parsed_set = set(s.upper() for s in parsed_skills)
        
        true_positives = gt_set & parsed_set
        false_positives = parsed_set - gt_set
        false_negatives = gt_set - parsed_set
        
        precision = len(true_positives) / len(parsed_set) if parsed_set else 0
        recall = len(true_positives) / len(gt_set) if gt_set else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'true_positives': list(true_positives),
            'false_positives': list(false_positives),
            'false_negatives': list(false_negatives),
            'precision': round(precision, 3),
            'recall': round(recall, 3),
            'f1_score': round(f1, 3)
        }
    
    def _print_result_summary(self, result: Dict):
        """Print summary of test result"""
        if result.get('skipped'):
            return
        
        eval_data = result['evaluation']
        
        print(f"  Name: {'✅' if eval_data['name_correct'] else '❌'}")
        print(f"  Email: {'✅' if eval_data['email_correct'] else '❌'}")
        print(f"  Phone: {'✅' if eval_data['phone_correct'] else '❌'}")
        print(f"  Recommendation: {'✅' if eval_data['recommendation_correct'] else '❌'}")
        print(f"  Skills F1: {eval_data['skills_evaluation']['f1_score']:.1%}")
    
    def run_all_tests(self):
        """Run tests on all CVs in ground truth"""
        print("=" * 60)
        print("🧪 CV PARSER TESTING")
        print("=" * 60)
        print(f"\nGround Truth: {self.ground_truth_file}")
        print(f"CV Directory: {self.cv_directory}")
        print(f"Job Position: {self.ground_truth['job_position']}")
        print(f"Required Skills: {', '.join(self.ground_truth['required_skills'])}")
        print(f"Total CVs: {len(self.ground_truth['cvs'])}")
        print("=" * 60)
        
        # Test each CV
        for cv_data in self.ground_truth['cvs']:
            result = self.test_single_cv(cv_data)
            if not result.get('skipped'):
                self.results.append(result)
        
        # Calculate aggregate metrics
        metrics = self._calculate_aggregate_metrics()
        
        # Print summary
        self._print_summary(metrics)
        
        return {
            'ground_truth': self.ground_truth,
            'results': self.results,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_aggregate_metrics(self) -> Dict:
        """Calculate aggregate metrics across all tests"""
        if not self.results:
            return {}
        
        total = len(self.results)
        
        # Information extraction accuracy
        name_correct = sum(1 for r in self.results if r['evaluation']['name_correct'])
        email_correct = sum(1 for r in self.results if r['evaluation']['email_correct'])
        phone_correct = sum(1 for r in self.results if r['evaluation']['phone_correct'])
        
        # Recommendation accuracy (confusion matrix)
        tp = sum(1 for r in self.results 
                if r['ground_truth']['expected_recommendation'] and r['matching']['is_recommended'])
        tn = sum(1 for r in self.results 
                if not r['ground_truth']['expected_recommendation'] and not r['matching']['is_recommended'])
        fp = sum(1 for r in self.results 
                if not r['ground_truth']['expected_recommendation'] and r['matching']['is_recommended'])
        fn = sum(1 for r in self.results 
                if r['ground_truth']['expected_recommendation'] and not r['matching']['is_recommended'])
        
        # Skills metrics (average)
        avg_precision = sum(r['evaluation']['skills_evaluation']['precision'] for r in self.results) / total
        avg_recall = sum(r['evaluation']['skills_evaluation']['recall'] for r in self.results) / total
        avg_f1 = sum(r['evaluation']['skills_evaluation']['f1_score'] for r in self.results) / total
        
        return {
            'total_cvs': total,
            'information_extraction': {
                'name_accuracy': round(name_correct / total, 3),
                'email_accuracy': round(email_correct / total, 3),
                'phone_accuracy': round(phone_correct / total, 3)
            },
            'recommendation': {
                'confusion_matrix': {
                    'true_positive': tp,
                    'true_negative': tn,
                    'false_positive': fp,
                    'false_negative': fn
                },
                'accuracy': round((tp + tn) / total, 3),
                'precision': round(tp / (tp + fp), 3) if (tp + fp) > 0 else 0,
                'recall': round(tp / (tp + fn), 3) if (tp + fn) > 0 else 0
            },
            'skills': {
                'avg_precision': round(avg_precision, 3),
                'avg_recall': round(avg_recall, 3),
                'avg_f1_score': round(avg_f1, 3)
            }
        }
    
    def _print_summary(self, metrics: Dict):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        print(f"\n📋 Information Extraction:")
        print(f"  Name Accuracy:  {metrics['information_extraction']['name_accuracy']:.1%}")
        print(f"  Email Accuracy: {metrics['information_extraction']['email_accuracy']:.1%}")
        print(f"  Phone Accuracy: {metrics['information_extraction']['phone_accuracy']:.1%}")
        
        print(f"\n🎯 Recommendation Performance:")
        cm = metrics['recommendation']['confusion_matrix']
        print(f"  Accuracy:  {metrics['recommendation']['accuracy']:.1%}")
        print(f"  Precision: {metrics['recommendation']['precision']:.1%}")
        print(f"  Recall:    {metrics['recommendation']['recall']:.1%}")
        print(f"\n  Confusion Matrix:")
        print(f"                    Predicted YES | Predicted NO")
        print(f"    Actual YES         {cm['true_positive']:3d}       |     {cm['false_negative']:3d}")
        print(f"    Actual NO          {cm['false_positive']:3d}       |     {cm['true_negative']:3d}")
        
        print(f"\n🔍 Skills Extraction:")
        print(f"  Avg Precision: {metrics['skills']['avg_precision']:.1%}")
        print(f"  Avg Recall:    {metrics['skills']['avg_recall']:.1%}")
        print(f"  Avg F1-Score:  {metrics['skills']['avg_f1_score']:.1%}")
        
        print("\n" + "=" * 60)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test CV Parser')
    parser.add_argument('--dataset', choices=['dev', 'test'], default='dev',
                       help='Dataset to test (dev or test)')
    args = parser.parse_args()
    
    # Set paths based on dataset
    if args.dataset == 'dev':
        gt_file = 'test_data/ground_truth/development_gt.json'
        cv_dir = 'test_data/development'
        output_file = 'results/development_results.json'
    else:
        gt_file = 'test_data/ground_truth/test_gt.json'
        cv_dir = 'test_data/test'
        output_file = 'results/test_results.json'
    
    # Check if ground truth exists
    if not os.path.exists(gt_file):
        print(f"❌ Ground truth file not found: {gt_file}")
        print(f"Please create ground truth first using: python testing/create_ground_truth.py")
        return
    
    # Run tests
    tester = CVParserTester(gt_file, cv_dir)
    results = tester.run_all_tests()
    
    # Save results
    os.makedirs('results', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")

if __name__ == "__main__":
    main()
