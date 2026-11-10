# App-owned publication contract; common engine: BaseCentral deploy 1.0.0.
# Deployment is a separate, explicit action. The destination below is a default,
# not an authorization to publish.
APP_ID=lexi
SOURCE_SUBDIR=.
DEFAULT_DESTINATION="${DEPLOY_SITE:-$HOME/lexi.basecentral.link}"
DEPLOY_URL=https://lexi.basecentral.link
PUBLIC_FILES=$(cat <<'PUBLIC_FILES'
index.html
style.css
app.js
conversation.js
editorial.js
i18n.js
missing.html
missing.js
credits.html
version.js
sw.js
manifest.webmanifest
ATTRIBUTION.md
LICENSE
icons/icon-180.png
icons/icon-192.png
icons/icon-512.png
icons/icon.svg
icons/mark.svg
images/manifest.json
data/meta.json
data/regional.json
data/forms-meta.json
data/missing-meta.json
data/_.json
data/a.json
data/b.json
data/c.json
data/d.json
data/e.json
data/f.json
data/g.json
data/h.json
data/i.json
data/j.json
data/k.json
data/l.json
data/m.json
data/n.json
data/o.json
data/p.json
data/q.json
data/r.json
data/s.json
data/t.json
data/u.json
data/v.json
data/w.json
data/x.json
data/y.json
data/z.json
data/forms/_.json
data/forms/a.json
data/forms/b.json
data/forms/c.json
data/forms/d.json
data/forms/e.json
data/forms/f.json
data/forms/g.json
data/forms/h.json
data/forms/i.json
data/forms/j.json
data/forms/k.json
data/forms/l.json
data/forms/m.json
data/forms/n.json
data/forms/o.json
data/forms/p.json
data/forms/q.json
data/forms/r.json
data/forms/s.json
data/forms/t.json
data/forms/u.json
data/forms/v.json
data/forms/w.json
data/forms/x.json
data/forms/y.json
data/forms/z.json
data/missing/_.json
data/missing/a.json
data/missing/b.json
data/missing/c.json
data/missing/d.json
data/missing/e.json
data/missing/f.json
data/missing/g.json
data/missing/h.json
data/missing/i.json
data/missing/j.json
data/missing/k.json
data/missing/l.json
data/missing/m.json
data/missing/n.json
data/missing/o.json
data/missing/p.json
data/missing/q.json
data/missing/r.json
data/missing/s.json
data/missing/t.json
data/missing/u.json
data/missing/v.json
data/missing/w.json
data/missing/x.json
data/missing/y.json
data/missing/z.json
docs/missing-lemmas.csv
docs/missing-lemmas.json
docs/CORPUS.md
docs/SOURCES.md
PUBLIC_FILES
)

# Illustrations are enumerated from the checkout when the profile loads. A
# release must publish every local file the manifest and the app reference:
# leaving images/ out of the allowlist produced a site whose service worker
# could not install and whose credits page returned 404. Adding a reviewed
# image therefore needs no second allowlist edit, and the deploy engine still
# rejects any file that is not tracked by Git.
for illustration in "${DEPLOY_CHECKOUT:-}"/images/*.jpg; do
 [[ -f "$illustration" ]] || continue
 PUBLIC_FILES="$PUBLIC_FILES
images/$(basename -- "$illustration")"
done

# Fail closed before staging: the service worker must only precache published
# files, and every published path must exist.
deploy_validate(){
 local root=$1
 command -v python3 >/dev/null || deploy_fail 'python3 is required for the publication check.'
 printf '%s\n' "$PUBLIC_FILES" | python3 "$root/scripts/check_publish.py" "$root" --files - || deploy_fail 'Publication inventory check failed.'
}
