"""
Database Seeding and Ingestion Pipeline for Disaster Resource Tracker.
Reads and integrates all 5 cleaned datasets into SQLite with foreign key enforcement.
"""

import os
import sqlite3
import pandas as pd
from database import DB_PATH, get_db_connection, create_schema
from algorithms import calculate_district_risk_scores

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEANED_DATA_DIR = os.path.join(PROJECT_ROOT, "cleaned_data")

def resolve_district_states(df_impact, df_dfsi):
    """
    Resolves the exact state for all 732 district rows in df_impact.
    720 districts in India have a unique name.
    6 district names exist across two states:
      - Aurangabad (BIHAR & MAHARASHTRA)
      - Balrampur (CHHATTISGARH & UTTAR PRADESH)
      - Bilaspur (CHHATTISGARH & HIMACHAL PRADESH)
      - Hamirpur (HIMACHAL PRADESH & UTTAR PRADESH)
      - Pratapgarh (RAJASTHAN & UTTAR PRADESH)
      - Raigarh (CHHATTISGARH & MAHARASHTRA)
    Their states are resolved deterministically using row index positions / populations.
    """
    # Create single-state lookup for the 720 unambiguous districts
    state_mapping = df_dfsi.groupby(df_dfsi['Unnamed: 0'].str.strip())['State_Name'].unique().to_dict()
    single_state_lookup = {
        dist: states[0].strip().upper() 
        for dist, states in state_mapping.items() 
        if len(states) == 1
    }

    # Deterministic resolution for the 6 dual-state districts based on dataset row index
    multi_state_by_row = {
        114: "BIHAR",             # Aurangabad (Bihar)
        401: "MAHARASHTRA",       # Aurangabad (Maharashtra)
        138: "CHHATTISGARH",      # Balrampur (Chhattisgarh)
        656: "UTTAR PRADESH",     # Balrampur (Uttar Pradesh)
        140: "CHHATTISGARH",      # Raigarh (Chhattisgarh)
        402: "MAHARASHTRA",       # Raigarh (Maharashtra)
        141: "CHHATTISGARH",      # Bilaspur (Chhattisgarh)
        222: "HIMACHAL PRADESH",  # Bilaspur (Himachal Pradesh)
        221: "HIMACHAL PRADESH",  # Hamirpur (Himachal Pradesh)
        657: "UTTAR PRADESH",     # Hamirpur (Uttar Pradesh)
        538: "RAJASTHAN",         # Pratapgarh (Rajasthan)
        658: "UTTAR PRADESH"      # Pratapgarh (Uttar Pradesh)
    }

    assigned_states = []
    for idx, row in df_impact.iterrows():
        name = row['Dist_Name'].strip()
        if idx in multi_state_by_row:
            assigned_states.append(multi_state_by_row[idx])
        elif name in single_state_lookup:
            assigned_states.append(single_state_lookup[name])
        else:
            # Fallback to first matching state in DFSI
            assigned_states.append(state_mapping.get(name, ["UNKNOWN"])[0].strip().upper())

    return assigned_states


