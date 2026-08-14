from collections import Counter
import json


class JourneyExtractor:

    def __init__(self, sessions):
        self.sessions = sessions

    # -------------------------------------------------
    # Normalize journey
    # -------------------------------------------------

    def normalize(self, steps):

        normalized = []

        previous = None

        # Remove consecutive duplicates
        for step in steps:

            if step != previous:
                normalized.append(step)

            previous = step

        # Ignore optional pages
        ignore = {

            "/filter",
            "/sort",
            "/recommendations",
            "/offers",
            "/banner"

        }

        normalized = [

            step

            for step in normalized

            if step not in ignore

        ]

        return normalized

    # -------------------------------------------------
    # Classify Journey
    # -------------------------------------------------

    def classify(self, steps):

        s = set(steps)

        if "/payment" in s:

            return "Buyer Journey"

        if "/checkout" in s:

            return "Checkout Journey"

        if "/track-order" in s:

            return "Returning Customer"

        if "/cancel-order" in s:

            return "Cancelled Order"

        if "/search" in s and "/homepage" in s:

            return "Guest Journey"

        return "Other"

    # -------------------------------------------------
    # Extract
    # -------------------------------------------------

    def extract(self):

        counter = Counter()

        sample_paths = {}

        total_sessions = len(self.sessions)

        for session in self.sessions.values():

            normalized = self.normalize(

                session["steps"]

            )

            label = self.classify(

                normalized

            )

            counter[label] += 1

            if label not in sample_paths:

                sample_paths[label] = normalized

        journeys = []

        for label, users in counter.most_common():

            journeys.append({

                "journey_name": label,

                "users": users,

                "percentage":

                    round(

                        users * 100 / total_sessions,

                        2

                    ),

                "sample_flow":

                    sample_paths[label]

            })

        return journeys

    # -------------------------------------------------
    # Top N
    # -------------------------------------------------

    def top_journeys(self, n=5):

        return self.extract()[:n]

    # -------------------------------------------------
    # JSON
    # -------------------------------------------------

    def to_json(self, journeys):

        return json.dumps(

            {

                "top_user_journeys": journeys

            },

            indent=4

        )