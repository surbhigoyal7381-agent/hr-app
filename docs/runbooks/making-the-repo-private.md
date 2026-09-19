# Making the repository private

The repository is public on purpose: unlimited GitHub Actions minutes while there
are no customers. It must be private before the first one.

## What does not change

**GitHub Actions still works on a private repository.** The free allowance is 2,000
minutes a month, and the deploy job does not count against it at all — it runs on the
self-hosted runner on the server.

Measured usage, September 2026:

| Workflow | Runs on | Typical | Billed |
|---|---|---|---|
| CI | GitHub | 6–17 min | yes |
| Build Image | GitHub | 6–13 min | yes |
| Deploy | self-hosted | 14–33 min | **no** |

About 19 billable minutes per push to `dev` — roughly 100 pushes a month inside the
free allowance. There is no need to replace the workflows or build a separate deploy
mechanism.

## The one thing that breaks

**The server pulls the image anonymously**, and that works only while the ghcr.io
package is public.

That is worse than it sounds. The image contains the whole application, so a public
package means anyone can `docker pull` it and read the source — a private repository
alone would not hide the code.

So the package has to go private too, and the deploy has to sign in. The
`Sign in to the image registry` step in `deploy.yml` does that, using the job's own
`GITHUB_TOKEN`. No long-lived token sits on the server and nothing needs rotating.

## The second thing that breaks — found the hard way

The first version of this runbook covered the image and missed that **the server also
fetches the code itself**, twice per deploy, over HTTPS with no stored credentials.
The repository went private on 18 September before that was fixed, and the next deploy
died at its first step:

```
fatal: could not read Username for 'https://github.com': No such device or address
exit code 128
```

Nothing on the server was touched — the nginx gate ran first and caught it. Both
fetches now carry the job's `GITHUB_TOKEN` in a header, passed through `env:` so it
never appears in a log or a process list. The server still holds no credential, and
that is deliberate. **Do not "fix" a future fetch failure by storing one there.**

## The trap: the automatic deploy runs `main`'s copy of the workflow

The Deploy workflow fires off `workflow_run`. GitHub executes that kind of trigger
**from the workflow file on the default branch (`main`)**, whatever branch is being
deployed. So a fix to `deploy.yml` on `dev` changes nothing until it reaches `main`.

On 18 September the git-login fix was on `dev` and the automatic deploy failed twice,
identically. It went through only when triggered by hand with
`gh workflow run Deploy --ref dev`, which uses `dev`'s copy.

Two consequences, both of which bit:

1. **Every automatic dev deploy keeps failing until the fix reaches `main`.** Trigger by
   hand with `--ref dev` in the meantime.
2. **A push to `main` runs `main`'s OLD workflow** — no git login, no registry login,
   no nginx parse gate, no dev backup. The production release therefore cannot be
   "push to main and watch". It has to land the workflow change on `main` first, by
   hand-triggered deploy, and only then release the application.

## Order of operations

**Get both sign-in steps onto `main` before making the package private.** In the other
order, the first deploy after the switch fails at the pull, and the site is mid-deploy
when it happens.

1. Release the `deploy.yml` change to `dev`. Deploy by hand: `gh workflow run Deploy
   --ref dev` (the automatic one will fail — see the trap above). Confirm both
   `Sign in to the image registry` and the git fetch pass. *(Done 18 Sep: both passed
   on their first real run.)*
2. Get the same `deploy.yml` onto `main`, and run one deploy from it.
3. Repository → Settings → **Change visibility → Private**. *(Done 18 Sep — out of
   order, which is what produced the failure above. No harm, because the package was
   still public.)*
4. Packages → the `hr-app` package → Package settings → **Change visibility →
   Private**. **Not before step 2.**
5. Push a trivial commit to `dev` and watch a full deploy through.

## If the minutes ever run short

Move the `ci` and `build-image` jobs to the self-hosted runner by changing
`runs-on: ubuntu-latest` to `runs-on: [self-hosted, contabo]`. Self-hosted minutes are
unlimited.

**Do this only if the allowance is genuinely being hit.** Tests on the production host
compete with the live site for memory, and a hostile dependency pulled in during CI
would be running on the machine customers use. The free allowance is the safer place
for that work while it fits.

## Also remember

Everything committed while the repository was public should be treated as already
copied. Going private hides what happens next; it does not retrieve what is out there.
GitHub traffic for the first half of September showed 713 clones from 190 unique
sources.
