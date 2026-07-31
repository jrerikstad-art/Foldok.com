# foldok_getapp

The "get the Capture app" control for the right of the header.

```
python -m foldok_getapp --url https://foldok.com/capture --out snippet.html
```

Paste the output straight after the hamburger button. It carries its own CSS
(scoped to its element id), its own script, and the QR as inline SVG.

## Three decisions

**On a phone, a QR is useless.** You are holding the device the code points at.
Android gets a direct install button, iOS gets an honest line about where things
stand, and only a desktop sees a code. Showing a QR to someone on a phone is the
tell that nobody thought about it.

**The QR points at a page you control, never at a store.** A printed or
screenshotted code outlives whatever distribution you are using this month.
Send it to `/capture` and change what that page does — sideload today, closed
test tomorrow, Play listing later — without invalidating a code on somebody's
noticeboard.

**No external request.** A hosted QR image would be a third-party call on every
page view with the referrer attached. On a site whose whole argument is that
nothing leaves the machine, that is the detail someone screenshots. `segno` is a
build-time dependency; the shipped page gains no requests and no scripts.

## Also

- Bilingual, using the same `data-i18n-no` / `data-i18n-en` attributes as the
  rest of the site.
- Uses `var(--signal)`, `var(--line)`, `var(--paper)` with fallbacks, so it
  takes the theme rather than fighting it.
- Literal colour inside the SVG, *not* `var(--ink)` — CSS variables in SVG
  presentation attributes are unreliable in older Safari, and a QR with no fill
  is a blank square that silently does not scan.
- Closes on Escape and on click-outside; `aria-haspopup`, `aria-expanded`,
  `role="dialog"`.
- Delimited by comments so the whole thing can be pulled out as one block.

## Files

| File | Contains |
|---|---|
| `qr.py` | QR to inline SVG, horizontal runs merged into single rects. |
| `widget.py` | The button, popover, styles, platform detection, copy. |
| `__main__.py` | CLI; warns if the URL is long enough to be awkward to scan. |

```
python -m pytest foldok_getapp/tests -q
```
