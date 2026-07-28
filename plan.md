**Abstractly**

1. User goes on the website, clicks “Start” triggering
2. We ask user for their **Last.fm username** — no OAuth needed for the default path. See **Last.fm Data Access** below.
3. We pull their scrobble history from Last.fm and bring it into our app
    - See **Data Pull & Storage** below.
4. We pass our data into 2 engines; I have some engine ideas here below anyways we’re just gonna run this on users, yes the plan is to ship this I’m so deadass
    
    #### some examples of `engines`
    
    | name | algorithm | inputs |
    | --- | --- | --- |
    | **plumb_and_dump** |   1. plumbs a specific set of dates
      2. queries the top 30 most streamed songs
      3. iterates through the 30 songs, computes a `iso_score`
      4. dumps the 15 lowest `iso_score` songs | `day / month` |
    | **valleys_and_troughs** |  | no inputs |

    `day / month` is now a real, satisfiable input — Last.fm's `from`/`to` timestamps give us actual date-ranged scrobble queries, unlike Spotify's API. See **Data Pull & Storage**.
5. Engine writes back some kind of metadata —> there are now 2 pieces
    - This metadata is Last.fm artist/track name pairs, not Spotify IDs — see **Track Resolution** below for how that becomes something we can hand to Spotify.
6. Program resolves each track to a Spotify URI, connects the user's Spotify account if not already connected (**Spotify — Playlist Write-Back** below), calls the SpotifyAPI to write a new Spotify playlist, and then user adds it to their Spotify / plays it in the web.

#### Last.fm Data Access

Default path needs **no OAuth at all** — Last.fm's `user.getRecentTracks` is public data, gated only by an `api_key` (ours, app-level) and the target `username`.

