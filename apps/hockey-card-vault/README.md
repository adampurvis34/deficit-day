# Hockey Card Vault

A Claude artifact for tracking what a hockey card collection is worth, in Canadian dollars.

Live app: https://claude.ai/artifact/9HbrcSzCUsgryVhPfCY5LJ (private to the owner)

## How it works

- **Add photos.** Take a picture of one card, the front and back, several cards laid flat,
  a graded slab, or a whole set. Claude reads the player, season, brand, set, card number,
  parallel, serial numbering and grade, and estimates a value in CAD with a low–high range.
  You check and correct the details before saving.
- **Update values.** Re-estimates every card in one pass and adds a dated point to each
  card's history and to the collection chart. Cards you priced yourself in the last 30 days
  are skipped.
- **Price from sold listings.** On a card's page, paste the text of an eBay "Sold items"
  search (or 130point). Claude keeps only matching sales and converts USD at the rate set
  in the footer. Use this for any card where the number matters.
- **Set value** by hand, track what you paid, and **Export CSV** for insurance records.

## Where things live

| What | Where |
|---|---|
| Card records and value history | the artifact's database, collection `cards` |
| USD→CAD rate | `meta/settings` |
| Photos | the artifact's asset store (resized to 1600 px JPEG) |

Only the owner (and anyone given Editor access) can change the collection.

## Limits

- Claude's estimates come from sales it knows about, not a live price feed, so a re-estimate
  won't catch last week's spike. Pasted sold listings fix that card by card.
- Each photo read or value update spends the viewer's own Claude usage.

`index.html` is the page source; republish it with the Artifact tool to update the app.
