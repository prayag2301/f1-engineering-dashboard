"""
Seed endpoint — populates the database with realistic F1 2025 data for development.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

try:
    from app.database import get_db
    from app.models.models import (
        Team,
        Race,
        Component,
        Upgrade,
        PerformanceDelta,
        Event,
        Evidence,
        RegulationConstraint,
    )
    from app.models.enums import UpgradeCategory, ComponentZone, EventStatus
    from app.services.regulation_parser import parse_regulations
except ModuleNotFoundError:  # Docker image expects backend.* imports
    from backend.database import get_db
    from backend.models.models import (
        Team,
        Race,
        Component,
        Upgrade,
        PerformanceDelta,
        Event,
        Evidence,
        RegulationConstraint,
    )
    from backend.models.enums import UpgradeCategory, ComponentZone, EventStatus
    from backend.services.regulation_parser import parse_regulations

router = APIRouter()


TEAMS = [
    {"name": "Red Bull", "full_name": "Oracle Red Bull Racing", "base": "Milton Keynes, UK", "team_principal": "Christian Horner", "power_unit": "Honda RBPT"},
    {"name": "Ferrari", "full_name": "Scuderia Ferrari", "base": "Maranello, Italy", "team_principal": "Frédéric Vasseur", "power_unit": "Ferrari"},
    {"name": "Mercedes", "full_name": "Mercedes-AMG Petronas F1 Team", "base": "Brackley, UK", "team_principal": "Toto Wolff", "power_unit": "Mercedes"},
    {"name": "McLaren", "full_name": "McLaren F1 Team", "base": "Woking, UK", "team_principal": "Andrea Stella", "power_unit": "Mercedes"},
    {"name": "Aston Martin", "full_name": "Aston Martin Aramco F1 Team", "base": "Silverstone, UK", "team_principal": "Mike Krack", "power_unit": "Mercedes"},
    {"name": "Alpine", "full_name": "BWT Alpine F1 Team", "base": "Enstone, UK", "team_principal": "Oliver Oakes", "power_unit": "Renault"},
    {"name": "Williams", "full_name": "Williams Racing", "base": "Grove, UK", "team_principal": "James Vowles", "power_unit": "Mercedes"},
    {"name": "RB", "full_name": "Visa Cash App RB F1 Team", "base": "Faenza, Italy", "team_principal": "Laurent Mekies", "power_unit": "Honda RBPT"},
    {"name": "Kick Sauber", "full_name": "Stake F1 Team Kick Sauber", "base": "Hinwil, Switzerland", "team_principal": "Mattia Binotto", "power_unit": "Ferrari"},
    {"name": "Haas", "full_name": "MoneyGram Haas F1 Team", "base": "Kannapolis, USA", "team_principal": "Ayao Komatsu", "power_unit": "Ferrari"},
]

RACES_2025 = [
    {"name": "Australian GP", "circuit": "Albert Park Circuit", "country": "Australia", "round_number": 1, "season": 2025, "date": "2025-03-16"},
    {"name": "Chinese GP", "circuit": "Shanghai International Circuit", "country": "China", "round_number": 2, "season": 2025, "date": "2025-03-23"},
    {"name": "Japanese GP", "circuit": "Suzuka International Racing Course", "country": "Japan", "round_number": 3, "season": 2025, "date": "2025-04-06"},
    {"name": "Bahrain GP", "circuit": "Bahrain International Circuit", "country": "Bahrain", "round_number": 4, "season": 2025, "date": "2025-04-13"},
    {"name": "Saudi Arabian GP", "circuit": "Jeddah Corniche Circuit", "country": "Saudi Arabia", "round_number": 5, "season": 2025, "date": "2025-04-20"},
    {"name": "Miami GP", "circuit": "Miami International Autodrome", "country": "USA", "round_number": 6, "season": 2025, "date": "2025-05-04"},
    {"name": "Emilia Romagna GP", "circuit": "Autodromo Enzo e Dino Ferrari", "country": "Italy", "round_number": 7, "season": 2025, "date": "2025-05-18"},
    {"name": "Monaco GP", "circuit": "Circuit de Monaco", "country": "Monaco", "round_number": 8, "season": 2025, "date": "2025-05-25"},
    {"name": "Spanish GP", "circuit": "Circuit de Barcelona-Catalunya", "country": "Spain", "round_number": 9, "season": 2025, "date": "2025-06-01"},
    {"name": "Canadian GP", "circuit": "Circuit Gilles Villeneuve", "country": "Canada", "round_number": 10, "season": 2025, "date": "2025-06-15"},
]

COMPONENTS = [
    {"name": "Front Wing Endplate", "zone": ComponentZone.FRONT_WING, "description": "Endplate geometry controlling front wing tip vortex"},
    {"name": "Front Wing Mainplane", "zone": ComponentZone.FRONT_WING, "description": "Primary front wing element generating downforce"},
    {"name": "Floor Edge", "zone": ComponentZone.FLOOR_EDGE, "description": "Floor edge geometry managing ground effect seal"},
    {"name": "Floor Fence", "zone": ComponentZone.FLOOR, "description": "Longitudinal floor fences directing underfloor airflow"},
    {"name": "Diffuser Strake", "zone": ComponentZone.DIFFUSER, "description": "Diffuser internal strake controlling expansion rate"},
    {"name": "Sidepod Inlet", "zone": ComponentZone.SIDEPOD, "description": "Sidepod inlet geometry for cooling and aero efficiency"},
    {"name": "Rear Wing Flap", "zone": ComponentZone.REAR_WING, "description": "Upper rear wing flap for DRS and downforce tuning"},
    {"name": "Brake Duct Inlet", "zone": ComponentZone.BRAKE_DUCT, "description": "Front/rear brake cooling duct inlet geometry"},
    {"name": "Engine Cover Bodywork", "zone": ComponentZone.ENGINE_COVER, "description": "Engine cover shaping affecting rear-end aero"},
    {"name": "Suspension Fairing", "zone": ComponentZone.SUSPENSION_ARM, "description": "Aerodynamic fairing around suspension elements"},
]

SAMPLE_EVENTS = [
    {"race": "Australian GP", "status": EventStatus.PUBLISHED},
    {"race": "Bahrain GP", "status": EventStatus.PUBLISHED},
    {"race": "Miami GP", "status": EventStatus.ANNOTATING},
    {"race": "Spanish GP", "status": EventStatus.RECONSTRUCTING},
    {"race": "Canadian GP", "status": EventStatus.PENDING},
]

SAMPLE_EVIDENCE = [
    {
        "team": "Red Bull",
        "race": "Bahrain GP",
        "component": "Floor Edge",
        "source": "Motorsport Week — Bahrain GP upgrades overview",
        "license": "editorial",
        "credibility_score": 0.92,
        "media_path": "s3://f1-evidence/2025/bahrain/redbull/floor-edge/photo-1.jpg",
        "article_path": "https://www.motorsportweek.com/2025/04/11/ferrari-leads-f1-bahrain-gp-upgrades-list-with-extensive-package/",
    },
    {
        "team": "Ferrari",
        "race": "Bahrain GP",
        "component": "Sidepod Inlet",
        "source": "The Race — Ferrari SF-25 Bahrain GP upgrade revealed",
        "license": "editorial",
        "credibility_score": 0.86,
        "media_path": "s3://f1-evidence/2025/bahrain/ferrari/sidepod-inlet/photo-2.jpg",
        "article_path": "https://www.the-race.com/formula-1/ferrari-sf25-bahrain-gp-upgrade-floor/",
    },
    {
        "team": "McLaren",
        "race": "Miami GP",
        "component": "Front Wing Endplate",
        "source": "The Race — McLaren & Mercedes Miami GP upgrades declared",
        "license": "editorial",
        "credibility_score": 0.81,
        "media_path": "s3://f1-evidence/2025/miami/mclaren/front-wing-endplate/photo-3.jpg",
        "article_path": "https://www.the-race.com/formula-1/mclaren-mercedes-upgrades-miami-gp-f1-declared/",
    },
    {
        "team": "Mercedes",
        "race": "Spanish GP",
        "component": "Diffuser Strake",
        "source": "Motorsport Week — Mercedes leads Spanish GP upgrades",
        "license": "editorial",
        "credibility_score": 0.79,
        "media_path": "s3://f1-evidence/2025/spain/mercedes/diffuser-strake/photo-4.jpg",
        "article_path": "https://www.motorsportweek.com/2025/05/30/mercedes-leads-the-way-with-upgrades-for-f1-spanish-gp/",
    },
    {
        "team": "Red Bull",
        "race": "Emilia Romagna GP",
        "component": "Suspension Fairing",
        "source": "PlanetF1 — Why Red Bull's big RB21 Imola upgrade will have everyone taking note",
        "license": "editorial",
        "credibility_score": 0.84,
        "media_path": "s3://f1-evidence/2025/imola/redbull/suspension-fairing/photo-5.jpg",
        "article_path": "https://www.planetf1.com/features/red-bull-rb21-upgrade-f1-imola-gp-analysis",
    },
]


@router.post("/", status_code=201)
def seed_database(db: Session = Depends(get_db)):
    """Populate database with initial F1 2025 data."""

    # Check if already seeded — if so, only backfill regulations if missing
    if db.query(Team).first():
        existing_regs = (
            db.query(RegulationConstraint)
            .filter(RegulationConstraint.season == 2026)
            .count()
        )
        if existing_regs == 0:
            constraints = parse_regulations(season=2026)
            for c in constraints:
                db.add(
                    RegulationConstraint(
                        season=c.season,
                        component=c.component,
                        parameter=c.parameter,
                        value=c.value,
                        unit=c.unit,
                        article_ref=c.article_ref,
                        notes=c.notes,
                    )
                )
            db.commit()
            return {
                "message": "Core data already seeded; regulation constraints backfilled",
                "seeded": False,
                "regulation_constraints_seeded": len(constraints),
            }
        return {"message": "Database already seeded", "seeded": False, "regulation_constraints_seeded": 0}

    # Teams
    team_objs = {}
    for t in TEAMS:
        team = Team(**t)
        db.add(team)
        db.flush()
        team_objs[t["name"]] = team

    # Races
    race_objs = {}
    for r in RACES_2025:
        race = Race(
            name=r["name"],
            circuit=r["circuit"],
            country=r["country"],
            round_number=r["round_number"],
            season=r["season"],
            date=datetime.strptime(r["date"], "%Y-%m-%d"),
        )
        db.add(race)
        db.flush()
        race_objs[r["name"]] = race

    # Components
    comp_objs = {}
    for c in COMPONENTS:
        comp = Component(**c)
        db.add(comp)
        db.flush()
        comp_objs[c["name"]] = comp

    # Sample upgrades
    sample_upgrades = [
        {
            "team": "Red Bull",
            "race": "Bahrain GP",
            "component": "Floor Edge",
            "category": UpgradeCategory.AERO,
            "description": "Revised floor edge profile with tighter radius curvature to strengthen the vortex seal along the floor perimeter.",
            "technical_detail": "The new floor edge features a compound curve reducing separation at yaw angles >3°. CFD indicates a 12% stronger floor edge vortex, improving the pressure differential beneath the floor.",
            "expected_effect": "Improved rear stability under braking and cornering, reduced porpoising sensitivity.",
            "confidence": 0.78,
            "aero_reasoning": "Stronger floor edge vortex creates a more robust seal, maintaining consistent ground effect across varying ride heights.",
            "mechanical_reasoning": "Reduced porpoising implies lower peak suspension loads, extending component life.",
            "performance_hypothesis": "Estimated 0.15s lap time improvement at high-downforce circuits.",
            "source": "FIA Technical Directive 2025-003",
        },
        {
            "team": "Ferrari",
            "race": "Bahrain GP",
            "component": "Sidepod Inlet",
            "category": UpgradeCategory.COOLING,
            "description": "Narrowed sidepod inlet with internal guide vanes to improve cooling efficiency while reducing frontal area.",
            "technical_detail": "Inlet area reduced by 8% with 3 internal guide vanes directing airflow to radiator cores. Heat rejection maintained through improved flow uniformity.",
            "expected_effect": "Lower drag coefficient with equivalent cooling capacity.",
            "confidence": 0.72,
            "aero_reasoning": "Smaller frontal area directly reduces pressure drag. Guide vanes prevent flow separation inside the duct.",
            "mechanical_reasoning": "Maintained cooling ensures PU operates within thermal limits under all conditions.",
            "performance_hypothesis": "Estimated 3-5 km/h top speed gain on straights.",
            "source": "Scuderia Ferrari technical briefing",
        },
        {
            "team": "McLaren",
            "race": "Miami GP",
            "component": "Front Wing Endplate",
            "category": UpgradeCategory.AERO,
            "description": "Redesigned front wing endplate with revised footplate geometry to manage front tire wake.",
            "technical_detail": "New footplate incorporates a 15mm Gurney-style trip along the lower edge, energizing the outboard vortex system. Upper endplate features a revised scroll geometry.",
            "expected_effect": "Better front-end grip and improved outwash pattern.",
            "confidence": 0.81,
            "aero_reasoning": "The Gurney trip energizes the boundary layer along the footplate, generating a stronger Y250-style outboard vortex for consistent outwash.",
            "mechanical_reasoning": "Improved front-end grip reduces front tire degradation through lower slip angles.",
            "performance_hypothesis": "Estimated 0.1-0.2s improvement in medium-speed corners.",
            "source": "McLaren technical analysis",
        },
        {
            "team": "Mercedes",
            "race": "Spanish GP",
            "component": "Diffuser Strake",
            "category": UpgradeCategory.AERO,
            "description": "Reconfigured diffuser strake layout optimizing expansion ratio in the central diffuser channel.",
            "technical_detail": "Central strake repositioned 25mm outboard with modified height progression. Outer strakes feature new curvature to manage the rear tire squirt interference.",
            "expected_effect": "Improved rear downforce with better diffuser pumping.",
            "confidence": 0.68,
            "aero_reasoning": "Controlled expansion in the central channel recovers more pressure energy, increasing the overall pressure differential across the floor.",
            "mechanical_reasoning": "More consistent rear downforce reduces oversteer tendency in long high-speed corners.",
            "performance_hypothesis": "Estimated 0.1s improvement at aero-sensitive circuits.",
            "source": "Mercedes AMG technical bulletin",
        },
        {
            "team": "Red Bull",
            "race": "Emilia Romagna GP",
            "component": "Suspension Fairing",
            "category": UpgradeCategory.MECHANICAL,
            "description": "Revised front suspension fairing geometry to reduce drag and improve airflow to sidepod inlets.",
            "technical_detail": "Fairing cross-section changed from elliptical to a more aggressive teardrop profile. Leading edge sweep increased by 5° to better manage the front tire wake.",
            "expected_effect": "Cleaner airflow to the rear of the car.",
            "confidence": 0.74,
            "aero_reasoning": "Reduced wake from suspension elements allows more energized air to reach the sidepod and floor leading edge.",
            "mechanical_reasoning": "New fairing accommodates revised suspension geometry for improved ride compliance.",
            "performance_hypothesis": "Estimated 2-3 km/h top speed gain with maintained downforce.",
            "source": "Red Bull Racing technical overview",
        },
    ]

    seeded_upgrades = {}
    for u in sample_upgrades:
        upgrade = Upgrade(
            team_id=team_objs[u["team"]].id,
            race_id=race_objs[u["race"]].id,
            component_id=comp_objs[u["component"]].id,
            category=u["category"],
            description=u["description"],
            technical_detail=u["technical_detail"],
            expected_effect=u["expected_effect"],
            confidence=u["confidence"],
            aero_reasoning=u["aero_reasoning"],
            mechanical_reasoning=u["mechanical_reasoning"],
            performance_hypothesis=u["performance_hypothesis"],
            source=u["source"],
        )
        db.add(upgrade)
        db.flush()
        seeded_upgrades[(u["team"], u["race"], u["component"])] = upgrade

    # Sample events
    for event in SAMPLE_EVENTS:
        db.add(
            Event(
                race_id=race_objs[event["race"]].id,
                status=event["status"],
            )
        )

    # Sample evidence linked to seeded upgrades
    for item in SAMPLE_EVIDENCE:
        upgrade_key = (item["team"], item["race"], item["component"])
        linked_upgrade = seeded_upgrades.get(upgrade_key)
        if not linked_upgrade:
            continue
        db.add(
            Evidence(
                upgrade_id=linked_upgrade.id,
                source=item["source"],
                license=item["license"],
                credibility_score=item["credibility_score"],
                media_path=item["media_path"],
                article_path=item["article_path"],
            )
        )

    # Sample performance deltas
    sample_deltas = [
        {
            "team": "Red Bull",
            "race": "Bahrain GP",
            "fp1_time": 91.234,
            "quali_time": 89.456,
            "race_best_lap": 90.123,
            "delta_fp1_to_quali": -1.778,
            "upgrade_efficiency_score": 0.82,
        },
        {
            "team": "Ferrari",
            "race": "Bahrain GP",
            "fp1_time": 91.567,
            "quali_time": 89.789,
            "race_best_lap": 90.345,
            "delta_fp1_to_quali": -1.778,
            "upgrade_efficiency_score": 0.75,
        },
    ]

    for d in sample_deltas:
        delta = PerformanceDelta(
            team_id=team_objs[d["team"]].id,
            race_id=race_objs[d["race"]].id,
            fp1_time=d["fp1_time"],
            quali_time=d["quali_time"],
            race_best_lap=d["race_best_lap"],
            delta_fp1_to_quali=d["delta_fp1_to_quali"],
            upgrade_efficiency_score=d["upgrade_efficiency_score"],
        )
        db.add(delta)

    db.commit()

    # Seed regulation constraints (runs even if core data was already present)
    existing_regs = (
        db.query(RegulationConstraint)
        .filter(RegulationConstraint.season == 2026)
        .count()
    )
    if existing_regs == 0:
        constraints = parse_regulations(season=2026)
        for c in constraints:
            db.add(
                RegulationConstraint(
                    season=c.season,
                    component=c.component,
                    parameter=c.parameter,
                    value=c.value,
                    unit=c.unit,
                    article_ref=c.article_ref,
                    notes=c.notes,
                )
            )
        db.commit()
        regulations_seeded = len(constraints)
    else:
        regulations_seeded = 0

    return {
        "message": "Database seeded successfully",
        "seeded": True,
        "teams": len(TEAMS),
        "races": len(RACES_2025),
        "components": len(COMPONENTS),
        "upgrades": len(sample_upgrades),
        "events": len(SAMPLE_EVENTS),
        "evidence": len(SAMPLE_EVIDENCE),
        "performance_deltas": len(sample_deltas),
        "regulation_constraints_seeded": regulations_seeded,
    }
