#!/usr/bin/env python3
"""
Read the demo campaign from the terminal.

    python3 show.py                  campaign summary
    python3 show.py calls            every connected call, one line each
    python3 show.py call 1038        one transcript, turn by turn
    python3 show.py appointments     what got booked and the prep notes
    python3 show.py dnc              the do-not-call audit log
    python3 show.py cleanup          what the campaign fixed in the list

Reads from ./data by default. Pass --data to point somewhere else.
No dependencies beyond the standard library.
"""
import argparse, csv, json, os, sys

try:  # let `show.py calls | head` exit quietly
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError):
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

LABELS = {
    "no_answer": "No answer",
    "voicemail": "Voicemail",
    "not_interested": "Not interested",
    "booked": "Booked",
    "wrong_number": "Wrong number",
    "callback": "Callback requested",
    "disconnected": "Disconnected number",
    "dnc": "Do not call",
    "language_barrier": "Language barrier",
}


def load(data_dir):
    def rows(name):
        with open(os.path.join(data_dir, name), newline="") as f:
            return list(csv.DictReader(f))
    with open(os.path.join(data_dir, "calls.json")) as f:
        calls = json.load(f)
    with open(os.path.join(data_dir, "summary.json")) as f:
        summary = json.load(f)
    return {
        "calls": calls,
        "summary": summary,
        "contacts": {r["contact_id"]: r for r in rows("contacts.csv")},
        "appointments": rows("appointments.csv"),
        "dnc": rows("dnc_log.csv"),
    }


def pct(x):
    return f"{x * 100:.1f}%"


def rule(ch="-", n=72):
    print(ch * n)


def show_summary(d):
    s = d["summary"]
    print()
    print("FIELDSTONE HOME PRODUCTS   Backlog reactivation   " + s["campaign_window"])
    rule("=")
    print(f"Backlog            {s['contacts_in_backlog']} contacts, oldest {s['oldest_contact_days']:,} days")
    print(f"Attempted          {s['contacts_attempted']} contacts, {s['total_calls_placed']} calls placed")
    print(f"Connect rate       {pct(s['connect_rate'])}")
    print(f"Booked             {s['appointments_booked']} appointments, {pct(s['booking_rate_on_connect'])} of connects")
    print(f"Avg talk time      {s['avg_talk_time_sec']:.0f} sec on connected calls")
    print()
    print("Dispositions")
    rule()
    total = s["total_calls_placed"]
    width = 36
    for key, n in sorted(s["by_disposition"].items(), key=lambda kv: -kv[1]):
        bar = "#" * max(1, round(n / total * width))
        print(f"  {LABELS.get(key, key):<22}{n:>4}  {bar}")
    print()
    print("List cleanup, as a side effect")
    rule()
    print(f"  Bad numbers identified     {s['bad_numbers_identified']}  (wrong number + disconnected)")
    print(f"  Opt-outs captured          {s['opt_outs_captured']}  all {s['numbers_suppressed']} suppressed, audit log in dnc_log.csv")
    print()
    print("Try:  python3 show.py call 1038      python3 show.py dnc")
    print()


def show_calls(d):
    print()
    print(f"{'call':>5}  {'date':<16} {'contact':<22} {'disp':<20} {'sec':>4}")
    rule()
    for c in d["calls"]:
        if not c.get("connected"):
            continue
        who = d["contacts"].get(str(c["contact_id"]), {})
        name = f"{who.get('first_name','')} {who.get('last_name','')}".strip()
        print(f"{c['call_id']:>5}  {c['started_at'][:16]:<16} {name:<22} {LABELS.get(c['disposition'], c['disposition']):<20} {c['duration_sec']:>4}")
    print()


def show_call(d, call_id, data_dir):
    call = next((c for c in d["calls"] if str(c["call_id"]) == str(call_id)), None)
    if not call:
        sys.exit(f"No call {call_id}")
    who = d["contacts"].get(str(call["contact_id"]), {})
    print()
    print(f"Call {call['call_id']}   {call['started_at']}   {call['duration_sec']} sec   attempt {call['attempt']}")
    print(f"To:  {who.get('first_name','')} {who.get('last_name','')}  {call['to']}  ({who.get('city','')}, {who.get('state','')})")
    print(f"Source: {who.get('source','')}, entered {who.get('entered_date','')}, {who.get('days_aged','')} days old")
    print(f"Disposition: {LABELS.get(call['disposition'], call['disposition'])}")
    if call.get("appointment_at"):
        print(f"Appointment: {call['appointment_at']}")
    rule()
    ref = call.get("transcript_ref")
    if not ref:
        print("No transcript. The call did not connect.")
        print()
        return
    with open(os.path.join(data_dir, ref)) as f:
        t = json.load(f)
    for turn in t["turns"]:
        tag = "AGENT " if turn["speaker"] == "agent" else "CALLER"
        print(f"{tag}  {turn['text']}")
        print()


def show_appointments(d):
    print()
    print(f"{'when':<17} {'name':<20} {'city':<16} notes")
    rule()
    for a in sorted(d["appointments"], key=lambda r: r["appointment_at"]):
        print(f"{a['appointment_at']:<17} {a['name']:<20} {a['city']:<16} {a['notes']}")
    print()
    print(f"{len(d['appointments'])} appointments. Each one came off a contact nobody was going to call.")
    print()


def show_dnc(d):
    print()
    print("Do-not-call audit log")
    rule("=")
    for r in d["dnc"]:
        print(f"{r['requested_at']}   {r['phone']}   call {r['source_call_id']}")
        print(f"   caller said:  \"{r['customer_words']}\"")
        print(f"   suppressed: {r['suppressed']}   confirmed on call: {r['confirmed_on_call']}")
        print()
    print("Every entry records the exact words. That is what a compliance reviewer asks for.")
    print()


def show_cleanup(d):
    calls = d["calls"]
    wrong = {c["contact_id"] for c in calls if c["disposition"] == "wrong_number"}
    dead = {c["contact_id"] for c in calls if c["disposition"] == "disconnected"}
    dnc = {c["contact_id"] for c in calls if c["disposition"] == "dnc"}
    cb = {c["contact_id"] for c in calls if c["disposition"] == "callback"}
    print()
    print("What the campaign wrote back to the CRM")
    rule("=")
    print(f"  {len(wrong):>3} contacts flagged wrong number, phone field cleared for correction")
    print(f"  {len(dead):>3} contacts marked disconnected, removed from dial lists")
    print(f"  {len(dnc):>3} contacts suppressed with a do-not-call flag and audit record")
    print(f"  {len(cb):>3} callbacks written to the team's daily list with the caller's window")
    print(f"  {len(d['appointments']):>3} appointments created with prep notes for the rep")
    print()
    print("None of this was typed by a person. The CRM has no API; a browser did the entry.")
    print()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("what", nargs="?", default="summary",
                   choices=["summary", "calls", "call", "appointments", "dnc", "cleanup"])
    p.add_argument("call_id", nargs="?")
    p.add_argument("--data", default=os.path.join(HERE, "data"))
    a = p.parse_args()
    d = load(a.data)
    if a.what == "summary":
        show_summary(d)
    elif a.what == "calls":
        show_calls(d)
    elif a.what == "call":
        if not a.call_id:
            sys.exit("Usage: show.py call <call_id>   (try: show.py calls)")
        show_call(d, a.call_id, a.data)
    elif a.what == "appointments":
        show_appointments(d)
    elif a.what == "dnc":
        show_dnc(d)
    elif a.what == "cleanup":
        show_cleanup(d)


if __name__ == "__main__":
    main()
