# District Intelligence — HubSpot CRM card

A UI extension that renders this platform's district intelligence directly on
the HubSpot **company** record: ICP targeting, funding profile, need
indicators, buying signals, and outreach status.

All values are read from the `k12_*` company properties written by
`hubspot_import.py`, so the card needs no backend of its own.

## Deploy

```bash
# 1. Authenticate the CLI against the account holding your CRM data
hs account auth

# 2. From this directory, upload the project
cd hubspot-app
hs project upload
```

Then open any district company record and add the card to the record
(Customize → add card) — or find it under the record's tabs.

## Files

- `hsproject.json` — project + platform version
- `src/app/app-hsmeta.json` — private app definition and scopes
- `src/app/cards/district-intelligence-hsmeta.json` — card placement config
- `src/app/cards/DistrictIntelligence.jsx` — the React card

## Installing the app (required — deploy alone is not enough)

`hs project upload` builds and deploys the app, but the cards will **not**
appear on any record until the app is *installed* in the target portal.
A deployed-but-uninstalled app looks exactly like a broken card.

```bash
# Is it installed?
hs project app-install-status

# If not, this prints an install URL and waits for you to approve it:
hs project dev --project-account=<portalId> --testing-account=<portalId>
```

The install URL looks like:
`https://app.hubspot.com/static-token/<portalId>/authorize?appId=<appId>`

Approve it in the browser, then the cards become available on company
records (add them via **Customize** if they don't appear automatically).
