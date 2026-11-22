
import os
import pandas as pd

# Correct dataset folder location
DATASET_FOLDER = os.path.join(
    "frontend", "public", "dataset"
)

print("\n========== DATASET INSPECTION ==========\n")

if not os.path.exists(DATASET_FOLDER):
    print("Dataset folder not found!")
else:
    for file in os.listdir(DATASET_FOLDER):

        file_path = os.path.join(DATASET_FOLDER, file)

        if file.lower().endswith(".csv"):
            try:
                df = pd.read_csv(file_path)

                print("\n====================================")
                print("FILE NAME:", file)
                print("====================================")

                print("\nRows:", df.shape[0])
                print("Columns:", df.shape[1])

                print("\nColumn Names:")
                print(df.columns.tolist())

                print("\nMissing Values:")
                print(df.isnull().sum())

                print("\nDuplicate Rows:")
                print(df.duplicated().sum())

                print("\nFirst 5 Records:")
                print(df.head())

                print("\nData Types:")
                print(df.dtypes)

            except Exception as e:
                print("Error reading", file, ":", e)

print("\n========== INSPECTION COMPLETED ==========")
