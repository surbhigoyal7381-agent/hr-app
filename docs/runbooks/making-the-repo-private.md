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

## Order of operations

**Get the sign-in step onto `main` before making the package private.** In the other
order, the first deploy after the switch fails with `unauthorized` at the pull, and
the site is mid-deploy when it happens.

1. Release the `deploy.yml` change to `dev`, then to `main`.
2. Run one deploy to each and confirm the sign-in step passes.
3. Repository → Settings → **Change visibility → Private**.
4. Packages → the `hr-app` package → Package settings → **Change visibility →
   Private**.
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
