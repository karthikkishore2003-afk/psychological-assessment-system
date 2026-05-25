import streamlit as st
import pandas as pd
import sqlite3

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="Psychological Assessment System",
    layout="wide"
)

# ---------------- DATABASE ----------------

DB_PATH = "master_database.db"

conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)

conn.execute("""
CREATE TABLE IF NOT EXISTS assessments (

    Name TEXT,
    Gender TEXT,

    TAS_Score INTEGER,
    TAS_Interpretation TEXT,

    BEIS_Score INTEGER,
    BEIS_Interpretation TEXT,

    DASS_Score INTEGER,
    DASS_Interpretation TEXT
)
""")

conn.commit()

# ---------------- TITLE ----------------

st.title("🧠 Psychological Assessment Management System")

st.markdown("""
Upload raw questionnaire Excel files.
The system automatically:
- Calculates TAS-20
- Applies reverse scoring
- Calculates BEIS-10
- Calculates DASS Anxiety
- Generates interpretations
- Appends new participants
""")

# ---------------- FILE UPLOAD ----------------

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

# ---------------- LIKERT MAP ----------------

likert_map = {

    # Strongly Disagree
    "strongly disagree": 1,
    "Strongly Disagree": 1,

    # Disagree
    "disagree": 2,
    "Disagree": 2,

    # Neutral
    "neutral": 3,
    "Neutral": 3,
    "Neither agree nor disagree": 3,
    "Neither Agree nor Disagree": 3,

    # Agree
    "agree": 4,
    "Agree": 4,

    # Strongly Agree
    "strongly agree": 5,
    "Strongly Agree": 5,

    # Numeric fallback
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5
}

# Reverse scored TAS items
reverse_items = [4, 5, 10, 18, 19]

# ---------------- INTERPRETATIONS ----------------

def tas_interpret(score):

    if score <= 51:
        return "No alexithymia"

    elif score <= 60:
        return "Possible alexithymia"

    else:
        return "Alexithymia likely present"

def beis_interpret(score):

    if score <= 23:
        return "Low Emotional Intelligence"

    elif score <= 37:
        return "Average Emotional Intelligence"

    else:
        return "High Emotional Intelligence"

def dass_interpret(score):

    if score <= 7:
        return "Normal"

    elif score <= 9:
        return "Mild"

    elif score <= 14:
        return "Moderate"

    elif score <= 19:
        return "Severe"

    else:
        return "Extremely Severe"

# ---------------- PROCESS ----------------

if uploaded_file:

    try:

        df = pd.read_excel(uploaded_file)

        columns = df.columns.tolist()

        # ---------------- COLUMN STRUCTURE ----------------
        # 0 = Consent
        # 1 = Name
        # 2 = Age
        # 3 = Place
        # 4 = Gender
        # 5 = Education
        # 6 = Occupation
        # 7-26 = TAS-20
        # 27-36 = BEIS-10
        # 37-43 = DASS Anxiety

        name_col = columns[1]
        gender_col = columns[4]

        tas_cols = columns[7:27]
        beis_cols = columns[27:37]
        dass_cols = columns[37:44]

        results = []

        # ---------------- ROW PROCESSING ----------------

        for _, row in df.iterrows():

            # ---------------- TAS ----------------

            tas_total = 0

            for i, col in enumerate(tas_cols, start=1):

                value = row[col]

                if pd.isna(value):
                    score = 0

                elif isinstance(value, (int, float)):
                    score = int(value)

                else:
                    score = likert_map.get(
                        str(value).strip(),
                        0
                    )

                # Reverse scoring
                if i in reverse_items:
                    score = 6 - score

                tas_total += score

            # ---------------- BEIS ----------------

            beis_total = 0

            for col in beis_cols:

                value = row[col]

                if pd.isna(value):
                    score = 0

                elif isinstance(value, (int, float)):
                    score = int(value)

                else:
                    score = likert_map.get(
                        str(value).strip(),
                        0
                    )

                beis_total += score

            # ---------------- DASS ----------------

            dass_total = 0

            for col in dass_cols:

                value = row[col]

                try:
                    dass_total += int(value)

                except:
                    pass

            # ---------------- SAVE RESULT ----------------

            results.append({

                "Name": row[name_col],
                "Gender": row[gender_col],

                "TAS_Score": tas_total,
                "TAS_Interpretation": tas_interpret(tas_total),

                "BEIS_Score": beis_total,
                "BEIS_Interpretation": beis_interpret(beis_total),

                "DASS_Score": dass_total,
                "DASS_Interpretation": dass_interpret(dass_total)
            })

        processed = pd.DataFrame(results)

        # Remove empty names
        processed = processed.dropna(subset=["Name"])

        # ---------------- EXISTING DATABASE ----------------

        existing = pd.read_sql(
            "SELECT * FROM assessments",
            conn
        )

        # ---------------- REMOVE DUPLICATES ----------------

        if not existing.empty:

            processed = processed[
                ~processed["Name"].astype(str).isin(
                    existing["Name"].astype(str)
                )
            ]

        # ---------------- SAVE ----------------

        if len(processed) > 0:

            processed.to_sql(
                "assessments",
                conn,
                if_exists="append",
                index=False
            )

            st.success(
                f"{len(processed)} new participants added successfully."
            )

        else:

            st.warning("No new participants found.")

    except Exception as e:

        st.error(f"Error: {e}")

# ---------------- SHOW DATABASE ----------------

st.divider()

st.subheader("📋 Master Database")

master_df = pd.read_sql(
    "SELECT * FROM assessments",
    conn
)

if not master_df.empty:

    # ---------------- SORT ----------------

    master_df["_sort"] = master_df["Gender"].astype(str).str.lower().map({
        "male": 0,
        "m": 0,
        "female": 1,
        "f": 1
    }).fillna(2)

    master_df = master_df.sort_values("_sort")

    master_df = master_df.drop(columns=["_sort"])

    master_df = master_df.reset_index(drop=True)

    # ---------------- SEARCH + FILTER ----------------

    col1, col2 = st.columns([3, 1])

    with col1:
        search = st.text_input(
            "🔍 Search participant by name",
            placeholder="Type a name or initials..."
        )

    with col2:
        gender_filter = st.selectbox(
            "Filter by Gender",
            ["All", "Male", "Female"]
        )

    if search:

        master_df = master_df[
            master_df["Name"].astype(str).str.contains(
                search,
                case=False,
                na=False
            )
        ]

    if gender_filter != "All":

        master_df = master_df[
            master_df["Gender"].astype(str).str.lower()
            == gender_filter.lower()
        ]

    # ---------------- TABLE ----------------

    st.write(f"Showing {len(master_df)} record(s)")

    st.dataframe(
        master_df,
        use_container_width=True,
        height=600
    )

    # ---------------- STATS ----------------

    st.divider()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Participants",
        len(master_df)
    )

    col2.metric(
        "Average TAS",
        round(
            pd.to_numeric(
                master_df["TAS_Score"],
                errors="coerce"
            ).mean(),
            2
        )
    )

    col3.metric(
        "Average DASS",
        round(
            pd.to_numeric(
                master_df["DASS_Score"],
                errors="coerce"
            ).mean(),
            2
        )
    )

    # ---------------- DOWNLOAD ----------------

    st.download_button(
        "⬇ Download Database",
        master_df.to_csv(index=False),
        file_name="master_database.csv",
        mime="text/csv"
    )

else:

    st.info("No participants added yet.")