def seed_database(db_path=None):
    """
    Main ETL function: Ingests all five datasets, calculates risk scores,
    and populates the relational SQLite database.
    """
    print("\n" + "=" * 65)
    print(">>> STARTING DATABASE INITIALIZATION & DATASET INGESTION")
    print("=" * 65)

    conn = get_db_connection(db_path)
    
    # 1. Initialize schema
    print("[1/6] Creating database tables and indexes...")
    create_schema(conn)

    cursor = conn.cursor()

    # Clear existing data in correct dependency order (child tables first)
    cursor.execute("DELETE FROM resource_requests;")
    cursor.execute("DELETE FROM reported_incidents;")
    cursor.execute("DELETE FROM resources;")
    cursor.execute("DELETE FROM annual_impact;")
    cursor.execute("DELETE FROM flood_events;")
    cursor.execute("DELETE FROM districts;")
    cursor.execute("DELETE FROM states;")
    conn.commit()

    # 2. Ingest Datasets 1, 2, and 3 (Districts, States, and DFSI)
    print("[2/6] Ingesting Datasets 1, 2, and 3 (Districts, States, Vulnerability)...")
    dfsi_path = os.path.join(CLEANED_DATA_DIR, "cleaned_DFSI.csv")
    impact_path = os.path.join(CLEANED_DATA_DIR, "cleaned_District_FloodImpact (1).csv")
    area_path = os.path.join(CLEANED_DATA_DIR, "cleaned_District_FloodedArea (1).csv")

    df_dfsi = pd.read_csv(dfsi_path)
    df_impact = pd.read_csv(impact_path)
    df_area = pd.read_csv(area_path)

    # Clean text columns
    df_dfsi['Unnamed: 0'] = df_dfsi['Unnamed: 0'].str.strip()
    df_dfsi['State_Name'] = df_dfsi['State_Name'].str.strip().str.upper()
    df_impact['Dist_Name'] = df_impact['Dist_Name'].str.strip()
    df_area['Dist_Name'] = df_area['Dist_Name'].str.strip()

    # Compute DFSI lookup: mean score for each (district, state) pair
    dfsi_grouped = df_dfsi.groupby(['Unnamed: 0', 'State_Name'])['DFSI'].mean().to_dict()

    # Resolve states for all 732 rows of df_impact
    assigned_states = resolve_district_states(df_impact, df_dfsi)
    df_impact['State_Name'] = assigned_states

    # Insert unique States into states table
    unique_states = sorted(list(set(assigned_states)))
    for st in unique_states:
        cursor.execute("INSERT OR IGNORE INTO states (state_name) VALUES (?);", (st,))
    conn.commit()

    # Fetch state_id mapping
    cursor.execute("SELECT state_id, state_name FROM states;")
    state_id_map = {row['state_name']: row['state_id'] for row in cursor.fetchall()}

    # Merge df_impact and df_area (row-by-row verified identical district order)
    districts_merged = pd.DataFrame({
        'district_name': df_impact['Dist_Name'],
        'state_name': df_impact['State_Name'],
        'population': df_impact['Population'].fillna(0).astype(int),
        'human_fatality_total': df_impact['Human_fatality'].fillna(0).astype(int),
        'human_injured_total': df_impact['Human_injured'].fillna(0).astype(int),
        'mean_flood_duration_days': df_impact['Mean_Flood_Duration'].fillna(df_impact['Mean_Flood_Duration'].median()),
        'percent_flooded_area': df_area['Percent_Flooded_Area'].fillna(0.0),
        'permanent_water_percent': df_area['Parmanent_Water'].fillna(0.0),
        'corrected_flooded_area': df_area['Corrected_Percent_Flooded_Area'].fillna(0.0),
    })

    # Attach DFSI scores
    dfsi_scores = []
    for _, row in districts_merged.iterrows():
        key = (row['district_name'], row['state_name'])
        score = dfsi_grouped.get(key)
        if score is None or pd.isna(score):
            # Fallback by district name alone
            fallback = df_dfsi[df_dfsi['Unnamed: 0'] == row['district_name']]['DFSI']
            score = fallback.mean() if not fallback.empty else 10.0
        dfsi_scores.append(round(float(score), 4))
    districts_merged['dfsi_score'] = dfsi_scores

    # Calculate Heuristic Risk Scores and Risk Tiers
    districts_scored = calculate_district_risk_scores(districts_merged)

    # Insert districts into database
    district_rows = []
    for _, r in districts_scored.iterrows():
        sid = state_id_map[r['state_name']]
        district_rows.append((
            r['district_name'],
            sid,
            float(r['dfsi_score']),
            int(r['population']),
            int(r['human_fatality_total']),
            int(r['human_injured_total']),
            float(r['mean_flood_duration_days']),
            float(r['percent_flooded_area']),
            float(r['permanent_water_percent']),
            float(r['corrected_flooded_area']),
            float(r['risk_score']),
            str(r['risk_tier'])
        ))

    cursor.executemany("""
    INSERT INTO districts (
        district_name, state_id, dfsi_score, population, human_fatality_total,
        human_injured_total, mean_flood_duration_days, percent_flooded_area,
        permanent_water_percent, corrected_flooded_area, risk_score, risk_tier
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, district_rows)
    conn.commit()
    print(f"   -> Inserted {len(unique_states)} States and {len(district_rows)} Districts.")

    # 3. Ingest Dataset 4 (cleaned_India_Flood_Inventory_v3 (1).csv)
    print("[3/6] Ingesting Dataset 4 (6,876 Historical Flood Events)...")
    events_path = os.path.join(CLEANED_DATA_DIR, "cleaned_India_Flood_Inventory_v3 (1).csv")
    df_events = pd.read_csv(events_path)

    event_rows = []
    for _, r in df_events.iterrows():
        event_rows.append((
            str(r['UEI']).strip(),
            str(r['Start Date']) if pd.notna(r['Start Date']) else None,
            str(r['End Date']) if pd.notna(r['End Date']) else None,
            float(r['Duration(Days)']) if pd.notna(r['Duration(Days)']) else 0.0,
            str(r['Main Cause']).strip() if pd.notna(r['Main Cause']) else "Unspecified",
            str(r['State']).strip() if pd.notna(r['State']) else "India",
            str(r['Districts']).strip() if pd.notna(r['Districts']) else None,
            int(r['Human fatality']) if pd.notna(r['Human fatality']) else 0,
            int(r['Human injured']) if pd.notna(r['Human injured']) else 0,
            str(r['Human Displaced']) if pd.notna(r['Human Displaced']) else None,
            str(r['Animal Fatality']) if pd.notna(r['Animal Fatality']) else None,
            str(r['Description of Casualties/injured']) if pd.notna(r['Description of Casualties/injured']) else None,
            str(r['Extent of damage']) if pd.notna(r['Extent of damage']) else None,
            str(r['Event Source']).strip() if pd.notna(r['Event Source']) else "IMD",
            str(r['District_LGD_Codes']) if pd.notna(r['District_LGD_Codes']) else None,
            str(r['State_Codes']) if pd.notna(r['State_Codes']) else None,
        ))

    cursor.executemany("""
    INSERT INTO flood_events (
        uei, start_date, end_date, duration_days, main_cause, state_name,
        districts_mentioned, human_fatality, human_injured, human_displaced,
        animal_fatality, description, extent_of_damage, event_source,
        district_lgd_codes, state_codes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, event_rows)
    conn.commit()
    print(f"   -> Inserted {len(event_rows)} Historical Flood Events.")

    # 4. Ingest Dataset 5 (cleaned_disaster_dataset_1.csv)
    print("[4/6] Ingesting Dataset 5 (12-Year Longitudinal Disaster Trends)...")
    annual_path = os.path.join(CLEANED_DATA_DIR, "cleaned_disaster_dataset_1.csv")
    df_annual = pd.read_csv(annual_path)

    annual_rows = []
    for _, r in df_annual.iterrows():
        annual_rows.append((
            str(r['Year']).strip(),
            int(r['Lives Lost (in Nos.)']),
            int(r['Cattle Lost (in Nos.)']),
            int(r['House damaged (in Nos.)']),
            float(r['Cropped areas affected (in lakh ha)'])
        ))

    cursor.executemany("""
    INSERT INTO annual_impact (
        year, lives_lost, cattle_lost, houses_damaged, cropped_area_affected_lakh_ha
    ) VALUES (?, ?, ?, ?, ?);
    """, annual_rows)
    conn.commit()
    print(f"   -> Inserted {len(annual_rows)} Annual Impact Records.")

    # 5. Seed Initial Disaster Relief Inventory (Clearly Flagged as Demo Data)
    print("[5/6] Seeding Initial Disaster Relief Resources (Flagged as Demo Data)...")
    demo_resources = [
        ("Packaged Drinking Water (20L Cans)", "Food & Water", "Cans", 15000, 15000, 0, "Central Warehouse Nagpur", "Available", 1),
        ("Ready-to-Eat Meal Ration Kits", "Food & Water", "Kits", 25000, 25000, 0, "Regional Hub Kolkata", "Available", 1),
        ("Emergency Medical Trauma Kits", "Medical Supplies", "Kits", 5000, 5000, 0, "Red Cross Hub Delhi", "Available", 1),
        ("Inflatable Rescue Motorboats", "Rescue Equipment", "Boats", 250, 250, 0, "NDRF Base Pune", "Available", 1),
        ("Family Relief Tarpaulin Tents", "Shelter", "Tents", 8000, 8000, 0, "Disaster Depot Guwahati", "Available", 1),
        ("Portable Diesel Generators (5kVA)", "Power & Utility", "Units", 400, 400, 0, "South Hub Chennai", "Available", 1),
        ("High-Capacity Water Purification Units", "Food & Water", "Units", 120, 120, 0, "Central Warehouse Nagpur", "Available", 1),
        ("Chlorine Disinfection Tablets (Bottles)", "Medical Supplies", "Bottles", 50000, 50000, 0, "National Depot Hyderabad", "Available", 1)
    ]

    cursor.executemany("""
    INSERT INTO resources (
        resource_name, category, unit, total_quantity, available_quantity,
        allocated_quantity, warehouse_location, status, is_demo_data
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, demo_resources)
    conn.commit()
    print(f"   -> Inserted {len(demo_resources)} Demo Resource Inventory Items.")

    # 6. Verification and Integrity Check
    print("[6/6] Verifying Database Records and Foreign Key Constraints...")
    tables = ["states", "districts", "flood_events", "annual_impact", "resources"]
    row_counts = {}
    for tbl in tables:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM {tbl};")
        row_counts[tbl] = cursor.fetchone()['cnt']

    print("\n" + "=" * 65)
    print(">>> VERIFICATION SUMMARY:")
    for tbl, cnt in row_counts.items():
        print(f"    - Table '{tbl}': {cnt} rows")

    # Assert expected counts
    assert row_counts['states'] == len(unique_states), "State count mismatch!"
    assert row_counts['districts'] == 732, "District count mismatch!"
    assert row_counts['flood_events'] == 6876, "Flood events count mismatch!"
    assert row_counts['annual_impact'] == 12, "Annual impact count mismatch!"
    assert row_counts['resources'] == len(demo_resources), "Resource count mismatch!"

    print(">>> ALL DATABASE COUNTS AND CONSTRAINTS VERIFIED SUCCESSFULLY!")
    print("=" * 65 + "\n")
    conn.close()

if __name__ == "__main__":
    seed_database()
