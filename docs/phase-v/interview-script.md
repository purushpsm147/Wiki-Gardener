# Phase V — admin interview script

**Who:** Confluence Cloud site admins, space admins or knowledge managers whose instance has **50k+ pages**. **Length:** 45 minutes.
**Needs no code.** The three mockups are static images built from the synthetic examples in this repo.
**Purpose:** try to *kill* the wedge: find out whether contradictions are urgent, whether an incumbent already covers them, and whether
the app could even be installed. Decision thresholds are **not** in this file; they live in
[`kill-proceed-criteria.md`](kill-proceed-criteria.md) (PV.3, pending source).

## Interviewer rules

1. **No pitch before the mockups.** Elicit pain unprompted first. Don't say "contradiction" until block 4 unless they do.
2. **Past behaviour over opinion.** Ask for the last time, a specific case, a number. Treat "that would be useful" as noise.
3. **Ask "why?" twice.** Don't fill silence. Don't defend the concept.
4. **Log commitments, not compliments.** An intro, a data sample, a pilot or money counts. "Interesting" does not.
5. **Randomise mockup order** (block 4) and record the order you used.
6. **Never show customer content.** Mockups are synthetic. Never record without explicit consent.

## Screening (before booking)

- Admin or knowledge-manager role on Confluence **Cloud**; roughly 50k+ pages (confirm in block 1 and record the real figure).
- Has installed, or been asked to approve, a Marketplace app in the last 12 months.
- Exclude people who work for a competitor and anyone you know personally. Note *how* each person was recruited, because
  respondents to "Confluence hygiene" outreach are a biased sample.

## 0. Opening (3 min)

"I'm researching how teams keep Confluence trustworthy at scale. I'm not selling anything today. Is it OK if I take notes /
record for my own use? Nothing is shared outside the project." *(Record consent: yes / notes only.)*

## 1. Context (5 min)

- What's your role? How many pages, spaces and users, roughly? How do you know?
- Who creates content and who is accountable for it being right? Are there "approved" pages (policies, standards) that
  others must follow? How many?
- Which apps do you run for content quality, archiving or governance? What did each cost, and who chose it?

## 2. Pain, unprompted (8 min)

- "Tell me about the **last time** someone acted on wrong information from Confluence." *(Who, what, when, what it cost.)*
- "How did you find out? What did you do about it?" "How often does that happen?"
- "What do you do today to prevent it? What have you tried or paid for?"
- "If you could remove **one** content-quality problem from your site, which would it be?" *(Record the category they name
  unprompted: stale, duplicate, contradictory, permissions, search quality, other.)*

## 3. Incumbent probe — the Evergreen-forcing block (7 min)

Do this **before** showing any of our mockups.

1. **Unaided:** "Have you heard of or used any Marketplace app that audits or cleans up Confluence content?" *(Record every name
   they volunteer.)*
2. **Aided awareness:** "Do you know **Evergreen AI for Confluence**?"
   - *Knows it:* "What do you understand it to do? Have you trialled or installed it? If not, why not?"
   - *Doesn't:* show its Marketplace listing for about 60 seconds, then: "From this alone, would you install it on production this
     quarter? What would stop you? What do you assume it does that the listing doesn't say?"
3. **What's missing:** "What would you still need that it doesn't give you?" *(Let them list; don't suggest.)*
4. **The forcing question:** "Suppose Evergreen announced next month that it also flags pages that **conflict with each other**,
   and flags a conflict **at the moment someone edits a page**. What would you still need from a separate product?"
   *(If the honest answer is "nothing", record it verbatim. It is the most important sentence in the interview.)*
5. **Atlassian itself:** "Are you using Rovo? The Documentation agent? What does it do for content quality for you today?"
6. Briefly, unaided→aided for **AI Hygiene Inspector** and **Better Content Archiving** (same two questions, one line each).

## 4. Mockup test (12 min)

Show three synthetic mockups **in a randomised order**. Describe nothing; ask what they see.

- **S — Staleness report:** "412 pages not edited in 12 months", sorted by age.
- **C — Contradiction report:** two pages side by side, e.g. *Data Retention Policy: "kept for 90 days"* vs *Runbook: Log Rotation:
  "kept for 30 days"*, both quotes highlighted, with links.
- **E — Edit-time alert:** "You changed '90 days' to '30 days'. The approved policy page says '90 days'", with both quotes.

For each: "What are you looking at? What would you do with it **this week**? Who would you send it to? What's wrong with it?"

Then the **separating questions** (is "contradictions are urgent" different from "staleness alerts would do"?):

- "If all you had was **S**, what would still go wrong in the incident you told me about?"
- "Which of these would have caught that incident? Which would have **missed** it?"
- "You can fund **one** project next week: clearing stale pages, or resolving contradictions between policy and procedure
  pages. Which one, and what happens to the other?"
- "Show me, or describe, a **real** contradiction that mattered: when, who noticed, what it cost." *(No concrete story means the
  urgency is hypothetical. Record that.)*

Then: "If you could only have one of S, C, E, which?" and "Who would pay for it, from which budget, and who approves that?"
(No price is quoted.)

## 5. Access reality (6 min)

- "Walk me through the **last** Marketplace app that was installed on production: who asked, who approved, how long, what did security
  or legal review?"
- "Could **you** get an app installed that reads the text of every page? Who has to say yes, and what would they ask?"
- "What do you require from app vendors: *Runs on Atlassian*, data residency, SOC 2, a DPA, no data leaving Atlassian?"
- "If page text was sent to a server **outside** Atlassian, is that a blocker, an extra review, or fine? What if the analysis ran
  entirely inside Atlassian?" *(This is the Phase V input ADR-013 is waiting for. Record the answer exactly.)*
- "If the app only ever **read** content and never wrote anything, does the approval path change?"
- "From a yes to an installed app: how many weeks?" "Which permission would make you say no outright?"
- "People who'd see the reports: can they all read the pages the reports cite?" *(Touches A06: viewer permissions.)*

## 6. Commitment ask (4 min)

"Would you be willing to: (a) share a **redacted real example** of a contradiction, (b) let me run a **one-off audit** on one space,
(c) introduce me to whoever approves apps, (d) **pay** for a one-off audit?" *Record exactly what they agreed to, not what they said
they "might".* The audit's scope is in [`concierge-scanner-spec.md`](concierge-scanner-spec.md).

## 7. Close (2 min)

"Who else should I talk to? May I follow up?" Thank them. Stop recording.

## Record sheet (fill within 15 minutes of the call)

| Field | Value |
|---|---|
| Date, interviewer, recruited via | |
| Role; pages / spaces / users (their number and how they know) | |
| Unprompted top pain (category) | |
| Concrete recent contradiction story? (Y/N; cost; when; who noticed) | |
| Competitors named **unaided** | |
| Knows Evergreen? Installed? Ruled out (why)? | |
| Would install Evergreen this quarter? (Y/N/maybe + reason) | |
| "What's missing" (verbatim) | |
| Answer to the forcing question (verbatim) | |
| Mockup order used; forced choice among S / C / E; reason | |
| Budget owner and approver named for such a tool | |
| Last app approval: approver, steps, weeks | |
| Stance on data leaving Atlassian: blocker / review / fine | |
| Weight of *Runs on Atlassian* in approval (none / some / required) | |
| Commitment given: none / intro / data sample / audit / paid audit | |
| ≤ 3 verbatim quotes | |

This sheet captures facts only. **Whether they add up to PROCEED or KILL is decided by PV.3, not here.**
