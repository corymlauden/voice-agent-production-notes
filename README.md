# voice-agent-production-notes

Field notes from building and running an AI calling platform for a real sales
office. Outbound and inbound, in production, built by the person who also runs
the sales team it works for.

This repo is the writeup, not the product. The production code is tied to
vendor accounts, a private CRM, and real customer data, so it stays private.
What's here is the part worth reading anyway: how the system is designed, what
the hard parts turned out to be, and a fully synthetic dataset that shows the
operating shape without a single real name or number in it.

## The problem

We had thousands of old contacts sitting in our CRM. Years of them. Gift card
entries, fair leads, referrals, people who said call me in the spring back
when it was a different spring. Nobody was ever going to call that list. You
can't ask a rep to spend a week on contacts that cold.

So I built something that would.

## What it does

It works the backlog on its own, roughly 4,000 aged contacts, the full CRM
history. Calls out, books appointments, and sorts the list while it goes.
Live numbers get separated from dead ones, opt-outs get flagged and
suppressed, and every result is written back.

It also answers our office line around the clock. Questions about the office,
questions about the product, all the way through a booked appointment, with
nobody on our end of the call.

The write-back is the part most people skip. Our CRM has no API, so a call
result that isn't typed in by hand normally doesn't exist. Here, browser
automation enters the outcome into the CRM after each call, field by field,
the way a person would.

Results so far: dozens of booked appointments off a list nobody was going to
touch, closed sales from those appointments, hundreds of inbound calls
handled, and a database that's cleaner than it has been in years. Still
running.

## The stack

Retell AI for the voice agent layer, GPT-4.1 for the conversation, ElevenLabs
for the voice, Twilio underneath, Google Sheets over service-account auth for
the team-facing call lists, and Python holding it together. The outbound
booking agent is a 13-node conversation flow. Post-call analysis runs on a
smaller model and turns every recording into structured notes.

[docs/conversation-flow.md](docs/conversation-flow.md) walks through the flow.
[docs/compliance-design.md](docs/compliance-design.md) covers the part that
took the longest.

## The hard parts

Getting an agent to hold a pleasant ninety-second conversation is the easy
half. The hard part was everything around it.

What happens when somebody says take me off your list. That's a legal
obligation, not a preference, and it gets its own conversation path, immediate
suppression, and an audit record with the caller's exact words.

What happens on a wrong number, a flat no, or "call me back Saturday
morning." Each one is its own path with its own follow-up behavior, because
lumping them together either burns goodwill or loses appointments.

Personal information shows up in transcripts whether you want it there or
not. It gets redacted before anything is stored or synced.

And the boring one that matters most: results have to land in the CRM, and
the CRM has no API. The browser automation that does the entry has to survive
an application that was never designed to be driven by software. The read and
write approach is written up in
[legacy-crm-toolkit](https://github.com/corymlauden/legacy-crm-toolkit).

## The demo dataset

[demo/](demo/) holds a generator and a pre-generated campaign: 250 synthetic
contacts, 328 calls, transcripts, appointments, and a do-not-call audit log.

All of it is fiction. Phone numbers come from the 555-01XX block, which is
permanently reserved for fiction and cannot reach a real person. The
disposition mix is modeled on a genuinely cold aged list: mostly no-answers,
a real slice of wrong numbers, a few opt-outs. A demo dataset with a 40%
booking rate tells an experienced operator you've never run one of these.
This one connects on 19% of calls and books on 30% of connects, which is what
an honest aged-list campaign looks like.

To poke at it, no dependencies needed:

```bash
cd demo
python3 show.py                # the campaign numbers
python3 show.py call 1038      # one booked call, turn by turn
python3 show.py dnc            # the do-not-call audit log
python3 show.py cleanup        # what got written back to the CRM
```

## What's deliberately not here

The production conversation prompts, the vendor configuration, the CRM
automation, and anything derived from real customer data. None of that is
mine to publish, and you don't need it to evaluate the thinking.

MIT licensed.
