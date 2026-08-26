#!/usr/bin/env python3
"""
Synthetic demo dataset for the calling platform.

Generates a believable backlog-reactivation campaign with zero real customer
data, so the system can be demonstrated without putting anyone's name, number,
or address on a stranger's screen.

Design decisions worth knowing:

- Phone numbers use the 555-01XX block, which is permanently reserved for
  fiction and can never be assigned to a real person. They read as slightly
  fake, and that is the correct trade for a demo you hand to strangers.
- Seeded, so it is byte-identical every run. A demo that changes between
  rehearsal and the real thing is a demo that surprises you in front of someone.
- Disposition mix is modeled on a genuinely cold aged list, not a happy path.
  Mostly no-answer, a real slice of wrong numbers, a small number of opt-outs.
  A demo dataset with a 40% booking rate tells an experienced operator you have
  never run one of these.
- Every opt-out carries an audit trail: which call produced it, when, and the
  caller's exact words. That is the record a compliance reviewer asks for.

Usage:
    python3 generate_demo_data.py --out ./demo_data [--contacts 250] [--seed 7]
"""
import argparse, csv, json, os, random
from datetime import datetime, timedelta

FIRST = ["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda",
    "David","Elizabeth","William","Barbara","Richard","Susan","Joseph","Jessica",
    "Thomas","Sarah","Charles","Karen","Christopher","Nancy","Daniel","Lisa",
    "Matthew","Betty","Anthony","Margaret","Mark","Sandra","Donald","Ashley",
    "Steven","Kimberly","Paul","Emily","Andrew","Donna","Joshua","Michelle",
    "Kenneth","Carol","Kevin","Amanda","Brian","Dorothy","George","Melissa",
    "Timothy","Deborah","Ronald","Stephanie","Edward","Rebecca","Jason","Sharon",
    "Jeffrey","Laura","Ryan","Cynthia","Jacob","Kathleen","Gary","Amy","Nicholas",
    "Angela","Eric","Shirley","Jonathan","Anna","Stephen","Ruth","Larry","Brenda"]

LAST = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
    "Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Wilson","Anderson",
    "Thomas","Taylor","Moore","Jackson","Martin","Lee","Perez","Thompson","White",
    "Harris","Sanchez","Clark","Ramirez","Lewis","Robinson","Walker","Young",
    "Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores","Green",
    "Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter",
    "Roberts","Yoder","Stoltzfus","Weaver","Zimmerman","Hoffman","Schaeffer",
    "Stoltzfus","Kauffman","Hershey","Bechtel","Diehl","Wentzel","Moyer","Landis"]

TOWNS = [("Royersford","19468"),("Phoenixville","19460"),("Collegeville","19426"),
    ("Pottstown","19464"),("Limerick","19468"),("Spring City","19475"),
    ("Reading","19601"),("Sinking Spring","19608"),("Wyomissing","19610"),
    ("Birdsboro","19508"),("Douglassville","19518"),("Boyertown","19512"),
    ("Gilbertsville","19525"),("Schwenksville","19473"),("Norristown","19401"),
    ("King of Prussia","19406"),("Exeter","19606"),("Laureldale","19605")]

STREETS = ["Main St","Walnut St","Chestnut St","Church Rd","Ridge Rd","Mill Rd",
    "Maple Ave","Oak Ln","Buttonwood St","Franklin St","Lincoln Ave","Park Ave",
    "Bridge St","Hill Rd","Spring St","Cherry Ln","Washington St","Second Ave"]

SOURCES = [("box_program", 0.42), ("county_fair", 0.21), ("referral", 0.14),
           ("home_show", 0.11), ("web_form", 0.07), ("past_customer", 0.05)]

# Aged-list reality. These do not sum to a flattering number, on purpose.
DISPOSITIONS = [
    ("no_answer",      0.360),
    ("voicemail",      0.170),
    ("not_interested", 0.150),
    ("wrong_number",   0.085),
    ("callback",       0.075),
    ("disconnected",   0.070),
    ("booked",         0.055),
    ("dnc",            0.020),
    ("language_barrier", 0.015),
]

CONNECTED = {"not_interested","callback","booked","dnc","language_barrier"}

DNC_QUOTES = [
    "Take me off your list please.",
    "I don't want any more calls about this. Remove me.",
    "Put me on your do not call list.",
    "Stop calling this number.",
    "I've asked before. Do not call me again.",
]

def weighted(rng, pairs):
    r, acc = rng.random(), 0.0
    for value, w in pairs:
        acc += w
        if r <= acc:
            return value
    return pairs[-1][0]