1. User types in their Last.fm username (or we offer a "connect Last.fm" button that just deep-links them to create one, if they don't have it — separate concern).
2. Backend does a cheap validation call — `user.getRecentTracks` with `limit=1` — to confirm the username exists and their history is public.
3. **If error 17 ("hide recent listening information")** — profile is private. Fall back to Last.fm's own auth flow:
    - Signed request (api_key + shared secret, MD5 signature) to `auth.getToken`.
    - Redirect user to `last.fm/api/auth/?api_key=...&token=...` to approve.
    - Call `auth.getSession` to exchange the approved token for a **session key**.
    - Unlike Spotify, this session key doesn't expire or rotate — it's valid until the user revokes it from their Last.fm settings. No refresh-token loop needed; just store it encrypted at rest, same handling as any long-lived secret.
4. Store whichever identity we ended up with (username, or username + encrypted session key) against the internal user record.

#### Data Pull & Storage

**How the API engages with pulling data:**

- `user.getRecentTracks` — takes `from` / `to` as UNIX timestamps, paginated up to 1000 results/page, walks the user's **actual scrobble history**, not a rolling window. This is what resolves `plumb_and_dump`'s `day / month` input — we can query real, arbitrary date ranges directly, which Spotify's API cannot do.
- `user.getWeeklyTrackChart` / `getWeeklyChartList` — available if an engine wants "top tracks for week X" pre-aggregated instead of raw scrobble rows.
- Caveat carried over from the Spotify-only design: a user only has scrobble history from whenever they connected Last.fm's Spotify Scrobbling (Last.fm Settings → Applications). No retroactive backfill before that date — day-one Last.fm users (or users who just signed up for Time Capsule) may have thin or no history for older date ranges.

**Where does the pulled data live — still not the browser:**

Same conclusion as before, same reasoning:
- A scrobble-history pull can be bigger than the old Spotify top-tracks call — a heavy listener over several months could be thousands of rows — but it's still just flat JSON (artist, track, timestamp), on the order of hundreds of KB to a couple MB, not something that changes the calculus.
- It's still personal listening data; keeping it in `localStorage`/`sessionStorage` exposes it to XSS, doesn't expire cleanly, and buys us nothing since the backend needs it anyway to run the engines.
- **Recommended default:** pull on-demand into the backend when an engine runs (using `from`/`to` scoped to what that engine actually needs), hold it in memory for the run, don't persist. If we want to avoid re-pulling the same range on repeated runs, a short-TTL server-side cache (Redis, keyed on `username + date range`) is the right shape — never the browser.

#### Track Resolution (Last.fm → Spotify)

Engines now operate on Last.fm scrobble rows — artist name + track name + timestamp, no Spotify IDs attached. Before we can write a playlist, each track an engine selects needs to become a Spotify URI:

- Call Spotify's **Search API** (`GET /search?type=track&q=...`) using an app-level **Client Credentials** token — this is app-to-Spotify auth, not user auth, so it doesn't need the user to be connected yet and doesn't need refreshing the way user tokens do (client-credentials tokens are just re-requested when expired, no refresh token concept).
- Artist/title strings from Last.fm won't always match Spotify's canonical naming 1:1 (remasters, features, typos) — matching/confidence strategy is a resolution-logic concern, out of scope here.

#### Spotify — Playlist Write-Back

Spotify is no longer our data source — it's only needed at the very end, to actually create the playlist in the user's account. This narrows what we ask for and when:

- **Scopes:** just `playlist-modify-public` + `playlist-modify-private`. We no longer need `user-top-read` or `user-read-recently-played` since we don't pull listening data from Spotify anymore.
- **UX choice:** defer the Spotify connect prompt to step 6 — right before we're about to hand the user a finished playlist — rather than upfront at step 2. They don't need to trust us with Spotify write access until we've already proven we have something worth giving them.

Otherwise the flow is unchanged from before — **Authorization Code Flow + PKCE**, backend-mediated:

1. **Kick off** — "Save this playlist to Spotify" button hits our backend at `/auth/login`.
2. Backend generates a random `code_verifier`, derives `code_challenge` (S256), generates a random `state`, and stashes `code_verifier` + `state` in a short-lived, signed httpOnly cookie (or server session).
3. Backend redirects the browser to Spotify's `/authorize` endpoint with `client_id`, `redirect_uri`, `scope`, `state`, `code_challenge`, `code_challenge_method=S256`. This is what triggers the actual "Spotify is requesting permission" screen.
4. User approves in Spotify's UI → Spotify redirects back to our `redirect_uri` (a backend callback route) with `code` + `state`.
5. Backend verifies `state` matches the cookie (CSRF check), then exchanges `code` + `code_verifier` for an `access_token` + `refresh_token` via POST to Spotify's `/api/token`.
6. Backend calls Spotify `/me` to get the user's Spotify ID, links it to the same internal user record as their Last.fm identity.
7. **Persistence layer:** the `refresh_token` is encrypted at rest (envelope encryption / KMS-backed key, never plaintext) and stored server-side against that user record. The short-lived `access_token` + its expiry can live in memory/cache (e.g. Redis) — no need to persist it, it's cheap to re-derive.
8. Backend sets its **own** app session (signed httpOnly cookie or JWT) tied to our internal user ID. This is what keeps the user logged into *Time Capsule* — it is intentionally separate from the Spotify tokens.
9. **Every future request that needs to write to Spotify:** backend checks the cached access token's expiry. If expired (access tokens last ~1hr), it silently calls `/api/token` with `grant_type=refresh_token` using the decrypted stored refresh token, gets a fresh access token (and a rotated refresh token, if Spotify sends one — overwrite the stored one when it does), and proceeds. The user never sees this happen.
10. **Revocation handling:** if a refresh attempt comes back `invalid_grant`, the stored token is dead (user revoked access in their Spotify settings, or it expired from disuse). Clear the stored token and fall back to step 1 — re-prompt the user, but only when they next try to save a playlist.

Security notes:
- Client secret (if used alongside PKCE) never touches the browser — token exchange happens server-side only.
- Tokens never live in localStorage or client-readable cookies; the browser only ever holds our own opaque session cookie.
- All redirects/exchanges over HTTPS; `state` + PKCE together cover CSRF and auth-code-interception attacks.
