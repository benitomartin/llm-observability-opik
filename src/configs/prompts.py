from settings import SummaryConfig

SUMMARY_VARIANTS: dict[str, SummaryConfig] = {
    "default": {
        "prompt": """Create a comprehensive summary of {team} from the following Wikipedia content:

                Content:
                {content}

                Expected sections:
                1. **Overview & History**
                2. **Stadium & Facilities**
                3. **Major Achievements**
                4. **Notable Players & Management**
                5. **Recent Performance**
                6. **Culture & Rivalries**

                Keep it factual, structured
                """,
        "max_tokens": 1200,
    },
    "recent": {
        "prompt": """Write a summary of {team} about its recent achievements focusing on from the following content:

                Content:
                {content}

                Expected sections:
                1. **Recent Achievements (2020-2025)**
                2. **Current Performance (2023-2025)**
                3. **Latest Developments (2025)**

                Keep it factual, structured.
                """,
        "max_tokens": 1200,
    },
    "achievements": {
        "prompt": """Write a summary of {team} about its overall historical achievements focusing
                     on from the following content:

                Content:
                {content}

                Expected sections:
                1. **Major Trophies**
                2. **Records & Milestones**
                3. **Historical Significance**

                Keep it factual, structured.
                """,
        "max_tokens": 1200,
    },
}
