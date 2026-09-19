---
slice: 002-ess-home-redesign
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-09
status: ready
inputs: [conversation 2026-09-09]
supersedes: earlier draft of 2026-09-09 which read "minimalist" as "show fewer things"
---

# A quieter visual system, and a home page that knows who is looking

## The job, in the user's words

> "Make our Employee Self Service page design much more minimalist and space
> should be optimally utilized. Considering the expectations of the key personas
> of this application rearrange the information on the home page and add more
> widgets that makes sense, such as policy documents, weekly look of attendance
> of people relevant to the login user such as department members, his own
> reporting team etc."

Clarified on 9 September:

> "more minimalistic means minimalistic design, having less colors making it
> look more professional and elegant, yet the space utilization should be
> better."

**Correction to the first draft of this brief.** It read "minimalist" as *show
fewer things* and proposed a slice that was mostly deletion. That was wrong.
The ask is about **how the product looks**: fewer colours, more elegant, more
professional — while fitting *more* into the same space, not less.

That flips one conclusion completely. The first draft said "kill this slice if
it turns into a theme change". A disciplined visual system is now the main
event.

So there are two workstreams, and they should ship in this order:

1. **The visual system** — fewer colours, one type scale, consistent surfaces.
   Elegance and professionalism come from restraint and repetition.
2. **The information architecture** — what goes on the home page, per persona,
   and the new widgets.

One first, because rearranging a page while its visual language is still
changing means doing the layout twice.

## Decisions taken (9 September 2026)

| # | Question | Decision |
|---|---|---|
| 1 | Priority persona for the home page | **Employee first, manager second.** Most numerous, most likely to give up on it |
| 2 | Ship the redesign behind a switch, or to everyone? | **Everyone at once.** No per-tenant rollout switch |
| 3 | Paid feature or base product? | **Base product** |
| 4 | Is this specific to PP Jewellers? | **No.** Every tenant, whatever their data looks like |
| 5 | Keep the purple `#5B4B8A` as the single accent? | **Yes.** The brand stays. This is about discipline, not identity |
| 6 | Gradients | **Remove them all.** Flat colour only |

Decision 2 raises the stakes rather than lowering them. There is no way to turn
this off for one customer if it lands badly, and no way to compare the new page
against the old one on a real tenant. That makes two things non-negotiable:

- **Phase one ships alone**, with every screen walked before and after. It is
  the change that touches all thirteen panels.
- **A rollback is a redeploy of the previous image.** That is the only undo, so
  the change must be one commit that can be reverted cleanly, not a fortnight of
  small edits mixed in with feature work.

Decision 4 has a practical edge here too: the home page must look deliberate on
a tenant with four employees, no branches and no goals cycle running — not just
on a full one.

## The pain, measured

I counted what is actually in the portal page today. This is the case for the
work, and it is not a matter of taste:

| Thing | Today | What a designed system uses |
|---|---|---|
| Distinct hex colours | **120** | 10 – 14 |
| Font sizes | **29** | 6 – 7 |
| Corner radii | **16** | 2 – 3 |
| Distinct shadows | **43** | 2 – 3 |
| Emoji used as interface icons | **135 uses, 49 different** | 0 |

Some specifics behind those numbers:

- **Three different greens** are in use for "good" — `#43a047`, `#16a373`,
  `#3a9899` — plus three pale green backgrounds. Four reds for "bad". The eye
  reads inconsistent colour as carelessness even when it cannot name why.
- **Emoji as icons.** The HR Analytics cards are labelled with 🧑‍💼 🆕 📅 📋 🎓
  🌴. Emoji render differently on every operating system, cannot be recoloured,
  and are the single strongest signal that a screen was assembled rather than
  designed. Nothing else on this list costs more credibility with a CXO.
- **Font sizes from 8px to 52px in 29 steps**, including 9.5, 10.5, 11.5, 12.5
  and 13.5. Half-pixel steps are not a decision anybody made; they accumulated.
- **Colour used as the only signal** in several places, which is also an
  accessibility problem — about one man in twelve cannot separate the red from
  the amber.

For honesty: **the org chart work I shipped last week added three more colours**
to that pile — a rose, an amber and a blue for the flag severities. Correct in
isolation, more entropy in aggregate. That is exactly how a page reaches 120
colours: every change is individually reasonable.

## Correction: the empty column that was not empty

An earlier version of this brief claimed the home grid reserved a 300px column
that nothing used, and that a third of the page was therefore wasted. **That was
wrong.** The grid has two columns and both are populated: `home-left-col` at
938px and `home-actions-col` at 300px, the latter holding approvals, holidays
and documents.

The claim was made from a grep rather than from the rendered page, and building
to it added a third column that wrapped below the fold, with the new week widget
squeezed into the narrow one where seven days of five people cannot fit. Found
by rendering the page and looking at it, which is the only way it could have
been found.

The space still improved, but by the honest route: blocks that have nothing to
say are no longer drawn, and the type scale and flat surfaces give back the
room that decoration was using.

## What "better space utilisation" means here

Not smaller text and tighter margins. It means **more answer per square inch**:

