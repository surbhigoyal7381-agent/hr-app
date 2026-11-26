# ALV-478: pay the next overtime band after a set percent of the window

Surbhi, 26 Nov 2026. Built locally on branch `fix/alv478-ot-next-band-percent`. Not pushed.

## The rule

One new setting on the Alvoraa Payroll Rule Set, under the overtime bands: **Pay The Next Overtime Band After (%)**.
A whole number from 1 to 100. Blank or 100 means today's behaviour: a band pays only at its own time.

Once the last punch has reached a band, a person who has gone at least this percent of the way from that band's
time to the NEXT band's time is paid the next band. Nothing is paid before the first band (23:00 on DTC), and the
last band is the cap. The shift end + 1 hour gate is unchanged.

## At 75% on DTC (bands 23:00 = 1, 01:00 = 2, 03:00 = 4)

| Last punch | Paid |
|---|---|
| 22:59 | 0 |
| 23:00, 23:42, 00:29 | 1 quarter |
| 00:30, 00:35, 01:50 | 2 quarters |
| 02:30, 02:40, 03:30 | 4 quarters |

The brief's example of 23:42 paying 2 quarters was wrong. It is 1 (corrected in the brief).

## Decisions

- **Rounding:** none. Minutes are counted from the shift day's midnight (01:00 next morning is 1500, ALV-402) and the test is whole-number: `(last punch - band) x 100 >= percent x window`. 75% of the 120 minutes from 23:00 to 01:00 is exactly 00:30, and 00:30 pays the next band (at or past, the same "milestone passed" rule as the bands).
- **Field type is Data, not Int or Percent.** An Int or Percent field turns blank into 0 and 75.5 into 75, so a save could not refuse 0 or 75.5. The save refuses anything but a whole number 1 to 100 or blank, in plain words.
- **One path.** `payroll_rules_apply.prepare()` reads the setting (as it reads the bands), `judge()` hands it to `evaluate_day`, which hands it to `overtime_quarters_for`. That is the only caller of each (grep). Daily Workings, Salary Workings and `payroll_month` read the verdict's `overtime_quarters`, so they follow with no change of their own. The day card has no overtime code.
- Bands typed in any order still work (sorted inside).

## After release (data, on Surbhi's word)

On dtc.alvoraa.co and ppj.dev: Desk > Alvoraa Payroll Rule Set > Overtime By Last Punch > set
"Pay The Next Overtime Band After (%)" to 75, and save. The release needs `bench migrate` to add the field.
Until then nothing changes anywhere. Re-run any month already judged if it should use the new rule.
