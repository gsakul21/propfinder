"""
Seed database with realistic Montgomery County, PA sample properties.
Run: DATABASE_URL=... python scripts/seed.py
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow running locally (outside Docker): add project root and backend to path
_root = Path(__file__).resolve().parents[1]
for p in [str(_root), str(_root / "backend")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.dialects.postgresql import insert as pg_insert

from workers.common.db import get_session
from workers.common.models import DistressSignal, Property, PropertyScore

NOW = datetime.now(timezone.utc).replace(tzinfo=None)

# fmt: off
PROPERTIES = [
    # (parcel_id, address, city, zip, lat, lon, assessed_value, owner_name, owner_mailing, prop_type)
    ("MC-001-0001", "412 Elm St",          "Norristown",    "19401", 40.1215, -75.3399, 185000, "Robert Carver",    "PO Box 441, Philadelphia, PA 19103",         "residential"),
    ("MC-001-0002", "87 Oak Ave",           "Lansdale",      "19446", 40.2415, -75.2838, 220000, "Linda Marsh",      "87 Oak Ave, Lansdale, PA 19446",             "residential"),
    ("MC-001-0003", "223 Main St",          "Pottstown",     "19464", 40.2454, -75.6496, 140000, "James Holloway",   "55 Pine Rd, Trenton, NJ 08601",              "residential"),
    ("MC-001-0004", "9 Willow Ln",          "Ambler",        "19002", 40.1537, -75.2260, 310000, "Patricia Dunne",   "9 Willow Ln, Ambler, PA 19002",              "residential"),
    ("MC-001-0005", "561 Cherry St",        "Conshohocken",  "19428", 40.0787, -75.2988, 260000, "Marcus Webb",      "112 Harbor Dr, Baltimore, MD 21201",         "residential"),
    ("MC-001-0006", "30 Broad St",          "Norristown",    "19401", 40.1188, -75.3441, 175000, "Angela Torres",    "30 Broad St, Norristown, PA 19401",          "residential"),
    ("MC-001-0007", "744 Maple Dr",         "Lansdale",      "19446", 40.2372, -75.2911, 198000, "Daniel Frost",     "744 Maple Dr, Lansdale, PA 19446",           "residential"),
    ("MC-001-0008", "18 Spruce Ct",         "Blue Bell",     "19422", 40.1523, -75.2702, 425000, "Evelyn Kraft",     "900 Park Ave, New York, NY 10028",           "residential"),
    ("MC-001-0009", "302 Ash Rd",           "Norristown",    "19401", 40.1234, -75.3521, 162000, "Harold Gibson",    "302 Ash Rd, Norristown, PA 19401",           "residential"),
    ("MC-001-0010", "55 Cedar Blvd",        "Pottstown",     "19464", 40.2512, -75.6388, 132000, "Shirley Quinn",    "PO Box 77, Reading, PA 19601",               "residential"),
    ("MC-001-0011", "1204 Valley Rd",       "Lansdale",      "19446", 40.2499, -75.2744, 245000, "Victor Osei",      "1204 Valley Rd, Lansdale, PA 19446",         "residential"),
    ("MC-001-0012", "67 Mill St",           "Ambler",        "19002", 40.1589, -75.2198, 287000, "Carol Hendrix",    "1500 Market St, Philadelphia, PA 19102",     "residential"),
    ("MC-001-0013", "419 Chestnut Ave",     "Norristown",    "19401", 40.1148, -75.3379, 192000, "Frank Morales",    "419 Chestnut Ave, Norristown, PA 19401",     "residential"),
    ("MC-001-0014", "88 Glenwood Dr",       "Horsham",       "19044", 40.1862, -75.1518, 335000, "Donna Sutton",     "88 Glenwood Dr, Horsham, PA 19044",          "residential"),
    ("MC-001-0015", "330 Fairview St",      "Pottstown",     "19464", 40.2421, -75.6554, 115000, "Gregory Lane",     "PO Box 234, Allentown, PA 18101",            "residential"),
    ("MC-001-0016", "5 Birchwood Ct",       "Jenkintown",    "19046", 40.0943, -75.1278, 398000, "Helen Park",       "77 Ocean Blvd, Miami, FL 33139",             "residential"),
    ("MC-001-0017", "726 Washington St",    "Norristown",    "19401", 40.1266, -75.3403, 155000, "Ivan Novak",       "726 Washington St, Norristown, PA 19401",    "residential"),
    ("MC-001-0018", "14 Briar Ln",          "Lansdale",      "19446", 40.2433, -75.2866, 210000, "Joyce Kimura",     "14 Briar Ln, Lansdale, PA 19446",            "residential"),
    ("MC-001-0019", "890 Hilltop Rd",       "Pottstown",     "19464", 40.2388, -75.6621, 128000, "Kevin Sloane",     "3400 Walnut St, Philadelphia, PA 19104",     "residential"),
    ("MC-001-0020", "43 Locust Ave",        "Ambler",        "19002", 40.1512, -75.2288, 265000, "Laura Vega",       "43 Locust Ave, Ambler, PA 19002",            "residential"),
    ("MC-001-0021", "177 Summit Blvd",      "Blue Bell",     "19422", 40.1556, -75.2634, 412000, "Michael Stern",    "PO Box 88, Princeton, NJ 08540",             "residential"),
    ("MC-001-0022", "532 Grove St",         "Norristown",    "19401", 40.1199, -75.3488, 143000, "Nancy Bloom",      "532 Grove St, Norristown, PA 19401",         "residential"),
    ("MC-001-0023", "61 Orchard Rd",        "Horsham",       "19044", 40.1823, -75.1456, 356000, "Oscar Delgado",    "PO Box 912, Las Vegas, NV 89101",            "residential"),
    ("MC-001-0024", "295 Penn St",          "Pottstown",     "19464", 40.2467, -75.6472, 138000, "Paula Novak",      "295 Penn St, Pottstown, PA 19464",           "residential"),
    ("MC-001-0025", "110 Riverside Dr",     "Norristown",    "19401", 40.1178, -75.3556, 168000, "Quincy Adams",     "200 King of Prussia Rd, Wayne, PA 19087",    "residential"),
    ("MC-001-0026", "8 Foxglove Ln",        "Lansdale",      "19446", 40.2352, -75.2789, 232000, "Rachel Burns",     "8 Foxglove Ln, Lansdale, PA 19446",          "residential"),
    ("MC-001-0027", "644 Market St",        "Norristown",    "19401", 40.1211, -75.3421, 158000, "Samuel Chen",      "PO Box 333, Harrisburg, PA 17101",           "residential"),
    ("MC-001-0028", "22 Dogwood Dr",        "Jenkintown",    "19046", 40.0912, -75.1334, 445000, "Theresa Ngozi",    "22 Dogwood Dr, Jenkintown, PA 19046",        "residential"),
    ("MC-001-0029", "501 Industry Rd",      "Conshohocken",  "19428", 40.0812, -75.3012, 520000, "Urban Holdings LLC", "1600 JFK Blvd, Philadelphia, PA 19103",   "commercial"),
    ("MC-001-0030", "78 Heritage Dr",       "Horsham",       "19044", 40.1877, -75.1489, 367000, "Vivian Okonkwo",   "78 Heritage Dr, Horsham, PA 19044",          "residential"),
    ("MC-001-0031", "350 Jefferson Ave",    "Pottstown",     "19464", 40.2438, -75.6580, 121000, "Walter Crane",     "PO Box 5, Camden, NJ 08101",                 "residential"),
    ("MC-001-0032", "139 Pinecrest Rd",     "Blue Bell",     "19422", 40.1498, -75.2723, 388000, "Xena Patel",       "50 Sunset Blvd, Los Angeles, CA 90028",      "residential"),
    ("MC-001-0033", "67 Buttonwood St",     "Norristown",    "19401", 40.1243, -75.3461, 147000, "Yolanda Fitch",    "67 Buttonwood St, Norristown, PA 19401",     "residential"),
    ("MC-001-0034", "488 Stony Creek Rd",   "Lansdale",      "19446", 40.2461, -75.2698, 253000, "Zachary Horn",     "PO Box 202, Wilmington, DE 19801",           "residential"),
    ("MC-001-0035", "25 Foxcroft Ln",       "Ambler",        "19002", 40.1566, -75.2241, 298000, "Alice Montes",     "25 Foxcroft Ln, Ambler, PA 19002",           "residential"),
    ("MC-001-0036", "912 Lincoln Hwy",      "Pottstown",     "19464", 40.2478, -75.6541, 109000, "Boris Kwan",       "PO Box 71, Norristown, PA 19401",            "residential"),
    ("MC-001-0037", "34 Bala Ave",          "Bala Cynwyd",   "19004", 40.0079, -75.2278, 578000, "Clara Whitfield",  "34 Bala Ave, Bala Cynwyd, PA 19004",         "residential"),
    ("MC-001-0038", "760 Germantown Pike",  "Plymouth Meeting","19462",40.1132, -75.2923, 342000, "Devon Shah",       "PO Box 44, Atlanta, GA 30301",               "residential"),
    ("MC-001-0039", "118 Elmwood Ave",      "Norristown",    "19401", 40.1221, -75.3512, 171000, "Elaine Ross",      "118 Elmwood Ave, Norristown, PA 19401",      "residential"),
    ("MC-001-0040", "575 Skippack Pike",    "Lansdale",      "19446", 40.2405, -75.2855, 228000, "Franklin Tse",     "PO Box 10, King of Prussia, PA 19406",       "residential"),
]

# (parcel_id, signal_type, raw_data)
SIGNALS = [
    ("MC-001-0001", "tax_delinquency", {"tax_year": 2023, "amount_due": 4200, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0001", "foreclosure",     {"case_number": "2024-FC-00112", "filing_date": "2024-03-15", "stage": "active", "auction_date": None}),
    ("MC-001-0001", "absentee",        {"location": "different_county"}),

    ("MC-001-0003", "tax_delinquency", {"tax_year": 2022, "amount_due": 8100, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0003", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0005", "tax_delinquency", {"tax_year": 2022, "amount_due": 6300, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0005", "foreclosure",     {"case_number": "2024-FC-00289", "filing_date": "2024-07-20", "stage": "auction", "auction_date": "2026-05-10"}),
    ("MC-001-0005", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0008", "tax_delinquency", {"tax_year": 2024, "amount_due": 3500, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0008", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0010", "tax_delinquency", {"tax_year": 2021, "amount_due": 11200, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 3}),
    ("MC-001-0010", "foreclosure",     {"case_number": "2023-FC-00071", "filing_date": "2023-11-05", "stage": "active", "auction_date": None}),
    ("MC-001-0010", "absentee",        {"location": "different_county"}),

    ("MC-001-0012", "tax_delinquency", {"tax_year": 2023, "amount_due": 5600, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0012", "absentee",        {"location": "different_county"}),

    ("MC-001-0015", "tax_delinquency", {"tax_year": 2022, "amount_due": 9400, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0015", "foreclosure",     {"case_number": "2025-FC-00044", "filing_date": "2025-01-08", "stage": "filing", "auction_date": None}),
    ("MC-001-0015", "absentee",        {"location": "different_county"}),

    ("MC-001-0016", "tax_delinquency", {"tax_year": 2023, "amount_due": 7200, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0016", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0019", "tax_delinquency", {"tax_year": 2021, "amount_due": 13500, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 3}),
    ("MC-001-0019", "absentee",        {"location": "different_county"}),

    ("MC-001-0021", "tax_delinquency", {"tax_year": 2024, "amount_due": 2800, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0021", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0023", "foreclosure",     {"case_number": "2025-FC-00199", "filing_date": "2025-02-14", "stage": "auction", "auction_date": "2026-06-01"}),
    ("MC-001-0023", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0025", "tax_delinquency", {"tax_year": 2023, "amount_due": 4900, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0025", "absentee",        {"location": "same_county"}),

    ("MC-001-0027", "tax_delinquency", {"tax_year": 2022, "amount_due": 7700, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0027", "absentee",        {"location": "different_county"}),

    ("MC-001-0029", "tax_delinquency", {"tax_year": 2022, "amount_due": 22000, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0029", "foreclosure",     {"case_number": "2025-FC-00301", "filing_date": "2025-03-22", "stage": "active", "auction_date": None}),
    ("MC-001-0029", "absentee",        {"location": "different_county"}),

    ("MC-001-0031", "tax_delinquency", {"tax_year": 2021, "amount_due": 9800, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 3}),
    ("MC-001-0031", "foreclosure",     {"case_number": "2024-FC-00452", "filing_date": "2024-09-11", "stage": "auction", "auction_date": "2026-05-22"}),
    ("MC-001-0031", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0032", "tax_delinquency", {"tax_year": 2024, "amount_due": 3100, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0032", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0034", "tax_delinquency", {"tax_year": 2023, "amount_due": 5300, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0034", "absentee",        {"location": "different_county"}),

    ("MC-001-0036", "tax_delinquency", {"tax_year": 2022, "amount_due": 8900, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0036", "absentee",        {"location": "same_county"}),

    ("MC-001-0038", "tax_delinquency", {"tax_year": 2023, "amount_due": 4600, "delinquency_status": "active", "sale_eligible": False, "years_delinquent": 1}),
    ("MC-001-0038", "absentee",        {"location": "out_of_state"}),

    ("MC-001-0040", "tax_delinquency", {"tax_year": 2022, "amount_due": 6100, "delinquency_status": "active", "sale_eligible": True,  "years_delinquent": 2}),
    ("MC-001-0040", "absentee",        {"location": "same_county"}),
]


def _compute_score(signals: list) -> dict:
    tax = foreclosure = absentee = 0
    for sig_type, raw in signals:
        if sig_type == "tax_delinquency":
            y = raw.get("years_delinquent", 0)
            tax = 35 if y >= 2 else (25 if y >= 1 else 15)
        elif sig_type == "foreclosure":
            stage = raw.get("stage", "filing")
            foreclosure = 40 if stage == "auction" else (35 if stage == "active" else 30)
        elif sig_type == "absentee":
            loc = raw.get("location", "same_county")
            absentee = 20 if loc == "out_of_state" else (15 if loc == "different_county" else 10)

    n = sum(1 for v in [tax, foreclosure, absentee] if v > 0)
    bonus = 15 if n >= 3 else (10 if n >= 2 else 0)
    final = max(0, min(100, tax + foreclosure + absentee + bonus))
    tier = "hot" if final >= 80 else ("warm" if final >= 50 else "cold")
    return {"score": final, "tier": tier, "reasons": {"tax": tax, "foreclosure": foreclosure, "absentee": absentee, "bonus": bonus, "penalty": 0}}


def seed() -> None:
    session = get_session()

    # Build parcel_id -> property_id map
    prop_id_map: dict[str, uuid.UUID] = {}

    print("Seeding properties...")
    for (parcel_id, address, city, zip_code, lat, lon, assessed_value, owner_name, owner_mailing, prop_type) in PROPERTIES:
        geom = from_shape(Point(lon, lat), srid=4326)
        pid = uuid.uuid4()
        prop_id_map[parcel_id] = pid
        is_absentee = owner_mailing and address.split(",")[0].strip().upper() not in owner_mailing.upper()

        stmt = pg_insert(Property).values(
            id=pid,
            parcel_id=parcel_id,
            address=address,
            city=city,
            state="PA",
            zip_code=zip_code,
            county="Montgomery",
            property_type=prop_type,
            latitude=lat,
            longitude=lon,
            geom=geom,
            assessed_value=assessed_value,
            owner_name=owner_name,
            owner_mailing_address=owner_mailing,
            is_absentee=is_absentee,
        ).on_conflict_do_update(
            index_elements=["parcel_id"],
            set_={
                "address": address,
                "owner_name": owner_name,
                "owner_mailing_address": owner_mailing,
                "latitude": lat,
                "longitude": lon,
                "geom": geom,
                "is_absentee": is_absentee,
                "assessed_value": assessed_value,
            },
        ).returning(Property.id)
        result = session.execute(stmt)
        prop_id_map[parcel_id] = result.scalar()

    session.flush()

    print("Seeding distress signals...")
    signals_by_parcel: dict[str, list] = {}
    for (parcel_id, sig_type, raw_data) in SIGNALS:
        if parcel_id not in signals_by_parcel:
            signals_by_parcel[parcel_id] = []
        signals_by_parcel[parcel_id].append((sig_type, raw_data))

    for parcel_id, sigs in signals_by_parcel.items():
        prop_id = prop_id_map[parcel_id]
        for sig_type, raw_data in sigs:
            severity_map = {
                "tax_delinquency": lambda r: 35 if r.get("years_delinquent", 0) >= 2 else (25 if r.get("years_delinquent", 0) >= 1 else 15),
                "foreclosure": lambda r: 40 if r.get("stage") == "auction" else (35 if r.get("stage") == "active" else 30),
                "absentee": lambda r: 20 if r.get("location") == "out_of_state" else (15 if r.get("location") == "different_county" else 10),
            }
            severity = severity_map[sig_type](raw_data)
            stmt = pg_insert(DistressSignal).values(
                id=uuid.uuid4(),
                property_id=prop_id,
                signal_type=sig_type,
                severity=severity,
                raw_data=raw_data,
                detected_at=NOW,
            ).on_conflict_do_update(
                index_elements=["property_id", "signal_type"],
                set_={"severity": severity, "raw_data": raw_data, "detected_at": NOW},
            )
            session.execute(stmt)

    print("Computing scores...")
    for parcel_id, sigs in signals_by_parcel.items():
        prop_id = prop_id_map[parcel_id]
        result = _compute_score(sigs)
        stmt = pg_insert(PropertyScore).values(
            property_id=prop_id,
            score=result["score"],
            tier=result["tier"],
            reasons=result["reasons"],
            computed_at=NOW,
        ).on_conflict_do_update(
            index_elements=["property_id"],
            set_={"score": result["score"], "tier": result["tier"], "reasons": result["reasons"], "computed_at": NOW},
        )
        session.execute(stmt)

    # Score 0 / cold for properties with no signals
    for parcel_id, pid in prop_id_map.items():
        if parcel_id not in signals_by_parcel:
            stmt = pg_insert(PropertyScore).values(
                property_id=pid,
                score=0,
                tier="cold",
                reasons={"tax": 0, "foreclosure": 0, "absentee": 0, "bonus": 0, "penalty": 0},
                computed_at=NOW,
            ).on_conflict_do_nothing()
            session.execute(stmt)

    session.commit()
    session.close()
    print(f"Done. {len(PROPERTIES)} properties, {len(SIGNALS)} signals seeded.")


if __name__ == "__main__":
    seed()
