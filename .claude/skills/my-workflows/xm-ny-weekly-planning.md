# XM NY Weekly Planning — Weekly Meeting Agenda Page

Create this week's "XM NY Weekly Planning" Confluence page under space RT, and post a footer comment inviting the recurring attendees to add topics. This is Bonnie's personal recurring workflow — normally run about once a week to prep the agenda ahead of the meeting.

## When to Use

Trigger on natural language, not a fixed command. Examples:

**中文：**
- "创建本周的 meeting agenda"
- "建一下这周的 weekly planning page"
- "这周的 XM NY weekly planning"

**English:**
- "create this week's meeting agenda"
- "set up the weekly planning page"
- "XM NY weekly planning for this week"

Usually asked once a week (often Monday), but recognize the intent regardless of which day it's asked on — the date math (below) is relative to whenever the page actually gets created, not tied to Monday specifically.

If the phrasing could plausibly mean some other meeting/page, confirm scope before creating anything.

## Defaults (fixed — do not ask the user to repeat these)

| Setting | Value |
|---|---|
| Space key | `RT` (Restaurant Technology) |
| Parent page | `4675175482` — the "2026" yearly container page. `https://wonder.atlassian.net/wiki/spaces/RT/pages/4675175482/2026` |
| Title format | `XM NY Weekly Planning yyyy-m-dd` — 4-digit year, month **without** leading zero, day **zero-padded to 2 digits**. Examples: `2026-7-03`, `2026-7-21`, `2026-12-05` |
| Title date rule | Page-creation date **+ 1 calendar day** (see below — this was corrected once already, don't default to "the day before") |
| Body content | Single heading `# Topics` (markdown format, via `content_format: "markdown"`) |
| Footer comment | Mentions the recurring attendees (below), inviting them to add topics |

**Parent-page caveat**: `4675175482` is specifically the **"2026"** container page. When the calendar rolls to 2027, this ID stops being correct — check whether an equivalent "2027" page exists under space RT (or ask the user) rather than continuing to hardcode this ID forever.

## Title Date — Worked Example

Title date = **today's date (the day the page is created) + 1 day**. Get "today" from the session's `currentDate` context — never guess or assume.

- Created 2026-07-20 → title date is 2026-07-21 → title: `XM NY Weekly Planning 2026-7-21`
- Created on a Monday → title date is Tuesday of the same week.

## Recurring Attendees to Mention

Mention these four by default in the footer comment (Bonnie is CC'd on her own agenda posts). Account IDs below are already confirmed working — reuse them directly, don't re-search unless a mention fails or the user changes the list:

| Name | Email | Account ID |
|---|---|---|
| Pratik Busi | pbusi@wonder.com | `63331686234d44d406d22f29` |
| Jakob Lewei | jakobhe@xm.wonder.com | `6369e33c96243ac755ede0b1` |
| Lisa Li | lisazheng@xm.wonder.com | `5d3834aaf8be2f0c20bb782e` |
| Bonnie Yang | bonnieyang@xm.wonder.com | `60bed03c8f2cc100696715b3` |

If the user asks to add/remove someone for a given week: resolve via `mcp__mcp-atlassian__confluence_search_user`. If a full handle/concatenated name (e.g. "jakoblewei") returns `[]`, retry with just the first name — Confluence's user search is inconsistent with concatenated handles. Always confirm the match (display name + email) against what the user meant before using the account ID — searches can return same-first-name collisions (e.g. searching "lisa" also surfaces "Lisa Appleton", a different person than "Lisa Li"). Never guess an account ID.

## Execution Steps

### 1. Compute the title date
Today (from `currentDate` context) + 1 day. Format per the Title format rule above (month unpadded, day zero-padded).

### 2. Create the page
Call `mcp__mcp-atlassian__confluence_create_page`:
- `space_key`: `RT`
- `parent_id`: `4675175482`
- `title`: `XM NY Weekly Planning <computed date>`
- `content`: `# Topics`
- `content_format`: `markdown`

### 3. Add the footer comment with real mentions — HARD RULE ON FORMAT

**Plain markdown mentions do not work.** Passing `@Name` or `[~accountId]` as plain text in `body` renders as dead literal text — no notification, no real mention (confirmed by direct testing on this exact page). The tool's schema documents `body` as "Markdown format" with no `content_format` option, but in practice it passes through unrecognized storage-format XHTML tags unchanged — so feeding it the Confluence user-mention macro directly works:

```html
<p><ac:link><ri:user ri:account-id="63331686234d44d406d22f29" /></ac:link> <ac:link><ri:user ri:account-id="6369e33c96243ac755ede0b1" /></ac:link> <ac:link><ri:user ri:account-id="5d3834aaf8be2f0c20bb782e" /></ac:link> <ac:link><ri:user ri:account-id="60bed03c8f2cc100696715b3" /></ac:link> Hi team! This is the agenda page for our weekly meeting. Feel free to add any topics you'd like to discuss!</p>
```

Call `mcp__mcp-atlassian__confluence_add_comment` with `page_id` = the new page's ID and this `body` (swap in the current attendee account IDs).

**Verify**: the tool response's `comment.body` should show real display names rendered as `@Pratik Busi @Jakob Lewei @Lisa Li @Bonnie Yang ...`. If it instead shows raw account-id strings, `[~...]`, or an email/@handle as plain text, the mention failed — redo it with the macro form above.

### 4. Report back
Give the user: page title, page URL, and confirmation that the footer comment posted with working mentions for all attendees.

## Troubleshooting

- **Mention renders as plain text / raw account ID**: markdown syntax was used instead of the `<ac:link><ri:user ri:account-id="..." /></ac:link>` macro. Re-post using the macro form from Step 3.
- **Need to remove a bad comment**: there is no dedicated "delete comment" MCP tool in this toolset, but `mcp__mcp-atlassian__confluence_delete_page` works on comment IDs too (comments are Confluence content objects under the hood, and that endpoint deletes content generically by ID) — confirmed working in practice. Double-check the ID is the comment's ID (not the page's) before calling it.
- **`confluence_search_user` returns `[]`**: retry with just the first name instead of a concatenated handle.
- **`confluence_search_user` returns multiple people**: confirm display name + email against what the user meant; don't default to the first result.

## Persistent Automation (macOS LaunchAgent)

As of 2026-07-20, this workflow also runs **fully unattended**, independent of any chat session. Bonnie asked for a "real" recurring trigger after learning `CronCreate` (the in-session scheduler) is capped at 7 days and dies when the session ends — this LaunchAgent has neither limitation.

| Component | Location |
|---|---|
| Script | `~/.xm-ny-weekly-planning/run.sh` |
| LaunchAgent plist | `~/Library/LaunchAgents/com.bonnie.xm-ny-weekly-planning.plist` |
| Schedule | Every Monday, 15:00 local time (`StartCalendarInterval`: Weekday=1, Hour=15, Minute=0) — moved from the original 10:00 because Bonnie isn't reliably logged into her Mac that early |
| Run log | `~/.xm-ny-weekly-planning/run.log` — one line per step, check this first if a page doesn't show up |
| launchd stdout/stderr | `~/.xm-ny-weekly-planning/launchd-stdout.log` / `launchd-stderr.log` |

The script is a **standalone** reimplementation of Execution Steps 1–3 using raw `curl` + the cached Atlassian OAuth token (same cache the MCP tools use: `~/.mcp-auth/mcp-remote-*/8d8bab2a93ad41172215aecfb4b6d869_tokens.json`). It does not depend on MCP tools or any Claude session being open. If the recurring-attendee list or any Default above changes, update **both** this skill file and the `MENTIONS` array / `SPACE_ID` / `PARENT_ID` constants near the top of `run.sh` — they are not derived from each other and will drift silently otherwise.

### Critical: the script uses Confluence REST API v2, not v1 — do not "fix" this back

Discovered by testing before relying on this unattended: the cached OAuth token has granular scopes (`write:page:confluence`, `write:comment:confluence`, etc.), and these granular scopes **only authorize Confluence REST API v2** (`/wiki/api/v2/...`). Calling the legacy v1 endpoint (`/wiki/rest/api/content`) — the pattern documented elsewhere in this vault, e.g. `atlassian-confluence.md` and the REST fallback in `create-jira-ticket.md` — fails with `401 {"code":401,"message":"Unauthorized; scope does not match"}` even though the scope list looks sufficient at a glance. This cost a real debugging cycle; don't rediscover it by "simplifying" `run.sh` back to v1-style calls.

`run.sh` therefore uses, and must keep using:
- Create page: `POST /wiki/api/v2/pages` with `spaceId` (**numeric** — resolved via `GET /wiki/api/v2/spaces?keys=RT` → currently `3185017363`; NOT the `RT` space key string), `parentId`, `title`, `body.representation="storage"`
- Create footer comment: `POST /wiki/api/v2/footer-comments` with `{"pageId": ..., "body": {"representation": "storage", "value": ...}}` — a different shape than v1's `container`-based comment creation

If any *other* skill in this vault ever adds a raw-REST (non-MCP) fallback for Confluence writes, check this scope issue first rather than copying the v1 Jira-REST pattern verbatim.

### Operating the LaunchAgent

```bash
# Check it's loaded
launchctl list | grep xm-ny-weekly-planning

# Watch what happened on the last run
tail -20 ~/.xm-ny-weekly-planning/run.log

# Trigger it immediately for testing — WARNING: this creates a REAL page, not a dry run
launchctl start com.bonnie.xm-ny-weekly-planning

# Pause without deleting (stays paused across reboots until re-loaded)
launchctl unload ~/Library/LaunchAgents/com.bonnie.xm-ny-weekly-planning.plist

# Resume after pausing
launchctl load ~/Library/LaunchAgents/com.bonnie.xm-ny-weekly-planning.plist

# Remove entirely
launchctl unload ~/Library/LaunchAgents/com.bonnie.xm-ny-weekly-planning.plist
rm ~/Library/LaunchAgents/com.bonnie.xm-ny-weekly-planning.plist
```

Requires the Mac to be on and Bonnie logged in at trigger time — launchd generally catches up a missed calendar run on the next wake/login, but this isn't a hard guarantee. There is no notification layer by design (Bonnie explicitly chose the plain version over one with a success/failure notification) — if a run fails (e.g., expired refresh token), it fails silently except for the entry in `run.log`.
