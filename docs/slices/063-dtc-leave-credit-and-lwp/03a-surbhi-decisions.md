# 063 · Decisions for Surbhi

From the functional spec v4.0 (`03-functional-spec.md`) and `prototype-v4.html`, 25 Oct 2026.
Nothing here is decided yet. Each point needs your yes or your change.

## Bad news first

1. **Three things block switch-on, whatever you decide below.** Field rights (ALV-215) must ship. The rehearsal must pass. You must check the Housekeeping table rows.
2. **Nobody can see a Housekeeping person's leave figures today.** None of the 42 has a login. HR filing for them is blocked from seeing the figure by a security rule (point 1 below). If you say no to point 1, the Housekeeping card is built for nobody, and I recommend cutting it.
3. **DTC payroll has no setting that leaves Housekeeping out.** HR must delete their 42 rows from every month's Payroll Entry by hand. If HR forgets once, DTC pays an agency worker.
4. **One switch turns on both leave (063) and the pay-slip marks (067).** So 067 cannot go live before 063.
5. **One Hindi draft wrongly promises pay to Housekeeping staff.** Two more Hindi lines are wrong for them. Hindi stays off until fixed and checked by a native speaker.

---

## Part 1 · Where the build differs from prototype v4

The spec counts 13. With the HR notice that was never drawn, there are 14. Listed here in full.

### Where the prototype meets a rule or the truth

| # | What differs | Example | My recommendation |
|---|---|---|---|
| 1 (X-2) | HR filing for someone does **not** see their Paid Leaves figure. The prototype shows it. | Ritika files for Geeta. Prototype: "Geeta has earned 2 so far". Build: no figure at all. | **Change to the prototype.** HR already sees the same number in the desk report. The security agent must update its rule. |
| 2 (X-4) | After Approve or Decline, the prototype says "Priya has been told too". | 0 of 445 DTC staff have an email on record, so nobody is told. Build says: "Priya has no email on record, so please tell them." | **Yes to the build.** The drawn line would be untrue every time at DTC. |
| 3 (X-5) | Hindi version of every screen. | **Three Hindi drafts are wrong for Housekeeping:** (a) the Paid Leaves preview says "इन दिनों का पैसा मिलेगा" ("these days will be paid") - but the agency pays, not DTC; (b) the half-day note keeps "charged double on a special day", which does not apply to them; (c) the leave-without-pay result drops the "2 of 5 used" sentence. | **Change.** Fix all three, then a native speaker checks. No Hindi file is installed until then. |
| 4 (X-6) | **The HR notice is not drawn at all.** You asked on 25 Oct that HR is told of every approval. | The build sends HR the wording in Part 2 below. | **Yes**, with the Part 2 wording (or your edit). |
| 5 (X-8) | **At the cap, the prototype says the count still goes up. It cannot.** | Geeta has 4 of 4. Prototype: "You have earned the most your class allows (4). This goes up as you attend more days in October." Build keeps only the first sentence. | **Yes to the build.** The second sentence is false at the cap. |
| 6 (X-9) | For a "No Leave" person, the prototype blames their work type. It is really their leave class. | Sushila. Prototype: "Your work type does not get Paid Leaves...". Build: "Your leave class (No Leave) does not get Paid Leaves, so only Leave Without Pay is offered." | **Yes to the build.** Contract staff keep the drawn sentence. |

### Where the engineer built it differently

| # | What differs | Example | My recommendation |
|---|---|---|---|
| 7 (D-1) | The "Getting your Paid Leaves..." placeholder is missing on the very first visit. | First visit shows the page's usual "Loading...". Every visit after shows the drawn one. | **Yes.** The page only learns it is DTC from the server. |
| 8 (D-2) | The "(2 people)" count is the real number told. | Sunil approves; only Kavita is above him. Line says "(1 person)", not "(2 people)". | **Yes.** "Told" must be true. |
| 9 (D-3) | The Half day box sits below the preview, not above. | Same form, same box, different position. | **Yes.** It is the existing form. |
| 10 (D-4) | HR picks the person with a search box, not a drop-down list. | Ritika types "Gee" and picks "Geeta Devi · no login". | **Yes.** A list of 445 names is unusable. |
| 11 (D-5) | "Tell him yourself" became "tell them yourself". | The first manager may be a woman. | **Yes.** |
| 12 (D-6) | Approvals happen on the Team page and Home card, not an Inbox. No "1 other person in this team is away" line. Buttons say Approve / Reject. | Ritika approves Manoj's leave from the Team page. | **Yes.** The portal has no Inbox page. Ask for the "other person away" line as a separate ticket if you want it. |
| 13 (D-7) | Badge says "Rejected", not "Declined", and a short pop-up message also appears. | After Reject: badge "Rejected" plus a toast. | **Yes.** It is the existing control. |
| 14 (D-8) | "Priya cancelled this request." shows as a short pop-up message, not a line in the row. | The row just disappears from the approver's list. | **Yes.** |

