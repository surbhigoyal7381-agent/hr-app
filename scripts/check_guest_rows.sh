#!/usr/bin/env bash
#
# Can anyone on the internet list this site's staff or leads? Read-only. (Slice 082, OPS-30, AC-67.)
#
# A Guest permission row on User, Employee or CRM Lead lets a person with no login
# list those records - a link printed on an event poster would then publish the
# staff list. Slice 082 stops new rows (a Custom DocPerm validate hook); this
# check finds rows made before that hook existed.
#
# Two `select` statements. Nothing is changed. A row found is reported to Surbhi
# and removed only on her word.
#
# Runs inside a bench (it uses `bench --site <site> mariadb`):
#   docker exec -i <backend-container> bash -s <site> < scripts/check_guest_rows.sh
#   bash scripts/check_guest_rows.sh <site>        (from a bench directory)
#
# Prints PASS (no Guest row) or FAIL with the rows, then the roles that can read,
# export or share CRM Lead. Exit 0 = PASS, 1 = FAIL, 2 = the check itself failed
# (a zero from a failed command must never look like a clean zero).

set -uo pipefail
SITE=${1:?usage: check_guest_rows.sh <site>}
cd "${BENCH_DIR:-/home/frappe/frappe-bench}" 2>/dev/null || true

rows=$(bench --site "$SITE" mariadb <<'SQL' 2>&1
select 'GUESTROW', p.parent, p.permlevel, p.`select`, p.`read`, p.`report`, p.`export`, p.`share`
from `tabCustom DocPerm` p
where p.role = 'Guest' and p.parent in ('User', 'Employee', 'CRM Lead')
union all
select 'GUESTROW', p.parent, p.permlevel, p.`select`, p.`read`, p.`report`, p.`export`, p.`share`
from `tabDocPerm` p
where p.role = 'Guest' and p.parent in ('User', 'Employee', 'CRM Lead');
select 'CHECKED';
SQL
)
status=$?
if [ $status -ne 0 ] || ! printf '%s\n' "$rows" | grep -q '^CHECKED'; then
  echo "ERROR could not read the permission tables on $SITE - this is not a PASS"
  printf '%s\n' "$rows" | tail -3
  exit 2
fi

found=$(printf '%s\n' "$rows" | grep '^GUESTROW' || true)
if [ -n "$found" ]; then
  echo "FAIL  $SITE: Guest permission rows on User / Employee / CRM Lead:"
  printf '%s\n' "$found" | sed 's/^GUESTROW/      /'
  result=1
else
  echo "PASS  $SITE: no Guest row on User, Employee or CRM Lead"
  result=0
fi

echo "Roles that can read CRM Lead (role, read, export, share):"
bench --site "$SITE" mariadb <<'SQL' 2>/dev/null | sed '1d; s/^/      /'
select role, max(`read`), max(`export`), max(`share`) from (
  select role, `read`, `export`, `share` from `tabCustom DocPerm` where parent = 'CRM Lead'
  union all
  select role, `read`, `export`, `share` from `tabDocPerm` where parent = 'CRM Lead'
    and not exists (select 1 from `tabCustom DocPerm` c where c.parent = 'CRM Lead')
) perms where `read` = 1 group by role order by role;
SQL
exit $result
