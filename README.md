# Heathrow Food Hygiene Scoreboard

A self-updating scoreboard of food hygiene ratings for the Heathrow hotels and
eateries you choose, plus a small live badge you can drop onto each review page.
All data comes **live from the Food Standards Agency (FSA)** - nothing is typed
in or stored by hand.

There are two things you can show on your site:

1. **The scoreboard** (`widget.html`) - a sortable, filterable table of all your
   venues.
2. **The per-review badge** (`badge.html`) - one venue's rating, shown on its own
   hotel/restaurant page, fetched live from the FSA every time the page loads.

---

## What's in this folder

| File | What it is |
|------|------------|
| `venues.csv` | **You edit this.** The list of venues to show (name, postcode, group). |
| `config.py` | Settings (file names, attribution wording). Rarely needs editing. |
| `resolve.py` | Run once to turn your list into stable FSA IDs (`venues.json`). |
| `fetch.py` | Run on a schedule to refresh the live ratings (`data.json`). |
| `widget.html` | The embeddable scoreboard table. |
| `badge.html` | The live single-venue badge for review pages. |
| `images/` | The official FSA rating badges (see `images/README.txt`). |
| `.github/workflows/refresh.yml` | Runs `fetch.py` automatically every day. |
| `venues.json` / `data.json` | Generated files - you don't edit these. |

You need **Python 3** installed to run the two scripts. No extra packages, no API
key, no sign-up.

---

## Quick start

From inside this folder, in Terminal:

```bash
python3 resolve.py     # find the FSA ID for each venue in venues.csv
python3 fetch.py       # pull the live ratings into data.json
```

Then open `widget.html` through a web address (see **Putting it on your site**).
That's it.

---

## How to add or remove a venue

1. Open **`venues.csv`** in any text editor or Excel.
2. Add or delete a line. Each line is:

   ```
   name,postcode,group
   ```

   - **name** - roughly as it appears on the FSA site.
   - **postcode** - the venue's postcode (this is what locks onto the right record).
   - **group** - optional label to filter/sort by, e.g. `Hotel`, `Hotel restaurant`,
     `Eatery`, or a terminal like `Terminal 5`.

3. Save, then run:

   ```bash
   python3 resolve.py
   python3 fetch.py
   ```

### Catching a hotel's own restaurant

Some hotels have their restaurant rated **separately** from the hotel. When you run
`resolve.py`, it lists any other food businesses found at the same postcode, e.g.:

```
[ 3/40] OK   Sofitel London Heathrow -> FHRSID 519347 (Sofitel London Heathrow)
      also at TW6 2GD: Sphere Bar & Restaurant [FHRSID 512345, Restaurant/Cafe/Canteen]
```

If you want that restaurant on the board too, just copy its name and postcode onto a
new line in `venues.csv` and re-run.

### When something doesn't match

If a venue can't be matched cleanly, `resolve.py` **flags it at the end** and lists the
likely candidates with their FSA IDs. Fix the name or postcode in `venues.csv` and
re-run, or note the correct details by hand. A flagged venue is simply left off until
it resolves - it never breaks the board.

---

## Putting the scoreboard on your site (XenForo)

The widget needs to be served from a web address (opening the file directly won't let
it load the data). The easiest free option is **GitHub Pages**: put this folder in a
GitHub repo and turn Pages on. You then have a URL like
`https://YOURNAME.github.io/heathrow-hygiene/widget.html`.

Embed it in a XenForo page with an iframe:

```html
<iframe src="https://YOURNAME.github.io/heathrow-hygiene/widget.html"
        style="width:100%;height:1200px;border:0"></iframe>
```

Or, if your XenForo setup allows raw HTML, paste the contents of `widget.html`
directly and make sure `data.json` and `images/` are reachable from the same place.

> **Tip:** if you host `data.json` somewhere else, open `widget.html` and set
> `DATA_URL` (top of the script) to its full `https://...` address.

---

## Adding a live badge to a hotel/restaurant review page

1. Run `resolve.py` - it prints (and saves in `venues.json`) the **FHRSID** for each
   venue. That number is all you need.
2. In `badge.html`, set `IMG_BASE` to the full web address of your `images/` folder,
   e.g. `https://beyondtheairport.com/heathrow-hygiene/images/`.
3. Paste the badge's `<style>` and `<script>` once into the review page (or your
   XenForo template), then add one line where you want the badge:

   ```html
   <div class="fsa-rating" data-fhrsid="519347"></div>
   ```

   (519347 is the Sofitel, as an example.) The badge fetches that venue's rating
   straight from the FSA on every page load, so it is always current.

---

## Scheduling the daily refresh (no server needed)

`.github/workflows/refresh.yml` runs `fetch.py` automatically once a day on GitHub's
free infrastructure and commits the updated `data.json`.

To switch it on:

1. Put this folder in a GitHub repository.
2. Run `resolve.py` locally once and commit `venues.json`.
3. In the repo: **Settings > Actions > General > Workflow permissions** > tick
   **Read and write permissions** (so it can save `data.json`).
4. Done. To change the time, edit the `cron:` line. To run it now, use the repo's
   **Actions** tab > **Run workflow**.

---

## Where settings live (`config.py`)

- `VENUES_CSV` / `VENUES_JSON` / `DATA_JSON` - the file names.
- `SHOW_POSTCODE_SIBLINGS` - whether `resolve.py` lists a hotel's neighbours.
- `REQUEST_DELAY_SECONDS` / `MAX_RETRIES` - how gently it calls the API.
- `ATTRIBUTION_HTML` - the credit/disclaimer line shown on the scoreboard. Leave the
  attribution in place (see Compliance).

---

## Compliance (please keep these)

The FSA data is free to reuse under the **Open Government Licence**, and the rating
images are free to use **as supplied**. The build already does what the FSA terms ask,
and you should keep it that way:

- Always shows the **live** rating and the **inspection date** - never a stored score.
- Uses the **official FSA images** unchanged (don't recolour or edit them).
- Credits the **Food Standards Agency** under the **Open Government Licence**.
- States the rating can change, that businesses have a **right to reply**, and that
  this is **not an FSA endorsement** (Beyond the Airport is not affiliated with the FSA).

If you display specific past inspection findings (e.g. from FOI reports) rather than
just the live rating, keep them dated and in your own words, and offer a right of reply
- but the live rating shown here is the clean, low-risk way to surface all of this.