---

## Part 2 · Two drafts for you to approve

### Draft A · The HR notice

Sent when a leave is approved - Paid Leaves or Leave Without Pay. Desk bell, plus email if the HR user's settings allow it.

**Who gets it:** every HR Manager and HR User who looks after that employee. Not the person who approved. Not the employee. Once each, even if they are also a manager in the chain.

**Fixed fields only.** Name, dates, number of days. No free text anyone can type.

> **Subject:** Priya Sharma will be away on Fri 30 Oct
>
> Priya Sharma's leave for Fri 30 Oct (1 day) has been approved.
>
> You are told because you look after Priya's records in HR. There is nothing for you to do.

**It must never show:** the leave type, the reason, who approved, job title, leave class, days left, or anything about pay. So the same notice goes out for Paid Leaves and Leave Without Pay.

**Note:** at DTC, 7 HR users see the whole company. So each approval can send up to 6 HR bells. If that is too noisy, tell me who should get it.

### Draft B · "Leave encashed" for Housekeeping in the desk report

Housekeeping staff are paid by their agency. DTC never pays out their unused days.

**What the line should show:** **0**, with the "Why" note beside it. Leave earned and Leave used still show their real figures.

> Geeta Devi, October, 14 days present: Leave earned **2** · Leave used **1** · Leave encashed **0**
> Why: "Housekeeping table: 14 days present in a 31-day month gives 2. Reported to the agency; not paid by DTC."

**Why 0 and not blank:** a blank looks like missing data. 0 says plainly "DTC paid nothing".

**Reminder:** HR must not send this report to an agency. It holds other people's pay.

---

## Part 3 · Questions still open from the spec (section 19)

### Must answer before switch-on

| Question | Example | My recommendation |
|---|---|---|
| **Q-S1** How is Housekeeping kept out of DTC payroll? | October payroll: HR presses "Get Employees", then deletes 42 Housekeeping rows before making slips. | **HR deletes by hand, plus a check that no slip was made.** No code. If it is missed once, add a small code check. |
| **Q-S2** May HR see the figure when filing for someone? | Same as point 1 above. | **Yes.** |
| **Q-S3** HR notice wording | Draft A above. | **Yes, as drafted.** |
| **Q-S4** Yes or no to each difference in Part 1. | - | As listed in Part 1. |
| **Q-S7** Accept that 067's pay-slip marks wait for 063? | Both go on with one box. | **Accept.** A second switch is extra build for no clear need. |
| **Q-S10** Was the 25 Oct 14:41 DTC backup checked and copied off the server? | - | **Take a fresh backup on switch-on day anyway.** |

### Confirm the drawn default

| Question | Example | My recommendation |
|---|---|---|
| **Q-S5** "Leave encashed" for Housekeeping | Draft B above. | **0, with the Why note.** |
| **Q-S6** A Housekeeping person whose shift ends short with no leave: count it as 1 day present or 0.5? | Geeta works 3 of 8 hours, no leave filed. Counts 1 day today. | **1 day**, the same as office staff. |
| **Q-S8** Paid Leaves approved by the person's named leave approver, also for Housekeeping. | Geeta's Paid Leaves go to Sunil; her leave without pay goes to HR. | **Yes.** |
| **Q-S9** The top of the chain hears of every approved absence. | Kavita hears of every leave in her stores. | **Yes, as you asked.** |
| **Q-S11** "Remind HR" stays words only (no button); "To be paid out" shows under 15 days with its note; the chain notice as drawn. | Rohit at 10 days sees "To be paid out 4 - once you reach 15 days". | **Yes, as drawn.** |
| **Q-S12** Keep the name "Paid Leaves" for agency staff; show them Used and Waiting. | Geeta's card reads "Paid Leaves - October". | **Yes, yes.** |
| **Q-5** Open the seven side findings as separate YouTrack tickets? | e.g. other tenants never set a leave approver. | **Yes**, once you agree. |

*I am not a lawyer. Nothing here settles a legal question.*
