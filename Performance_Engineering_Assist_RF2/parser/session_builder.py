import pandas as pd


class SessionBuilder:

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    # -------------------------------------------------------
    # Build complete session journeys
    # -------------------------------------------------------

    def build_sessions(self):

        sessions = {}

        grouped = self.df.groupby("session_id")

        for session_id, group in grouped:

            group = group.sort_values("timestamp")

            sessions[session_id] = {

                "user_id": group.iloc[0]["user_id"],

                "persona": group.iloc[0]["persona"],

                "start_time": group.iloc[0]["timestamp"],

                "end_time": group.iloc[-1]["timestamp"],

                "duration_seconds": (
                    group.iloc[-1]["timestamp"] -
                    group.iloc[0]["timestamp"]
                ).total_seconds(),

                "steps": list(group["endpoint"])
            }

        return sessions

    # -------------------------------------------------------
    # Convert sessions to dataframe (optional)
    # -------------------------------------------------------

    def sessions_dataframe(self, sessions):

        rows = []

        for sid, details in sessions.items():

            rows.append({

                "session_id": sid,

                "user_id": details["user_id"],

                "persona": details["persona"],

                "journey": " → ".join(details["steps"]),

                "steps": len(details["steps"]),

                "duration_seconds": details["duration_seconds"]

            })

        return pd.DataFrame(rows)