def make_phone(rng, used):
    """555-01XX is permanently reserved for fiction. Cannot reach a real person."""
    while True:
        area = rng.choice(["610","484","215","267"])
        n = f"+1{area}555{rng.randint(100,199):04d}"
        if n not in used:
            used.add(n)
            return n

def duration_for(disposition, rng):
    if disposition in ("no_answer","disconnected"):
        return 0
    if disposition == "voicemail":
        return rng.randint(18, 41)
    if disposition == "wrong_number":
        return rng.randint(9, 28)
    if disposition == "language_barrier":
        return rng.randint(12, 35)
    if disposition == "not_interested":
        return rng.randint(22, 74)
    if disposition == "dnc":
        return rng.randint(11, 33)
    if disposition == "callback":
        return rng.randint(41, 96)
    if disposition == "booked":
        return rng.randint(148, 331)
    return 30

def transcript_for(d, name, rng, town):
    """Modeled on a gift-card lead call flow: intro, incentive, demo offer, alternate-choice close."""
    agent = "Alex"
    intro = (f"Hi, is this {name}? Hi {name}, this is {agent} calling from Fieldstone "
             f"Home Products. You entered to receive a free twenty dollar gift card, and "
             f"I'm calling to schedule a time to drop that off for you.")
    if d == "booked":
        return [
            ("agent", intro),
            ("customer", "Oh, right. I think I filled that out at the pizza place."),
            ("agent", "That's the one. When we come by with the gift card we also do a quick "
                      "demonstration of our cleaning system, it also purifies the air. "
                      " Short visit, no obligation. Would tomorrow evening around six or "
                      "Thursday afternoon around two work better for you?"),
            ("customer", "Thursday afternoon is better. Two is fine."),
            ("agent", "Thursday at two. A couple quick questions so we can prepare. Does anyone "
                      "in the house have allergies or asthma?"),
            ("customer", "My son does, allergies."),
            ("agent", "Good to know. Any pets or small children?"),
            ("customer", "Two dogs."),
            ("agent", "Perfect. We do ask that both you and your spouse are there so you can both "
                      "see it and ask questions. Will that work?"),
            ("customer", "Yeah, he's home by then."),
            ("agent", f"You're all set for Thursday at two. You'll get the gift card just for "
                      f"having us out. Thanks {name}, we'll see you then."),
        ]
    if d == "dnc":
        return [
            ("agent", intro),
            ("customer", rng.choice(DNC_QUOTES)),
            ("agent", "I understand, I apologize for the call. I'm marking this number do not "
                      "call and you'll be removed from any future outreach. Thank you for your "
                      "time, have a good day."),
        ]
    if d == "not_interested":
        return [
            ("agent", intro),
            ("customer", "Yeah I remember. I'm honestly not interested in a demonstration though."),
            ("agent", "Not a problem at all. I appreciate you letting me know. Thanks for your "
                      "time and have a good rest of your day."),
        ]
    if d == "callback":
        return [
            ("agent", intro),
            ("customer", "I'm actually walking into work right now. Can you try me later?"),
            ("agent", "Of course. What day and time is usually good for you?"),
            ("customer", "Try me Saturday morning, before ten."),
            ("agent", "Saturday morning before ten, I've got it down. Thanks, talk to you then."),
        ]
    if d == "wrong_number":
        return [
            ("agent", "Hi, is this " + name + "?"),
            ("customer", "No, you've got the wrong number. There's nobody here by that name."),
            ("agent", "Sorry to bother you, I'll get this number corrected. Have a good day."),
        ]
    if d == "language_barrier":
        return [
            ("agent", intro),
            ("customer", "No English, sorry. No English."),
            ("agent", "No problem at all, I apologize. Thank you, goodbye."),
        ]
    if d == "voicemail":
        return [("agent", f"Hi {name}, this is {agent} from Fieldstone Home Products calling about "
                          f"the twenty dollar gift card you entered for. Give us a call back when "
                          f"you get a chance. Thanks.")]
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./demo_data")
    ap.add_argument("--contacts", type=int, default=250)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.join(args.out, "transcripts"), exist_ok=True)

    # Campaign runs across a fixed window so the demo never shifts with today's date.
    campaign_start = datetime(2026, 6, 1, 9, 0)

    used_numbers, contacts, calls, dnc_log, appointments = set(), [], [], [], []
    call_id = 1000

    for i in range(1, args.contacts + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        town, zipc = rng.choice(TOWNS)
        phone = make_phone(rng, used_numbers)
        # Aged: entered between 8 months and 3.5 years before the campaign.
        entered = campaign_start - timedelta(days=rng.randint(240, 1280))
        contact = {
            "contact_id": 200000 + i,
            "first_name": first,
            "last_name": last,
            "phone": phone,
            "address": f"{rng.randint(12, 4200)} {rng.choice(STREETS)}",
            "city": town,
            "state": "PA",
            "zip": zipc,
            "source": weighted(rng, SOURCES),
            "entered_date": entered.strftime("%Y-%m-%d"),
            "days_aged": (campaign_start - entered).days,
        }
        contacts.append(contact)

        # 82% of the list gets attempted in this campaign window.
        if rng.random() > 0.82:
            continue

        attempts = 1
        d = weighted(rng, DISPOSITIONS)
        # No-answers get retried, like a real dialer would.
        if d in ("no_answer", "voicemail"):
            attempts = rng.randint(1, 3)

        for attempt in range(1, attempts + 1):
            call_id += 1
            final = d if attempt == attempts else "no_answer"
            when = campaign_start + timedelta(
                days=rng.randint(0, 44), hours=rng.randint(0, 9), minutes=rng.randint(0, 59))
            dur = duration_for(final, rng)
            rec = {
                "call_id": call_id,
                "contact_id": contact["contact_id"],
                "to": phone,
                "direction": "outbound" if rng.random() > 0.08 else "inbound",
                "started_at": when.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_sec": dur,
                "disposition": final,
                "attempt": attempt,
                "connected": final in CONNECTED,
                "recording_url": f"demo://recordings/{call_id}.wav" if dur > 0 else None,
            }

            t = transcript_for(final, first, rng, town)
            if t:
                rec["transcript_ref"] = f"transcripts/{call_id}.json"
                with open(os.path.join(args.out, "transcripts", f"{call_id}.json"), "w") as f:
                    json.dump({"call_id": call_id, "turns":
                               [{"speaker": s, "text": x} for s, x in t]}, f, indent=2)

            if final == "booked":
                appt = when + timedelta(days=rng.randint(1, 6))
                appt = appt.replace(hour=rng.choice([10, 13, 14, 17, 18]), minute=0, second=0)
                rec["appointment_at"] = appt.strftime("%Y-%m-%d %H:%M")
                appointments.append({
                    "contact_id": contact["contact_id"],
                    "name": f"{first} {last}",
                    "phone": phone,
                    "city": town,
                    "appointment_at": rec["appointment_at"],
                    "booked_on_call": call_id,
                    "notes": "Allergies in household; pets present; spouse confirmed present.",
                })

            if final == "dnc":
                quote = next(x for s, x in t if s == "customer")
                dnc_log.append({
                    "contact_id": contact["contact_id"],
                    "phone": phone,
                    "requested_at": when.strftime("%Y-%m-%d %H:%M:%S"),
                    "source_call_id": call_id,
                    "customer_words": quote,
                    "suppressed": "yes",
                    "confirmed_on_call": "yes",
                })

            calls.append(rec)

    # ---- write ----
    def write_csv(name, rows):
        if not rows:
            return
        with open(os.path.join(args.out, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv("contacts.csv", contacts)
    write_csv("dnc_log.csv", dnc_log)
    write_csv("appointments.csv", appointments)
    with open(os.path.join(args.out, "calls.json"), "w") as f:
        json.dump(calls, f, indent=2)

    # ---- summary, the numbers you'd quote in a demo ----
    from collections import Counter
    counts = Counter(c["disposition"] for c in calls)
    connected = [c for c in calls if c["connected"]]
    talk = [c["duration_sec"] for c in connected]
    summary = {
        "contacts_in_backlog": len(contacts),
        "contacts_attempted": len({c["contact_id"] for c in calls}),
        "total_calls_placed": len(calls),
        "by_disposition": dict(counts.most_common()),
        "connect_rate": round(len(connected) / len(calls), 3),
        "appointments_booked": len(appointments),
        "booking_rate_on_connect": round(len(appointments) / len(connected), 3),
        "opt_outs_captured": len(dnc_log),
        "numbers_suppressed": len({d["phone"] for d in dnc_log}),
        "bad_numbers_identified": counts["wrong_number"] + counts["disconnected"],
        "avg_talk_time_sec": round(sum(talk) / len(talk), 1),
        "campaign_window": "2026-06-01 to 2026-07-15",
        "oldest_contact_days": max(c["days_aged"] for c in contacts),
    }
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nWrote to {args.out}/")
    print("  contacts.csv  dnc_log.csv  appointments.csv  calls.json  summary.json  transcripts/")

if __name__ == "__main__":
    main()
