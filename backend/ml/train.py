"""
train.py
Entry point for training custom behavioral models.
Run this after collecting sufficient training data.
"""
from data_collector import DataCollector
from model_trainer import train_all_models
import sys

def main():
    # Export features to CSV
    print("=== Exporting Training Data ===")
    collector = DataCollector(data_dir="data/training")
    stats = collector.get_statistics()
    
    print(f"Total training samples: {stats['total_samples']}")
    
    if stats['total_samples'] < 50:
        print("\n⚠️ Warning: You need at least 50 samples for meaningful training.")
        print(f"Currently have: {stats['total_samples']} samples")
        print("Collect more data by having users complete quiz sessions.")
        response = input("\nProceed anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Export to CSV
    num_rows = collector.export_features_csv()
    print(f"\n✅ Exported {num_rows} feature vectors to CSV")
    
    # Train models
    print("\n" + "="*50)
    train_all_models(data_dir="data/training", models_dir="data/models")
    print("="*50)
    
    print("\n🎉 Training pipeline complete!")
    print("\nNext steps:")
    print("1. Restart your FastAPI server to load the trained models")
    print("2. New quiz sessions will use ML predictions instead of rules")
    print("3. Continue collecting data to improve model accuracy")

if __name__ == "__main__":
    main()
