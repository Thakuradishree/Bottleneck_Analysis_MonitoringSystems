from pathlib import Path
import pandas as pd
import streamlit as st


REQUIRED_COLUMNS = [
    "timestamp",
    "session_id",
    "user_id",
    "persona",
    "module",
    "endpoint",
    "method",
    "status_code",
    "response_time_ms"
]


class LogParser:

    def __init__(self):
        self.df = None

    # -------------------------------------------
    # Read CSV
    # -------------------------------------------
    def read_logs(self, uploaded_file):

        try:

            self.df = pd.read_csv(uploaded_file)

            return self.df

        except Exception as e:

            st.error(f"Unable to read CSV.\n\n{e}")

            return None

    # -------------------------------------------
    # Validate Schema
    # -------------------------------------------
    def validate_schema(self):

        missing = []

        for column in REQUIRED_COLUMNS:

            if column not in self.df.columns:
                missing.append(column)

        if len(missing) > 0:

            st.error(
                "Missing Columns : "
                + ", ".join(missing)
            )

            return False

        return True

    # -------------------------------------------
    # Clean Logs
    # -------------------------------------------
    def clean_logs(self):

        self.df["timestamp"] = pd.to_datetime(
            self.df["timestamp"],
            errors="coerce"
        )

        self.df = self.df.dropna()

        self.df = self.df.drop_duplicates()

        self.df = self.df.sort_values(
            by=["session_id", "timestamp"]
        )

        self.df.reset_index(
            drop=True,
            inplace=True
        )

        return self.df

    # -------------------------------------------
    # Dataset Statistics
    # -------------------------------------------
    def get_statistics(self):

        stats = {

            "Total Logs":
                len(self.df),

            "Unique Sessions":
                self.df["session_id"].nunique(),

            "Unique Users":
                self.df["user_id"].nunique(),

            "Modules":
                self.df["module"].nunique(),

            "Endpoints":
                self.df["endpoint"].nunique(),

            "Average Response Time (ms)":
                round(
                    self.df["response_time_ms"].mean(),
                    2
                ),

            "Error Requests":

                len(

                    self.df[
                        self.df["status_code"] != 200
                    ]
                )
        }

        return stats

    # -------------------------------------------
    # Preview
    # -------------------------------------------
    def preview_logs(self):

        st.dataframe(
            self.df.head(20),
            use_container_width=True
        )