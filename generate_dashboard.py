"""Generate a static HTML dashboard from the listings database."""

import os
from datetime import datetime

from database import get_all_active_ranked, get_stats, init_db

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
OUTPUT_PATH = os.path.join(DOCS_DIR, "index.html")


def generate():
    """Generate docs/index.html from current listings database."""
    init_db()
    listings = get_all_active_ranked()
    stats = get_stats()

    now = datetime.now().strftime("%b %d, %Y at %-I:%M %p")
    total = stats.get("total_active", 0)
    top_score = listings[0].score if listings else 0

    # Collect unique neighborhoods and sources for filter tabs
    neighborhoods = sorted({l.neighborhood for l in listings if l.neighborhood})
    sources = sorted({l.source for l in listings if l.source})

    # Build listing rows
    rows_html = ""
    for l in listings:
        # Score color
        if l.score >= 85:
            score_bg, score_fg = "#dcfce7", "#166534"
        elif l.score >= 65:
            score_bg, score_fg = "#dbeafe", "#1e40af"
        elif l.score >= 45:
            score_bg, score_fg = "#fef3c7", "#92400e"
        else:
            score_bg, score_fg = "#fee2e2", "#991b1b"

        # Price tier
        tier = l.price_tier()
        if tier == "Ideal":
            tier_bg, tier_fg = "#dcfce7", "#166534"
        elif tier == "Local Max":
            tier_bg, tier_fg = "#fef3c7", "#92400e"
        elif tier == "Absolute Max":
            tier_bg, tier_fg = "#fee2e2", "#991b1b"
        else:
            tier_bg, tier_fg = "#f3f4f6", "#6b7280"

        # Amenity pills
        pills = ""
        if l.has_outdoor_space:
            pills += '<span class="pill pill-green">Outdoor</span>'
        if l.has_garage:
            pills += '<span class="pill pill-blue">Garage</span>'
        if l.has_in_unit_laundry:
            pills += '<span class="pill pill-purple">In-Unit W/D</span>'
        if not pills:
            pills = '<span class="pill pill-gray">None</span>'

        neighborhood = l.neighborhood or "N/A"
        address = l.address or ""
        address_display = address[:50] + "..." if len(address) > 50 else address
        title = l.title[:60] + "..." if len(l.title) > 60 else l.title
        first_seen = l.first_seen.strftime("%b %d")

        # Amenity data attributes for filtering
        amenity_tags = []
        if l.has_outdoor_space:
            amenity_tags.append("outdoor")
        if l.has_garage:
            amenity_tags.append("garage")
        if l.has_in_unit_laundry:
            amenity_tags.append("laundry")
        amenities_data = ",".join(amenity_tags) if amenity_tags else "none"

        rows_html += f"""
        <tr class="listing-row" data-score="{l.score}" data-price="{l.price}"
            data-neighborhood="{neighborhood}" data-tier="{tier}"
            data-source="{l.source}" data-amenities="{amenities_data}">
          <td class="col-score">
            <span class="score-badge" style="background:{score_bg};color:{score_fg}">{l.score}</span>
          </td>
          <td class="col-price">
            <div class="price">${l.price:,}/mo</div>
            <span class="tier-badge" style="background:{tier_bg};color:{tier_fg}">{tier}</span>
          </td>
          <td class="col-neighborhood">{neighborhood}</td>
          <td class="col-address" title="{address}">{address_display}</td>
          <td class="col-beds">{l.bedrooms}BR</td>
          <td class="col-amenities">{pills}</td>
          <td class="col-title hide-mobile">{title}</td>
          <td class="col-source hide-mobile">{l.source}</td>
          <td class="col-date hide-mobile">{first_seen}</td>
          <td class="col-link">
            <a href="{l.source_url}" target="_blank" rel="noopener">View&nbsp;&rarr;</a>
          </td>
        </tr>
        """

    # Build neighborhood filter buttons
    hood_buttons = '<button class="filter-btn active" data-filter="all">All</button>\n'
    for n in neighborhoods:
        hood_buttons += f'<button class="filter-btn" data-filter="{n}">{n}</button>\n'

    # Build source filter buttons
    source_buttons = '<button class="filter-btn active" data-filter="all">All</button>\n'
    for s in sources:
        source_buttons += f'<button class="filter-btn" data-filter="{s}">{s.title()}</button>\n'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Apartment Scrape Bot</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; }}

  .container {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}

  /* Header */
  .header {{ background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .header h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .header .subtitle {{ color: #64748b; font-size: 14px; }}

  /* Filters */
  .filters {{ margin-bottom: 16px; }}
  .filter-group {{ margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .filter-group-label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; width: 100%; }}
  .filter-btn {{
    padding: 6px 14px; border-radius: 20px; border: 1px solid #e2e8f0;
    background: white; color: #475569; font-size: 13px; cursor: pointer;
    transition: all 0.15s;
  }}
  .filter-btn:hover {{ border-color: #94a3b8; }}
  .filter-btn.active {{ background: #1e293b; color: white; border-color: #1e293b; }}

  /* Table */
  .table-wrap {{ background: white; border-radius: 12px; overflow-x: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  thead th {{
    padding: 12px 10px; text-align: left; font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.5px; color: #94a3b8; border-bottom: 2px solid #e2e8f0;
    cursor: pointer; user-select: none; white-space: nowrap;
  }}
  thead th:hover {{ color: #475569; }}
  thead th.sorted-asc::after {{ content: ' \\2191'; }}
  thead th.sorted-desc::after {{ content: ' \\2193'; }}
  tbody tr {{ border-bottom: 1px solid #f1f5f9; transition: background 0.1s; }}
  tbody tr:hover {{ background: #f8fafc; }}
  tbody td {{ padding: 12px 10px; vertical-align: middle; }}

  .score-badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 15px; }}
  .tier-badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-top: 2px; }}
  .price {{ font-weight: 600; font-size: 15px; }}

  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; margin: 1px 2px; }}
  .pill-green {{ background: #dcfce7; color: #166534; }}
  .pill-blue {{ background: #dbeafe; color: #1e40af; }}
  .pill-purple {{ background: #ede9fe; color: #5b21b6; }}
  .pill-gray {{ background: #f3f4f6; color: #9ca3af; }}

  .col-link a {{ color: #3b82f6; text-decoration: none; font-weight: 500; white-space: nowrap; }}
  .col-link a:hover {{ text-decoration: underline; }}

  .col-title {{ max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #64748b; font-size: 13px; }}
  .col-address {{ max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #64748b; font-size: 13px; }}
  .col-source {{ color: #94a3b8; font-size: 12px; }}
  .col-date {{ color: #94a3b8; font-size: 12px; white-space: nowrap; }}

  .footer {{ text-align: center; padding: 20px; color: #94a3b8; font-size: 12px; }}
  .footer a {{ color: #94a3b8; }}

  .no-results {{ padding: 40px; text-align: center; color: #94a3b8; }}

  /* Mobile card layout */
  @media (max-width: 768px) {{
    .hide-mobile {{ display: none; }}
    .container {{ padding: 8px; }}
    .header {{ padding: 16px; }}
    .header h1 {{ font-size: 18px; }}
    table {{ font-size: 13px; }}
    thead th, tbody td {{ padding: 10px 6px; }}
    .score-badge {{ font-size: 13px; padding: 3px 8px; }}
    .price {{ font-size: 14px; }}
    .pill {{ font-size: 10px; padding: 1px 6px; }}
    .col-amenities {{ max-width: 120px; }}
  }}
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>Apartment Scrape Bot</h1>
    <div class="subtitle">
      {total} active listing{"s" if total != 1 else ""} &middot;
      Top score: {top_score} &middot;
      Updated: {now}
    </div>
  </div>

  <div class="filters">
    <div class="filter-group" id="hood-filters">
      <div class="filter-group-label">Neighborhood</div>
      {hood_buttons}
    </div>
    <div class="filter-group" id="tier-filters">
      <div class="filter-group-label">Price Tier</div>
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="Ideal">Ideal (&le;$3,100)</button>
      <button class="filter-btn" data-filter="Local Max">Local Max (&le;$3,500)</button>
      <button class="filter-btn" data-filter="Absolute Max">Abs Max (&le;$4,000)</button>
    </div>
    <div class="filter-group" id="source-filters">
      <div class="filter-group-label">Source</div>
      {source_buttons}
    </div>
    <div class="filter-group" id="amenity-filters">
      <div class="filter-group-label">Amenities</div>
      <button class="filter-btn active" data-filter="all">All</button>
      <button class="filter-btn" data-filter="outdoor">Outdoor</button>
      <button class="filter-btn" data-filter="garage">Garage</button>
      <button class="filter-btn" data-filter="laundry">In-Unit W/D</button>
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th data-sort="score" class="sorted-desc">Score</th>
          <th data-sort="price">Price</th>
          <th data-sort="neighborhood">Area</th>
          <th data-sort="address">Address</th>
          <th data-sort="beds">Beds</th>
          <th>Amenities</th>
          <th class="hide-mobile">Title</th>
          <th class="hide-mobile">Source</th>
          <th class="hide-mobile">Found</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody id="listings-body">
        {rows_html}
      </tbody>
    </table>
    <div class="no-results" id="no-results" style="display:none;">
      No listings match your filters.
    </div>
  </div>

  <div class="footer">
    <p>Budget: $3,100 ideal &middot; $3,500 local max &middot; $4,000 absolute max</p>
    <p>Santa Monica &middot; Brentwood &middot; Mar Vista &middot; Ocean Park &middot; Venice</p>
    <p style="margin-top:8px"><a href="https://github.com/todd-gavin/apartment-scrape-bot">GitHub</a></p>
  </div>
</div>

<script>
// --- Filtering ---
let activeHood = 'all';
let activeTier = 'all';
let activeSource = 'all';
let activeAmenity = 'all';

function setupFilterGroup(groupId, setter) {{
  document.querySelectorAll('#' + groupId + ' .filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('#' + groupId + ' .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      setter(btn.dataset.filter);
      applyFilters();
    }});
  }});
}}

setupFilterGroup('hood-filters', v => activeHood = v);
setupFilterGroup('tier-filters', v => activeTier = v);
setupFilterGroup('source-filters', v => activeSource = v);
setupFilterGroup('amenity-filters', v => activeAmenity = v);

function applyFilters() {{
  let visible = 0;
  document.querySelectorAll('.listing-row').forEach(row => {{
    const matchHood = activeHood === 'all' || row.dataset.neighborhood === activeHood;
    const matchTier = activeTier === 'all' || row.dataset.tier === activeTier;
    const matchSource = activeSource === 'all' || row.dataset.source === activeSource;
    const matchAmenity = activeAmenity === 'all' || (row.dataset.amenities && row.dataset.amenities.split(',').includes(activeAmenity));
    const show = matchHood && matchTier && matchSource && matchAmenity;
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  document.getElementById('no-results').style.display = visible === 0 ? '' : 'none';
}}

// --- Sorting ---
let currentSort = 'score';
let sortDir = 'desc';

document.querySelectorAll('thead th[data-sort]').forEach(th => {{
  th.addEventListener('click', () => {{
    const field = th.dataset.sort;
    if (currentSort === field) {{
      sortDir = sortDir === 'desc' ? 'asc' : 'desc';
    }} else {{
      currentSort = field;
      sortDir = field === 'price' ? 'asc' : 'desc';
    }}

    // Update header classes
    document.querySelectorAll('thead th').forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));
    th.classList.add(sortDir === 'asc' ? 'sorted-asc' : 'sorted-desc');

    // Sort rows
    const tbody = document.getElementById('listings-body');
    const rows = Array.from(tbody.querySelectorAll('.listing-row'));
    rows.sort((a, b) => {{
      let va, vb;
      if (field === 'score' || field === 'price') {{
        va = parseFloat(a.dataset[field]);
        vb = parseFloat(b.dataset[field]);
      }} else if (field === 'neighborhood') {{
        va = a.dataset.neighborhood.toLowerCase();
        vb = b.dataset.neighborhood.toLowerCase();
      }} else if (field === 'address') {{
        va = (a.querySelector('.col-address') || {{}}).textContent || '';
        vb = (b.querySelector('.col-address') || {{}}).textContent || '';
        va = va.toLowerCase(); vb = vb.toLowerCase();
      }} else if (field === 'beds') {{
        va = parseInt(a.querySelector('.col-beds').textContent);
        vb = parseInt(b.querySelector('.col-beds').textContent);
      }}
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    }});
    rows.forEach(row => tbody.appendChild(row));
  }});
}});
</script>

</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    print(f"Dashboard generated: {OUTPUT_PATH}")
    print(f"  {total} listings, top score: {top_score}")


if __name__ == "__main__":
    generate()
