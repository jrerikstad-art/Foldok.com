"""The "get the Capture app" control, for the right of the header.

Two decisions that make it feel considered rather than bolted on:

**On a phone, a QR is useless.**  You are holding the device the code is meant
to send you to. So the widget detects: on Android it offers a direct install, on
iOS it says where things stand, and only on a desktop does it show a code to
scan. A QR shown to someone on a phone is the tell that nobody thought about it.

**The QR points at a page you control, never at a store.**  A printed or
screenshotted code outlives whatever distribution you are using this month. Send
it to ``/capture`` and change what that page does — sideload today, Play Store
later, TestFlight in between — without invalidating a code somebody pinned to a
noticeboard.

Bilingual, because the site is. Uses the site's own CSS variables, so it takes
the theme rather than fighting it. No external requests, no new scripts, no
dependency at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from .qr import QRStyle, qr_svg


@dataclass(frozen=True)
class Copy:
    no: str
    en: str

    def span(self) -> str:
        return f'<span data-i18n-no="{self.no}" data-i18n-en="{self.en}">{self.en}</span>'


DEFAULT_COPY: dict[str, Copy] = {
    "button": Copy("Kamera-app", "Capture app"),
    "title": Copy("Få Capture på telefonen", "Get Capture on your phone"),
    "blurb": Copy(
        "Ta bilder rett inn i prosjektmappen. Bildene havner i mappen du allerede bruker "
        "— ingenting lastes opp til oss.",
        "Photograph straight into the project folder. Pictures land in the folder you "
        "already use — nothing is uploaded to us.",
    ),
    "scan": Copy("Skann med telefonen", "Scan with your phone"),
    "android": Copy("Installer på Android", "Install on Android"),
    "ios": Copy("iOS kommer", "iOS coming"),
    "open_page": Copy("Åpne siden", "Open the page"),
    "close": Copy("Lukk", "Close"),
}


def widget(
    url: str,
    *,
    android_url: str = "",
    ios_url: str = "",
    copy: dict[str, Copy] | None = None,
    qr_style: QRStyle | None = None,
    element_id: str = "getCapture",
) -> str:
    """A self-contained block: button, popover, styles and behaviour.

    Paste it immediately after the hamburger button in the header. It carries its
    own CSS scoped to ``#{element_id}`` and its own script, so it can be dropped
    in and pulled back out without touching anything else.
    """
    copy = {**DEFAULT_COPY, **(copy or {})}
    svg = qr_svg(url, qr_style, title="Foldok Capture")
    android = android_url or url
    ios = ios_url

    return f"""
<!-- Foldok :: get the Capture app. Self-contained; safe to remove as one block. -->
<div id="{element_id}" class="gc">
  <button class="gc-btn" type="button" aria-haspopup="dialog" aria-expanded="false"
          aria-controls="{element_id}-pop" title="{copy['title'].en}">
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
         stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <rect x="6" y="2.5" width="12" height="19" rx="2.5"/>
      <circle cx="12" cy="11" r="3.2"/>
      <path d="M10.5 6.4h3"/>
    </svg>
    <span class="gc-label">{copy['button'].span()}</span>
  </button>

  <div class="gc-pop" id="{element_id}-pop" role="dialog" aria-modal="false"
       aria-label="{copy['title'].en}" hidden>
    <p class="gc-title">{copy['title'].span()}</p>
    <p class="gc-blurb">{copy['blurb'].span()}</p>

    <div class="gc-desktop">
      <div class="gc-qr">{svg}</div>
      <p class="gc-hint">{copy['scan'].span()}</p>
      <a class="gc-link" href="{url}">{copy['open_page'].span()}</a>
    </div>

    <div class="gc-android" hidden>
      <a class="gc-cta" href="{android}">{copy['android'].span()}</a>
    </div>

    <div class="gc-ios" hidden>
      {'<a class="gc-cta" href="' + ios + '">' + copy['ios'].span() + '</a>'
       if ios else '<p class="gc-hint">' + copy['ios'].span() + '</p>'}
    </div>
  </div>
</div>

