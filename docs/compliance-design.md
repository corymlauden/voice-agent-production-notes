# Compliance design

The part of the project that took the longest, and the part I'd show first to
anyone evaluating whether a voice agent is production-ready. Getting the
do-not-call piece wrong is a legal problem, not a bug.

This describes how one production system treats it. It is not legal advice.

## Who gets called at all

The outbound list is people who gave us their contact information through our
own lead programs: gift card entries, event signups, referrals, past
customers. An existing relationship, not a purchased list. Numbers already on
the internal suppression list never make it into a campaign.

## Do not call, end to end

The request can show up in many shapes. "Take me off your list." "Stop
calling me." "I've asked before." The agent doesn't need magic words; the
intent routes to a dedicated state where the only possible behaviors are
confirming the removal out loud and ending the call politely. No recovery
attempt, no "before you go."

What gets written, immediately and automatically:

The number is suppressed in the calling system, so no future campaign can
select it. The contact is flagged in the database, so a human pulling a list
sees it too. And an audit record is appended with the timestamp, the call it
came from, and the caller's exact words. When someone asks how you honor
opt-outs, the answer is a log, not a promise. That's the record a compliance
reviewer actually asks for, and the demo dataset includes a synthetic version
of it: [demo/data/dnc_log.csv](../demo/data/dnc_log.csv).

## Wrong and dead numbers

A wrong number is suppressed for that contact and flagged for correction, so
the same person never gets bothered twice by a bad record. Disconnected
numbers are marked dead. Nobody's afternoon should be spent redialing a fax
machine, including the agent's.

## Calling windows

Outbound runs inside daytime and early-evening hours, the same windows a
respectful human caller would keep. Callbacks are honored in the window the
customer named, not whenever the queue gets around to it.

## Personal information

Transcripts get PII redaction before storage or sync. The notes the team
sees carry what they need to run the appointment, not everything a person
happened to say near a microphone.

## Why this much machinery

Because the failure mode is quiet. An agent that mishandles one opt-out
doesn't crash. It just creates liability and calls someone who told you to
stop, which is worse. The only defense is making the compliant path the
structurally easy one: dedicated states the conversation cannot avoid,
suppression that happens without a human remembering to do it, and an audit
trail written at the moment it happens.
