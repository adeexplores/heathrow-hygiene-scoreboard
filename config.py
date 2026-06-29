# ============================================================================
#  config.py  -  ALL THE SETTINGS IN ONE PLACE
# ----------------------------------------------------------------------------
#  The scoreboard shows ONLY the venues you list in venues.csv (the hotels,
#  their in-hotel restaurants, and the eateries you mention in HTT). It does
#  NOT pull in the whole area. To change which venues appear, edit venues.csv
#  and re-run resolve.py.
#
#  Both resolve.py and fetch.py read their settings from here.
# ============================================================================

# --- FILES --------------------------------------------------------------------
VENUES_CSV  = "venues.csv"      # your curated list (name, postcode, group)
VENUES_JSON = "venues.json"     # written by resolve.py (your list -> FHRSID)
DATA_JSON   = "data.json"       # written by fetch.py (what the widget reads)

# --- API ----------------------------------------------------------------------
# Food Standards Agency Food Hygiene Rating API, v2. Free, no key needed.
API_BASE   = "https://api.ratings.food.gov.uk"
API_HEADER = {"x-api-version": "2", "accept": "application/json"}

# When resolving a venue, the resolver also lists OTHER food businesses found at
# the same postcode. That is how you spot a hotel's separately-rated restaurant
# (e.g. the brasserie inside a hotel) so you can add it as its own line.
SHOW_POSTCODE_SIBLINGS = True

# --- Politeness / robustness when calling the API -----------------------------
REQUEST_DELAY_SECONDS = 0.25   # small pause between calls
MAX_RETRIES           = 4      # retries on a failed call

# --- ATTRIBUTION (shown on the widget, do not remove) -------------------------
# Wording chosen to meet the FSA terms (ratings.food.gov.uk/terms-and-conditions):
# OGL attribution, the rating is a snapshot with a date, right to reply, and a
# clear statement that this is not an FSA endorsement / we are not affiliated.
ATTRIBUTION_HTML = (
    'Food hygiene ratings &copy; Food Standards Agency, reused under the '
    '<a href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" '
    'target="_blank" rel="noopener">Open Government Licence v3.0</a>. '
    'Each rating reflects the standards found at that venue&rsquo;s last inspection (date shown) '
    'and can change; businesses have a right to reply. '
    'Beyond the Airport is not affiliated with, or endorsed by, the Food Standards Agency. '
    'Always confirm the current rating on the '
    '<a href="https://ratings.food.gov.uk" target="_blank" rel="noopener">FSA site</a>.'
)