<style>
#{element_id} {{ position: relative; display: inline-flex; }}
#{element_id} .gc-btn {{
  display: inline-flex; align-items: center; gap: 7px; cursor: pointer;
  font: 600 12.5px/1 inherit; color: inherit;
  padding: 7px 11px; border: 1px solid var(--line, #DAD7CC);
  border-radius: 8px; background: transparent;
}}
#{element_id} .gc-btn:hover {{ border-color: var(--signal, #F2B705); }}
#{element_id} .gc-btn[aria-expanded="true"] {{
  border-color: var(--signal, #F2B705); background: color-mix(in srgb, var(--signal, #F2B705) 12%, transparent);
}}
#{element_id} .gc-pop {{
  position: absolute; top: calc(100% + 9px); right: 0; z-index: 60;
  width: 272px; padding: 16px;
  background: var(--paper, #FAF9F5); color: var(--ink, #16181D);
  border: 1px solid var(--line, #DAD7CC); border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0,0,0,.16);
}}
#{element_id} .gc-pop[hidden] {{ display: none; }}
#{element_id} .gc-title {{ margin: 0 0 6px; font: 700 14px/1.3 inherit; }}
#{element_id} .gc-blurb {{ margin: 0 0 13px; font-size: 12.5px; line-height: 1.45;
  color: var(--steel, #8A8577); }}
#{element_id} .gc-qr {{ display: flex; justify-content: center; padding: 9px;
  background: #fff; border: 1px solid var(--line, #DAD7CC); border-radius: 8px; }}
#{element_id} .gc-hint {{ margin: 9px 0 0; text-align: center; font-size: 12px;
  color: var(--steel, #8A8577); }}
#{element_id} .gc-link {{ display: block; margin-top: 7px; text-align: center;
  font-size: 12px; color: inherit; }}
#{element_id} .gc-cta {{
  display: block; text-align: center; text-decoration: none;
  padding: 11px 14px; border-radius: 9px; font: 600 13px/1 inherit;
  background: var(--signal, #F2B705); color: var(--ink, #16181D);
}}
@media (max-width: 640px) {{ #{element_id} .gc-label {{ display: none; }} }}
@media (prefers-reduced-motion: no-preference) {{
  #{element_id} .gc-pop {{ animation: gc-in .13s ease-out; }}
  @keyframes gc-in {{ from {{ opacity: 0; transform: translateY(-4px); }} }}
}}
</style>

<script>
(function () {{
  var root = document.getElementById("{element_id}");
  if (!root) return;
  var btn = root.querySelector(".gc-btn");
  var pop = root.querySelector(".gc-pop");

  /* A QR is useless to someone already holding the phone it points at. */
  var ua = navigator.userAgent || "";
  var android = /Android/i.test(ua);
  var ios = /iPad|iPhone|iPod/.test(ua) ||
            (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (android || ios) root.querySelector(".gc-desktop").hidden = true;
  if (android) root.querySelector(".gc-android").hidden = false;
  if (ios) root.querySelector(".gc-ios").hidden = false;

  function open(state) {{
    pop.hidden = !state;
    btn.setAttribute("aria-expanded", state ? "true" : "false");
    if (state) {{
      var focusable = pop.querySelector("a");
      if (focusable) focusable.focus({{ preventScroll: true }});
    }}
  }}
  btn.addEventListener("click", function (e) {{ e.stopPropagation(); open(pop.hidden); }});
  document.addEventListener("click", function (e) {{
    if (!pop.hidden && !root.contains(e.target)) open(false);
  }});
  document.addEventListener("keydown", function (e) {{
    if (e.key === "Escape" && !pop.hidden) {{ open(false); btn.focus(); }}
  }});
}})();
</script>
<!-- /Foldok :: get the Capture app -->
""".strip()


def landing_note(url: str) -> str:
    """What the page behind the QR has to do, in one paragraph.

    Worth writing down because the QR is the durable thing and the page is the
    changeable one — that split is the whole reason the code points here.
    """
    return (
        f"{url} is the only address the QR code knows, so it has to stay valid longer than "
        "any distribution decision. It should detect the visitor's platform and send Android "
        "to whatever install route is current — sideload, closed test, or Play listing — and "
        "tell iOS visitors honestly where things stand. When distribution changes, this page "
        "changes and every printed or screenshotted code keeps working."
    )
