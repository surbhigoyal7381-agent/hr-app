# Client onboarding form

What we ask a new customer for before building their tenant.

`client-onboarding-form.html` is the source. `Client-Onboarding-Form.pdf` is what we
send them.

## Regenerating the PDF

Any Chromium browser will do it:

```
msedge --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=docs/product/onboarding/Client-Onboarding-Form.pdf \
  docs/product/onboarding/client-onboarding-form.html
```

## What it asks for, and why

Sections A to D are the fields `tenant_api.create_tenant` and
`tenant_setup.complete_company_setup` actually take. **If those signatures change, the
form goes stale** — in particular the feature tick-list in Section C, which mirrors
`subscription.FEATURES`.

Sections E to H are not needed to create a tenant, only to make it usable: working
time and leave, payroll and statutory numbers, the staff spreadsheet, and the privacy
decisions.

Section H exists because the customer is the data fiduciary and we are the processor.
It collects the GPS consent decision **before** anyone is tracked, and names who may
see location records. See `docs/product/legal/`.

Section B states that we never send passwords by email. That is a commitment, and the
product does not honour it yet — see `docs/runbooks/email-sending.md`.

## Branding

Currently All About HR colours, with the wordmark drawn in CSS rather than an image
file. Swap in the real logo when there is one in the repo.
