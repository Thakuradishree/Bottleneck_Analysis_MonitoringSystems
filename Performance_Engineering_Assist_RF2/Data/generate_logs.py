from pathlib import Path
import pandas as pd
import random
from datetime import datetime, timedelta

# ==========================================================
# PROJECT PATHS (WORKS FROM ANYWHERE)
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = DATA_DIR / "sample_logs.csv"

# ==========================================================
# CONFIGURATION
# ==========================================================

TOTAL_LOGS = 2500

random.seed(42)

# ==========================================================
# USER JOURNEYS
# ==========================================================

JOURNEYS = {

    "Buyer":[

        ("Authentication","POST","/login"),

        ("Catalog","GET","/products"),

        ("Search","GET","/search"),

        ("Catalog","GET","/product"),

        ("Cart","POST","/cart"),

        ("Checkout","POST","/checkout"),

        ("Payment","POST","/payment")

    ],

    "Guest":[

        ("Homepage","GET","/homepage"),

        ("Catalog","GET","/products"),

        ("Search","GET","/search"),

        ("Homepage","GET","/exit")

    ],

    "Returning":[

        ("Authentication","POST","/login"),

        ("Orders","GET","/orders"),

        ("Orders","GET","/track-order"),

        ("Authentication","GET","/logout")

    ],

    "Cancelled":[

        ("Authentication","POST","/login"),

        ("Catalog","GET","/products"),

        ("Cart","POST","/cart"),

        ("Checkout","POST","/checkout"),

        ("Orders","POST","/cancel-order"),

        ("Authentication","GET","/logout")

    ]

}

WEIGHTS = [70,15,10,5]

# ==========================================================
# RESPONSE TIMES
# ==========================================================

RESPONSE = {

"/homepage":(20,80),

"/login":(80,220),

"/products":(100,300),

"/search":(150,450),

"/product":(120,350),

"/cart":(150,500),

"/checkout":(350,900),

"/payment":(800,1800),

"/orders":(180,450),

"/track-order":(100,250),

"/cancel-order":(350,700),

"/logout":(40,120),

"/exit":(20,50)

}

# ==========================================================
# STATUS CODE
# ==========================================================

def generate_status():

    x=random.random()

    if x<0.95:
        return 200

    elif x<0.97:
        return 404

    elif x<0.99:
        return 500

    else:
        return 503

# ==========================================================
# GENERATE LOGS
# ==========================================================

rows=[]

start=datetime.now()

session_number=1

journey_names=list(JOURNEYS.keys())

while len(rows)<TOTAL_LOGS:

    session_id=f"S{session_number:05}"

    session_number+=1

    user_id=f"U{random.randint(1000,9999)}"

    persona=random.choice([
        "Guest",
        "Buyer",
        "Premium"
    ])

    journey=random.choices(

        journey_names,

        weights=WEIGHTS,

        k=1

    )[0]

    flow=JOURNEYS[journey]

    current=start+timedelta(

        seconds=random.randint(0,7200)

    )

    for module,method,endpoint in flow:

        if len(rows)>=TOTAL_LOGS:
            break

        low,high=RESPONSE[endpoint]

        response=random.randint(low,high)

        rows.append({

            "timestamp":current.strftime("%Y-%m-%d %H:%M:%S"),

            "session_id":session_id,

            "user_id":user_id,

            "persona":persona,

            "module":module,

            "endpoint":endpoint,

            "method":method,

            "status_code":generate_status(),

            "response_time_ms":response

        })

        current+=timedelta(

            seconds=random.randint(2,18)

        )

# ==========================================================
# SAVE
# ==========================================================

df=pd.DataFrame(rows)

df.to_csv(OUTPUT_FILE,index=False)

# ==========================================================
# SUMMARY
# ==========================================================

print("\n"+"="*70)

print("LOG FILE GENERATED SUCCESSFULLY")

print("="*70)

print(f"Rows Generated : {len(df)}")

print(f"Unique Sessions: {df['session_id'].nunique()}")

print(f"Unique Users   : {df['user_id'].nunique()}")

print(f"\nSaved To:\n{OUTPUT_FILE}")

print("\nFirst 10 Records:\n")

print(df.head(10))

print("\n"+"="*70)