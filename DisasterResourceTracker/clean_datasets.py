
import os
import pandas as pd

# Original dataset location
INPUT_FOLDER = os.path.join(
    "frontend", "public", "dataset"
)

# New folder for cleaned datasets
OUTPUT_FOLDER = "cleaned_data"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("\n========== DATA CLEANING STARTED ==========\n")

for file in os.listdir(INPUT_FOLDER):

    if not file.lower().endswith(".csv"):
        continue

    input_path = os.path.join(INPUT_FOLDER, file)

    try:
        df = pd.read_csv(input_path)

        print("\nProcessing:", file)

        # Clean column names
        df.columns = df.columns.str.strip()

        # Clean text values
        for col in df.select_dtypes(include=["object", "str"]).columns:
            df[col] = df[col].apply(
                lambda x: x.strip() if isinstance(x, str) else x
            )

            df[col] = df[col].replace(
                ["", "None", "nan", "NaN"],
                pd.NA
            )

        # Remove exact duplicate rows
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)

        # Save cleaned dataset
        output_path = os.path.join(
            OUTPUT_FOLDER,
            "cleaned_" + file
        )

        df.to_csv(output_path, index=False)

        print("Original rows:", before)
        print("Duplicates removed:", removed)
        print("Final rows:", len(df))
        print("Missing values:", df.isnull().sum().sum())
        print("Saved to:", output_path)

    except Exception as e:
        print("Error processing", file, ":", e)

print("\n========== DATA CLEANING COMPLETED ==========")
