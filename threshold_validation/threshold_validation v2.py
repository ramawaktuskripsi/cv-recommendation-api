from app_local import (
    batch_process_cv,
    calculate_metrics
)
import csv
from datetime import datetime

CV_FOLDER = "test_cv"

THRESHOLDS = [70, 75, 80, 85]

JOBS = [
    {
        'job_title': 'Operator Sablon',
        'required_skill': [
            'Menyablon',
            'Sablon Manual',
            'Operator'
        ]
    },
    {
        'job_title': 'Quality Control',
        'required_skill': [
            'Quality Control',
            'QC',
            'Quality Assurance',
            'Inspection'
        ]
    },
    {
        'job_title': 'PPIC',
        'required_skill': [
            'PPIC',
            'Production Planning',
            'Inventory Control',
            'Production Scheduling',
            'Material Planning'
        ]
    }
]


def run_threshold_validation():

    all_results = []

    print("=" * 80)
    print("THRESHOLD VALIDATION")
    print("=" * 80)

    for job in JOBS:

        print(f"\n\nJOB : {job['job_title']}")
        print("-" * 80)

        best_f1 = -1
        best_threshold = None

        for threshold in THRESHOLDS:

            print(
                f"\nTesting Threshold = {threshold}"
            )

            results, skipped_files, duplicate_files = batch_process_cv(
                CV_FOLDER,
                job,
                max_cv=None,
                fuzzy_threshold=threshold
            )

            metrics = calculate_metrics(
                results,
                job['required_skill']
            )

            row = {
                'job_title': job['job_title'],
                'threshold': threshold,
                'tp': metrics['total_tp'],
                'fp': metrics['total_fp'],
                'fn': metrics['total_fn'],
                'tn': metrics['total_tn'],
                'precision': metrics['precision'],
                'recall': metrics['recall'],
                'f1': metrics['f1_score'],
                'accuracy': metrics['accuracy']
            }

            all_results.append(row)

            print(
                f"Precision={metrics['precision']}% "
                f"Recall={metrics['recall']}% "
                f"F1={metrics['f1_score']}%"
            )

            if metrics['f1_score'] > best_f1:
                best_f1 = metrics['f1_score']
                best_threshold = threshold

        print(
            f"\nBEST THRESHOLD "
            f"{job['job_title']} = "
            f"{best_threshold} "
            f"(F1={best_f1}%)"
        )

    save_threshold_results(all_results)


def save_threshold_results(results):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"threshold_validation_"
        f"{timestamp}.csv"
    )

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "Job Title",
            "Threshold",
            "TP",
            "FP",
            "FN",
            "TN",
            "Precision",
            "Recall",
            "F1",
            "Accuracy"
        ])

        for r in results:

            writer.writerow([
                r['job_title'],
                r['threshold'],
                r['tp'],
                r['fp'],
                r['fn'],
                r['tn'],
                r['precision'],
                r['recall'],
                r['f1'],
                r['accuracy']
            ])

    print(
        f"\nCSV saved: {filename}"
    )


if __name__ == "__main__":
    run_threshold_validation()