- Today the analytics KPI cards are large tiles with a big emoji, a big number
  and a caption. Six of them fill a laptop screen and carry six numbers.
- The same area, set as a quiet data row, carries the same six numbers plus the
  trend on each, and leaves room for the chart underneath.

Density comes from removing decoration, not from shrinking content. Every pixel
spent on a shadow, a rounded corner or an emoji is a pixel not spent on an
answer.

## The design direction

A payroll and attendance product is read by people doing careful work with other
people's money and time. It should feel like a well-set financial document, not
like a consumer app.

Proposed, for your approval before anything is built:

**Colour — one accent, three states, ten neutrals.**
Keep the existing purple `#5B4B8A` as the single brand accent, used sparingly:
the active nav item, primary buttons, focus rings. Nothing else is purple.
Three semantic colours only — one positive, one warning, one negative — each
with exactly one text shade and one background shade. Everything else is a
neutral grey, slightly warm to sit with the existing cream background. That is
about twelve values, replacing 120.

**Type — one family, seven steps.**
The page already reaches for Inter. Set a real scale (roughly 11 / 12 / 13 / 15
/ 18 / 24 / 32) and delete the rest. Numbers get `tabular-nums` everywhere they
line up in a column, which is most of this product.

**No gradients.** Seven `linear-gradient` declarations are in the page today.
All of them go. A gradient is decoration that changes the colour of the thing
underneath it, so it defeats a token system: the value is no longer one value.
It is also the fastest way to make a professional tool look like a consumer app.
Flat colour throughout, including the buttons and the sidebar.

**Surfaces — flatter.**
One radius for cards, one for controls, one for pills. One shadow, used only
where something genuinely floats — dialogs and dropdowns. Cards separated by a
hairline border and whitespace instead of by a shadow. This alone makes a page
look calmer than any other single change.

**Icons — a real set, not emoji.**
The portal already uses inline SVG for the sidebar. Extend that. One weight, one
size, `currentColor` so they inherit the text colour and work in both themes.

**Both themes stay.** The portal has a dark mode today and it must keep working.
Colours get defined once as tokens and the dark theme redefines the tokens only
— which is also what stops the two drifting apart.

## The WOW moment

Two of them, one per workstream.

**Design:** somebody who used the portal last month opens it and cannot say what
changed, only that it looks like a more expensive product. That is what a
consistent system does — it is invisible and it reads as competence.

**Home page:** an employee and their manager open the same page and each sees a
page that looks made for them. The employee sees check-in, leave balance, the
week's team attendance and the next holiday. The manager sees check-in, three
approvals as a list they can act on, who is out this week, and one line on team
attendance. Same page, different four things, no scrolling for either.

## The personas, and what each opens the portal to do

**Employee** — most days, for under a minute. *Am I marked in? How much leave do
I have? Has my request been approved?* Rarely wants a chart.

**Manager** — a few times a week. *Who is out today? What needs my approval? Is
anybody drifting?* Today each of those is a different screen.

**HR Manager** — lives in the portal. *What is waiting for me? Who joins this
week? Which numbers moved?* The persona the current home page serves worst,
because their work is approvals and exceptions and neither is on it.

**CXO** — rarely, and judges the product by what they see. For them the home
page is a credibility test more than a tool. This is the persona the visual
workstream is really for.

## What the home page shows today, and what is missing

Today: check-in with a live clock · activity feed · my goals · team goals ·
a "needs your attention" banner with a count.

Missing, by name:

1. **Policy documents** — the screen exists; nothing points at it. New joiners
   do not know it is there.
2. **This week's attendance for people relevant to me** — my team if I manage
   one, otherwise my department. Exists nowhere in the product.
3. **My leave balance** — the most common employee question, currently two
   clicks away.
4. **What is waiting for me** — approvals are a count in a banner, not a list
   you can act on.
5. **Who is out today** — what a manager checks before planning a shift.

## The thin slice

**Phase one — the design system.** Tokens defined once; the 120 colours, 29 font
sizes, 16 radii and 43 shadows collapsed onto them; emoji replaced with SVG.
No layout changes, no new features. Ships and is judged on its own, and it
touches every screen, so it is the riskiest change in this brief and deserves to
travel alone.

**Phase two — blocks that earn their place.** A block appears only when it has
something to say. No goals cycle running, no goals block — not a block with a
dash in it. This is where "better space utilisation" becomes real, because the
space freed is spent on the widgets below.

**Phase three — the four new widgets.**

| Block | Who sees it | The question it answers |
|---|---|---|
| Leave balance | Everyone | "How much leave do I have left?" |
| This week's attendance | Manager → their team; everyone else → their department | "Who is in this week?" |
| Waiting for you | Anyone with something pending | "What needs me, and can I act here?" |
| Policies | Everyone; prominent for the first 30 days after joining | "Where is the leave policy?" |

**The attendance widget shows presence only.** In, out, on leave, not yet in —
never the reason, never a running tally, never the leave type. Absence can
reveal a pregnancy, a diagnosis or a family crisis, and a colleague has no
business inferring any of it from a home page. A manager's analytics view may go
further because they have a duty of care; a peer's must not. This is a rule for
the endpoint, not a decision for the front end.

