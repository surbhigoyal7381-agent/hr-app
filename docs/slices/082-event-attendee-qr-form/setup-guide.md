# Event QR form: setup guide

For the **organiser manager**: a person at the organiser with the Sales Manager role. Some
steps need a **System Manager**, and the guide says so where they do.

What you get: one phone form per event. People at the event scan a QR code, fill the form on
their own phone and press Send. Each answer becomes one CRM lead, marked with the event it
came from. Nobody at the door needs a login.

---

## 1. Before your first event (once)

**Do not use this form for events with people under 18.** The notice says the form is for
people aged 18 or over.

The five event fields are already on CRM leads: **Event form**, **Event rating**, **Event
comment**, **Consent: this event** and **News OK**. You do not create them.

### Extra questions (System Manager only)

If an event needs a question that is not on the lead (for example "Your shop name"), a
**System Manager** adds it once, for all events:

1. Desk → **Customize Form** → CRM Lead → add a row.
2. Give it a plain label, bilingual if you like: "Your shop name (optional) / आपकी दुकान का नाम (वैकल्पिक)".
3. Use only these types: **Data, Phone, Small Text, Text, Long Text, Int, Float, Select,
   Check, Date**. Any other type (a list of your staff, a file upload, a rich-text box, a
   time, money, a colour) stops the form from opening.
4. Save. CRM's form builder now offers the question.

**Never ask for sensitive data.** No Aadhaar, PAN, passport, voter ID, bank or IFSC details,
account numbers, health, disability, religion, caste or sexual life. The page refuses to open
a form whose question names any of these. That check is a safety belt, not a licence: if you
find yourself rewording a question to get past it, do not ask the question.

To retire a question, tick **Hidden** on its field. Old answers stay. A form that still
lists a hidden question will not open until you remove it from the form.

---

## 2. Build the form for an event

1. CRM → **Settings → Forms → New**.
2. **Title = the event's name and date**, for example "Pune Dealer Meet, 14 Nov". The title
   is the event: it appears on the page, on the QR card and in the thank-you message.
3. Choose **CRM Lead** as the record type.
4. Add these seven questions, in this order. This is the default form; add an extra question
   only if you will act on its answer.

   | Question on the lead | Label to type (example) | Needed? |
   |---|---|---|
   | First name | Your name / आपका नाम | Yes |
   | Mobile no | Mobile number / मोबाइल नंबर | Yes |
   | Email | Email (optional) / ईमेल (वैकल्पिक) | No |
   | Event rating | How was the event? (optional) / कार्यक्रम कैसा रहा? (वैकल्पिक) | No |
   | Event comment | Anything you want to tell us? (optional) / कुछ और बताना चाहें? (वैकल्पिक) | No |
   | Consent: this event | I agree that <organiser> keeps these details to follow up on this event. / मैं सहमत हूँ… | **Yes** |
   | News OK | Send me news of future events. (optional) / मुझे आगे के कार्यक्रमों की जानकारी भेजें। (वैकल्पिक) | No |

   **Do not add "Lead type"** to an event form. Each answer could then start your sales steps
   and send an email per attendee.

   Keep it short: **five extra questions at most.** In a hall, most people stop after about five.

5. **Write the notice** in the *description* of the "I agree" question. The form will not open
   without it. Template, English then Hindi:

   > Collected by **<organiser>** for **<event>**. We keep your details for 6 months after the
   > event, and in backups until they age out. If you tick "Send me news", we keep your contact
   > until you ask us to stop. To see or remove your details: **<organiser's email>**. For
   > people aged 18 or over.
   >
   > **<organiser>** यह जानकारी **<event>** के लिए ले रहा है। कार्यक्रम के 6 महीने बाद तक रखी
   > जाएगी। "आगे की जानकारी" पर टिक करने पर, जब तक आप मना न करें। देखने या हटवाने के लिए:
   > **<organiser's email>**। केवल 18 वर्ष या उससे अधिक के लोगों के लिए।

   ⚠ The retention period and the backup line wait for counsel. Use the wording you are given.

6. Set the **button label** ("Send my details / जानकारी भेजें") and, if you like, a
   **success message**. Leave the success message empty and the page says "Thank you. Your
   details are saved for <event>." in English and Hindi.
7. **Publish.**

---

## 3. Test it from your own phone, then print

1. Open `https://<your site>/event-form/<the form's route>` while signed in. You see a yellow
   box: "You are signed in as an organiser. Attendees do not see this box."
2. If the box says the form **cannot open for attendees yet**, it names the problem. Fix it in
   CRM and open the page again.
3. On your phone, **not signed in**, fill the form once and press Send. Check the lead in CRM.
   Delete it afterwards.
4. Back on the signed-in page, press **Download QR card**, then **Download PNG**. Print it at
   A6 or larger. The card shows your site's address in plain text: check it is your live
   address, not a test one, before you print.

**Never rename the site once QR codes are in print.** Every printed code would stop working.

**Staff phones:** if a staff member fills the form for someone on a shared phone and the send
fails, **reload the page** before the next person, or they will see the last person's answers.

---

## 4. After the event

1. **Unpublish** the form when you stop taking answers. The link then shows "This form is not
   taking answers" in English and Hindi. Published again later, the same QR works again.
2. Call the unhappy people first, using the views below.

### The saved views (create once, then pin)

Create each one in **CRM → Leads**: set the filters, sort, columns or group-by, then **Save as
new view**, name it exactly as below, and **pin** it.

**"<Event> – lowest first"** (one per event, for example "Pune Dealer Meet – lowest first")

- Filters: **Event form** = your event's form; **Event rating** *is set*.
- Sort: **Event rating** ascending, then **Created on** ascending.
- Columns: Name, Event rating, Event comment, Mobile no, News OK, Created on, Assigned to.

The rating reads "1 · Very poor" on purpose: the number at the front makes "lowest first" a
plain sort. Assign each 1 and 2 to a sales person with CRM's own **Assign to**.

**"Events – entries per form"**

- Filter: **Event form** *is set*. Group by: **Event form**. A count per event.

**"<Event> – answers"** (only for an event with extra questions)

- Filter: **Event form** = that form. Columns: the extra questions. Sort by the one you act
  on, for example *Shops, descending*.

**Deleting old entries.** Six months after an event, open its leads (filter **Event form** =
that form, **News OK** *not ticked*), select them and Delete. Do one event at a time: very
large deletions run in the background and can stop part-way.

A saved view is a convenience, not a lock. Who can see leads is decided by CRM's roles:
Sales Managers see all leads; a Sales User sees only leads they own or are assigned.

---

## 5. When someone asks

- **"Stop sending me news."** Open their lead and untick **News OK**. CRM records who and when.
  Only email people whose lead has News OK ticked.
- **"Delete my details."** Delete their lead. Its history copies are removed with it.
- **"What did you collect?"** Open their lead; everything they gave is on it.

Do not tick News OK for anyone yourself. Only the person can say yes.
