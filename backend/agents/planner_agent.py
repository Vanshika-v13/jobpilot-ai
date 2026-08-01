from typing import List, TypedDict

class SearchPlan(TypedDict):
    portal: str
    role: str
    location: str
    experience: str
    skills: List[str]

def create_search_plans(
    role: str,
    location: str,
    experience: str,
    skills: List[str],
    source: str = "all"
) -> List[SearchPlan]:
    """
    Generate search plans for Internshala and/or Unstop based on the source parameter.
    No LLM call; pure Python logic.
    """
    portals = []
    src = source.lower().strip()
    if src == "internshala":
        portals = ["internshala"]
    elif src == "unstop":
        portals = ["unstop"]
    else:  # "all" or anything else
        portals = ["internshala", "unstop"]

    plans: List[SearchPlan] = []
    for portal in portals:
        plans.append({
            "portal": portal,
            "role": role,
            "location": location,
            "experience": experience,
            "skills": skills
        })
    return plans