**Phase four — layout.** Last, because arranging blocks whose look and existence
are still changing is doing the work twice.

## Out of scope

Drag-and-drop dashboards · a widget marketplace · per-tenant home page
configuration · a mobile app · changing the brand colour itself · any screen
other than home in phases two to four.

Per-tenant configuration deserves a note: it is the obvious next request and it
should be resisted. Every customer configuring their own home page means we stop
learning what a good default is, and we need a good default far more than we
need a settings screen.

## Success measures

| Measure | Baseline | Target | How we will know |
|---|---|---|---|
| Distinct hex colours in the page | **120** | Under 15 | Count in the file |
| Font sizes | **29** | 7 | Count in the file |
| Distinct shadows | **43** | 3 | Count in the file |
| Emoji used as icons | **135** | 0 | Count in the file |
| Gradients | **7** | 0 | Count in the file |
| Blocks shown to a plain employee | 5, several empty | 4, all populated | A test account |
| Clicks to leave balance | 2 | 0 — on the page | Walk the path |
| Page height, 1366×768 | Measure first | No scrolling, any persona | Screenshot per persona |
| Home page load | Measure first | No slower | Timing on PPJ |

The first four are objective and can be checked automatically. That matters:
"looks more professional" is otherwise an argument nobody can win, and it is
exactly the kind of goal that quietly gets dropped.

## Thriving-workplace check

- **Engagement** — A page that knows who you are is the cheapest signal that a
  product was built for you.
- **Collaboration** — The team attendance block is the genuinely new
  collaborative surface. Knowing who is in this week is what a manager currently
  asks a group chat.
- **Inclusiveness** — Two real gains and one real risk. Gains: fewer colours
  with proper contrast, and never colour as the only signal, helps colour-blind
  users and anyone on a poor screen. Risk: a team attendance block shows absence
  patterns to colleagues, and absence can reveal health or caring
  circumstances. Show **who is in or out**, never **why**, and never a running
  absence tally to peers. A manager's view may go further; a peer's must not.
- **Transparency** — Policies on the home page make the rules easier to find
  than to be told.

## Risks and kill criteria

| Risk | What we do about it |
|---|---|
| A design pass breaks the other twelve screens | Tokens first, then replace values one group at a time. Every screen walked before and after. This is why phase one ships alone |
| "Elegant" becomes a matter of taste and stalls | The four counted measures above settle it objectively |
| Dark mode breaks | Colours defined once as tokens; dark redefines tokens only, never component rules |
| The page ends up busier | Phase two is conditional blocks, and it ships before any widget is added |
| Team attendance leaks personal data to peers | In or out only. No reasons, no totals, no leave types. Tested in the endpoint, not the page |
| **The file gets damaged** | Every panel lives in one 15,000-line HTML page. On 9 September a script matching an ambiguous anchor deleted 2,760 lines of it — whole unrelated panels — caught only because the diff was read line by line. Every edit anchors on a string that matches exactly once, and panel count is checked before and after |

**Kill this slice if:** it becomes a rebrand. The brand colour stays. This is
about using one accent with discipline instead of 120 without it. Changing the
brand is a different conversation with a different owner.

---

## Open questions

1. **When somebody has no team, is a department view acceptable?** (owner:
   Surbhi) — In a 400-person store chain a department can be large. May need to
   fall back to branch or shift. Does not block phase one.
2. **Is a "first 30 days" state worth building for new joiners?** (owner:
   Surbhi) — The highest-value personalisation on the page, and the most work.
   Can be deferred without harming the rest.

Settled on 9 September: the purple stays as the single accent; all gradients go;
a colleague sees only whether somebody is in or out, never why.

## Assumptions

- `[ASSUMPTION]` "Role" means the Designation field, not a Frappe permission
  role — matching slice 001.
- `[ASSUMPTION]` The sidebar and the other twelve panels keep their structure.
  Phase one changes how they look, not what they contain.
- `[ASSUMPTION]` The weekly attendance widget reads the same numbers as slice
  001. If both ship, they share one calculation — two would diverge, and then
  neither is trusted.
- `[ASSUMPTION]` Desktop first, but the page must not break on a phone. Many
  PP Jewellers store staff will only ever open it on one, so "optimal use of
  space" means two layouts, not one compromise.

## Handoff note

To the business analyst: the two workstreams need different kinds of spec.

The **design system** is a specification of values, not behaviour: the token
list, what each token is for, and the mapping from every current value to its
replacement. Write that mapping out in full. A design pass done by judgement,
file by file, is how a page reaches 120 colours in the first place. It should
end with a check that can run automatically and count what is in the file,
because that is the only way this stays fixed after the next feature lands.

The **home page** spec should resist starting with the layout. That is the fun
decision and everybody wants to make it first. Specify the **rules for whether
each block appears** and **who may see what inside it**; the layout falls out of
how many blocks a persona ends up with.

Note the ordering dependency with slice 001: the team attendance widget and the
analytics screen answer the same question at different depths. Build the
calculation once in slice 001 and have this widget call it. If this slice ships
first, call `numbers_for_many()` directly rather than growing a second sum.
