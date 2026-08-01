import pytest
from agents.planner_agent import create_search_plans

def test_planner_internshala():
    plans = create_search_plans(
        role="Backend Developer",
        location="Bangalore",
        experience="0-2 years",
        skills=["Python", "FastAPI"],
        source="internshala"
    )
    assert len(plans) == 1
    assert plans[0]["portal"] == "internshala"
    assert plans[0]["role"] == "Backend Developer"
    assert plans[0]["location"] == "Bangalore"
    assert plans[0]["experience"] == "0-2 years"
    assert plans[0]["skills"] == ["Python", "FastAPI"]

def test_planner_unstop():
    plans = create_search_plans(
        role="Frontend Developer",
        location="Remote",
        experience="Fresher",
        skills=["React", "TypeScript"],
        source="unstop"
    )
    assert len(plans) == 1
    assert plans[0]["portal"] == "unstop"
    assert plans[0]["role"] == "Frontend Developer"
    assert plans[0]["location"] == "Remote"
    assert plans[0]["experience"] == "Fresher"
    assert plans[0]["skills"] == ["React", "TypeScript"]

def test_planner_all():
    plans = create_search_plans(
        role="Fullstack Developer",
        location="Mumbai",
        experience="1-3 years",
        skills=["Node", "React"],
        source="all"
    )
    assert len(plans) == 2
    portals = {p["portal"] for p in plans}
    assert portals == {"internshala", "unstop"}
    for p in plans:
        assert p["role"] == "Fullstack Developer"
        assert p["location"] == "Mumbai"
        assert p["experience"] == "1-3 years"
        assert p["skills"] == ["Node", "React"]
