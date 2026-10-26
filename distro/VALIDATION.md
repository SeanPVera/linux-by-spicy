# Desktop alpha validation

## Automated checks

- Five asset checks cover the compiled cursor sizes and click hotspots,
  disconnected tip/paw silhouettes, wallpaper exports, text contrast and
  the approved art selections.
- Behavior checks cover stalled appearance subprocesses, Qt process failure and
  retry handling, evidence filtering, installed appearance observations, and
  interrupted desktop probes with surviving descendants. VM launcher checks
  cover independent CPU/graphics choices, blocked prerequisites, bounded probes
  and evidence preservation. The alpha2 automated suite contains 65 passing
  tests; the unchanged alpha1 baseline passes its original 41 tests.
- Real Qt renders exercise 80 welcome layouts and 40 sign-in layouts across
  ten physical resolutions, from 1024×768 through 3840×2160, at 100%, 125%,
  150% and 200% scaling. The actual Atkinson Hyperlegible font is loaded.
- The sign-in preview checks that failed authentication clears the password.
  Preview authentication uses a mock; SDDM performs real authentication.
- Native checks report zero QML warnings. Shell scripts and desktop entries
  pass their format checks, and the live-build profile validates.
- The release-identity package passes install, reinstall and removal checks;
  removal restores Debian's original identity.

## Alpha2 appearance fixes and recovered validation tools

The 2026-10-26 continuation recovered the earlier uncommitted work and verified
it afresh. The recovered implementation was first saved in local source commit
`2693ed27876bd55fa3e477ea0dbd2498c5865138`.

The appearance helper now saves the Kvantum selection before applying
look-and-feel. A controlled native Qt 6.8.2/Kvantum check reproduces the previous
palette on all three Daylight → Night Prowl → Daylight selections with the old
helper, and the requested palette on all three with alpha2. The retained
`check-appearance-refresh.py`, included in `check-native`, uses Qt's native style
plugin and requires normal process teardown. Its controlled style recreation
does not establish the palette of a running Konsole or complete Plasma desktop.

Theme changes also broadcast KDE's `CursorChanged` notification after saving
settings. A private D-Bus test receives the actual `notifyChange(int32 5,
int32 0)` signal at `/KGlobalSettings`. This verifies transport and signature;
KWin selection, visible paw artwork, fallback behavior and hotspot clicks still
need a desktop run. An isolated check using real `kwriteconfig6` writes and
fresh Welcome processes confirms saved theme and reduced-motion settings; its
Plasma commands are stubbed, so sign-out and reboot persistence remain untested.

The new `spicy-desktop-test` records helper hashes, bounded operation timings,
saved settings, KWin cursor observations and optional pointer-inclusive captures.
It rejects root execution, preserves previous evidence, stops on failed desktop
access or captures, and cleans up its own process groups after timeouts,
interruptions or an early-exiting window probe. Raw outputs remain private and
visual checks remain unreviewed. See the
[installed desktop workflow](VM_VALIDATION.md#installed-desktop-follow-up).

All 72 compared regular artwork, cursor, wallpaper, Plymouth and palette files
match the alpha1 baseline byte for byte. The alpha2 packages build successfully.
Disposable package checks cover artwork/desktop unpack, alpha1-to-alpha2 upgrade
and purge; those checks do not configure the complete KDE dependency set.
The installed collector correctly returns its explicit desktop blocker in a
container without a live session, with no theme requests and no visual passes.
Release-identity install/reinstall/removal preserves foreign diversions and
restores Debian. The live-overlay regression and 20 native Plymouth renders
also pass. No accelerated or physical validation is implied by these checks.

## Alpha2 live image

The new amd64 ISO was built from
`0f80037ef3526a17bf588c926f3c6b5140bf6459`. Its SHA-256 is
`0fe59b786ce1ffe51bfc117147eea6f8a3a75f59932ecd23bc644a606cbf27ca`
and its size is 1,877,213,184 bytes. The checksum verifies. The live-build
stages completed in 488 seconds after resolving the screenshot package as
Debian's `kde-spectacle`.

The package builder records the completed package version. Image staging uses
that version explicitly and removes earlier Spicy archives from the generated
profile while retaining them in `dist`. A mixed-version fixture retained all
three alpha1 archives beside alpha2; only the three alpha2 archives were staged.

Inspection extracts the filesystem from the actual ISO and verifies that it
matches the built SquashFS. All three Spicy packages are configured at
`0.1.0~alpha2`; Spectacle, Konsole and the KWin/KScreen query tools are installed.
The installed appearance helper, collector and desktop test match the source
byte for byte, as do all 72 checked asset files against the alpha1 baseline.

A separate 300-second QEMU/TCG software boot used fresh OVMF variables, two
virtual CPUs, 4 GiB RAM, virtio-vga requesting 1920×1080, no network and no hard
disk. It received no guest input. Six timed QMP captures were retained. The
first frame passes the approved-portrait and continuous-track comparison;
some intermediate frames are black. The 225- and 270-second captures show the
Daylight desktop and Welcome window. The launcher returned 124 at its declared
time limit. These captures establish those rendered frames, not responsiveness,
successful theme switching, the guest renderer, fractional scale or sustained
stability.

A second software boot reached the same desktop, then received a read-only
diagnostic USB medium and explicit QMP keyboard input. Ctrl+Alt+T opened Konsole.
The installed test ran as the `spicy` desktop user; its helper, collector and test
hashes match the source. Guest-only mount and serial-device permission changes
allowed a bounded JSON export. These interventions and the supplemental medium
are recorded separately from the unchanged distribution ISO.

The live KWin query confirms Wayland, KWin 6.3.6, Qt 6.8.2 and Mesa 25.0.7
llvmpipe. KWin reports `SpicyLittleTip`, size 32. KWin and active-output probes
succeed, but the initial Spectacle pointer capture exceeds its 25-second limit.
The tool cleans up that process group and returns `blocked_capture`/exit 2 before
any theme-change request. It does not bypass the capture check or mark visual
acceptance. The timeout's cause remains undetermined. Selected cursor identity
does not establish pointer pixels or hotspot clicks; actual palette cycling,
reduced motion, lock/unlock, persistence and sustained use still need a capable
desktop run. No renderer defaults or process-environment overrides were changed.

The accelerated launch was rejected before QEMU started, with exit 1: this
host exposes neither a usable `/dev/kvm` nor `/dev/dri/renderD128`. No fallback
was used for that attempt. The software profile is a separate diagnostic run.
The [reviewed alpha2 summary](validation/2026-10-26-alpha2.json) records exact
artifacts, checks and remaining acceptance gates.

## Graphics and boot continuation

Appearance commands now have bounded subprocess and D-Bus waits. A failed
live refresh is reported separately from failed settings writes, and the welcome
app releases its busy state after failed starts, crashes and completed requests.
Reduced-motion changes also refresh KWin. These changes address application
responsiveness during a stalled session; they do not establish a fix for KWin's
rendering stalls.

The missing early-boot portrait was traced to Debian's Plymouth initramfs hook:
the external artwork directory was copied to a path different from the theme's
declared `ImageDir`. Boot assets now ship inside the Plymouth theme directory.
The progress image also had a square SVG viewport that letterboxed the strip;
its viewport now matches the strip dimensions.

The new `check-plymouth` uses Debian's actual initramfs hook and confirms every
theme image is present at its declared path. The staged portrait matches the
approved source byte for byte. Plymouth 24.004.60-5 then renders the staged theme
through its real script/X11 plugins under Xvfb: 20 captures across ten
resolutions through 3840×2160 at integer device scales 1× and 2× passed portrait
matching and continuous progress-track checks. This is independent of Plasma's
fractional scaling checks and does not certify DRM or hardware boot rendering.
The renderer harness explicitly requests graphical boot, including on CI hosts
whose active serial console otherwise makes Plymouth wait in text mode. The
same 20 cases pass with a simulated serial-console host.

The [VM launcher](VM_VALIDATION.md) records the exact ISO and firmware hashes,
disposable boot profile and timed QMP captures. The
[guest evidence collector](hardware/README.md) records actual session/renderer
observations and explicit missing or failed probes. All 18 functional checks and
80 scale/theme cases start untested. ISO builds regenerate local packages so
an existing `.deb` cannot silently omit source fixes. After bootstrap cleanup,
the build runs the remaining live-build stages directly so a second cache
restore cannot reintroduce the temporary release-identity diversion. Disposable
package checks also verify that foreign diversions remain intact on a refused
installation and removal.

A full-image boot exposed another build-specific blocker: live-build preserved
private checkout directory permissions from the `/etc` overlay, leaving `/etc`
at `0700`. The serial diagnostic boot showed repeated system D-Bus startup
failures; the graphical boot reached SDDM but could not complete a desktop
session. The build now normalizes copied profile directories and readable
defaults, preserving executable hooks and leaving source permissions intact.
The live-config check reproduces Debian's tar overlay with a deliberately
private source tree, verifies that service-user access fails before staging,
and verifies access and unchanged default contents after normalization.

## Earlier alpha image observations

The initial Debian 13 amd64 alpha was booted with OVMF UEFI firmware in QEMU using
software emulation, 4 GB of RAM and a virtual graphics device. The boot reached
SDDM, authenticated the `spicy` account automatically, and started Plasma on
Wayland. The Daylight desktop, portrait launcher and sleeping-Spicy lock
wallpaper rendered. Unlocking with the live-session password `live` succeeded.

The boot review found and corrected a missing `user-setup` dependency, a
Daylight lock-screen contrast issue, and a redundant first-login theme
application that could prevent the welcome app from opening after a timeout.
Firmware menus also received Spicy's portrait and consistent live-account
settings for the fallback entry.

## Rebuilt image smoke test

The continuation image was built from commit
`f64979899cf429bf03a7cbc5bfbb233d2a640dff` on 2026-10-14 UTC. Its SHA-256 is
`2806bb6cf62de0d91d46938b637bb3e0527a3c1b9b207cbdf539d24404f4fe2f`
(`spicy-linux-0.1-alpha-amd64.iso`, 1,869,873,152 bytes).

The disposable software profile used QEMU 10.0.13, q35/TCG, two virtual CPUs,
4 GiB RAM, virtio-vga requesting 1920×1080, and fresh OVMF variables. No disk or
network was attached. The launcher recorded both firmware hashes and verified
the ISO checksum before boot. Evidence is retained locally under
`distro/build/vm/alpha-software-fixed/` and is excluded from Git.

The real UEFI boot rendered the approved portrait and continuous progress bar
at 1920×1080 (`boot-016.png`). Serial diagnostics confirmed system D-Bus and
SDDM were active. SDDM authenticated `spicy` automatically and started the
Plasma Wayland session on VT 2. The Welcome app and desktop panel rendered
(`plasma-vt2-later.png`), and the text console accepted keyboard input and
diagnostic commands.

The guest collector ran as the desktop user through the existing user service
manager and was exported before shutdown (`guest-observations.json`). It reports
Plasma 6 / KWin 6.3.6 on Wayland, OpenGL composition with Mesa 25.0.7 llvmpipe
(LLVM 19.1.7), and an empty collector-process renderer-overrides map. That
collector did not inspect KWin's environment; the empty map cannot establish
that KWin had no overrides. KScreen confirms 1920×1080 at 105%
scaling, rather than an assumed 100%. The report retains tester-supplied ISO
provenance; the launcher's separately computed digest identifies the booted
medium. EFI boot was observed, but Secure Boot variables were unavailable and
the `mokutil` probe failed, so Secure Boot remains unverified.

The original collector matrix remains intact with untested defaults. A separate
`reviewed-results.json`, linked to `reviewed-observations.json` and the captures,
records portrait rendering as passed, software Daylight graphics as failed,
and usable-desktop/Secure Boot acceptance as blocked. The 80 complete-desktop
scaling/theme cases remain untested; this guest's 105% mode is outside that
matrix. The reviewed copies confirm boot provenance against the launcher and
include its VM profile.

The complete graphics gate remains incomplete: framebuffer updates were slow,
with black backgrounds and partial or blank application redraws after an
appearance request. This run does not establish successful theme switching,
reduced motion, lock/unlock or sustained everyday use for the rebuilt image.
Compare the same digest on the accelerated profile before attributing these
failures to a graphics driver or changing the default renderer.

## Host inspection and software follow-up

The next workspace also exposes neither `/dev/kvm` nor `/dev/dri`. The new
`run-vm inspect` records device type/access and bounded QEMU capability probes.
It reports blocked prerequisites or unverified candidates, never an automatic
graphics pass. CPU acceleration and graphics can now be selected independently
for KVM/software and TCG/VirGL diagnostic controls, while the original profiles
retain their defaults and never fall back silently.

Inspection also found that the builder's minimal QEMU installation lacked GTK
and OpenGL modules. Adding Debian's `qemu-system-gui` makes QEMU 10.0.13 advertise
GTK, EGL and `virtio-vga-gl`. These listings do not initialize acceleration.
The accelerated launch still exits 1 before starting QEMU because the host's
KVM and render devices are absent. No accelerated result is certified.

Generated artifacts were unavailable and were rebuilt from
`c45155426d2285ac39f92ea5ef93cb924a7c9b53` on 2026-10-14 UTC. The new ISO is
1,869,873,152 bytes, with SHA-256
`240830a1a6efafe71e649879f626661ff6bed703abade88166a1ab145f8855cf`.
The [reviewed campaign summary](validation/2026-10-14-software-vm.json) retains
the declared VM profile, observations, operation timings, acceptance statuses
and hashes of local evidence. Full reports and captures remain ignored build
artifacts under `distro/build/vm/`; private journals are not committed.

Both software boots used the same digest, q35/TCG, two virtual CPUs, 4 GiB RAM,
virtio-vga requesting 1920×1080, a headless display, fresh OVMF variables and no
network or hard disk. A read-only diagnostics CD and local USB serial command
channel were attached later; these are recorded separately from the original
launcher configuration. Neither changes the distribution ISO.

The first run included early VT switches during the SDDM-to-KWin handoff. SDDM
authenticated automatically, then its helper exited with 64. In the installed
SDDM source revision `4fe234b`, VT release uses Linux `SIGRTMAX` (64), and the
helper forwards the child's code without retaining its normal/crash distinction.
This fits an interrupted startup; it does not prove a new image login regression.
The first run rendered the approved 7A boot and 7C sign-in artwork. Its startup
result remains inconclusive, and the workflow now cautions against early VT
changes.

The repeat run received no guest input for its first 203 seconds. It rendered
the approved Plymouth portrait and growing continuous progress bar, authenticated
automatically and kept the Plasma Wayland session alive on VT 2. Guest collection
confirms KWin 6.3.6, Qt 6.8.2, Mesa 25.0.7 / llvmpipe (LLVM 19.1.7, 256 bits),
and the actual 1920×1080 mode at 105% scaling. KWin's initial environment was
unreadable to the collector and remains unknown; it is no longer inferred from
the collector's empty renderer-overrides map.

Rendering is still not stable. Initial captures stayed black; a complete Daylight
desktop/Welcome frame appeared after later VT activation, followed by a Welcome
"Not Responding" frame. The user journal records repeated KWin main-thread hang
warnings and an output-configuration failure. A later capture explicitly reports
an inactive display output; that power-saving observation is not counted as a
blank-redraw failure. The host execution transport disconnected once during
the campaign; the VM and files survived, and no host OOM kill was observed.
These interventions and unreliable input limit the interactive conclusions.

| Diagnostic operation | Observed result | Acceptance limit |
| --- | --- | --- |
| Night Prowl | Exit 0 after 18.109 s; saved `night-prowl` preference observed | Complete visual refresh and 30-minute use unverified |
| Reduced motion on | Exit 0 after 1.753 s; `ReducedMotion=true` and `AnimationDurationFactor=0` observed | Visible animation and control responsiveness unverified |
| Dolphin, Kate, Firefox ESR | All three launch requests returned 0 | Dialogs, scrolling, video and GTK interoperability unverified |
| Return to Daylight | Exit 1 after 11.096 s; `plasma-apply-lookandfeel` exceeded its 8 s limit; saved preference stayed Night Prowl | Both-theme switching/persistence gate failed; sign-out persistence untested |
| 1080p at 100% | Request skipped after the display probe could not obtain one usable active output | Actual scale remained 105%; no 100% pass |
| 720p at 100% | Request skipped because 1280×720 was not advertised | This resolution is blocked in this VM profile |
| Lock | An earlier active lock state was observed; the later lock request returned 0 | Later lock transition, sleeping 7B rendering and successful unlock unverified |

The original collector matrix is preserved with its untested defaults. Separate
reviewed copies confirm the launcher digest, pass only the exercised Plymouth
portrait criterion, fail the observed Daylight responsiveness and return-switch
criteria, and retain blocked or untested results elsewhere. Nine complete
desktop scaling cases are blocked by the attempted 100% request or unavailable
720p mode; 71 remain untested. None passed. Native Qt/Plymouth coverage through
4K remains separate from complete-desktop acceptance.

The software campaign did not complete sustained interactive use in both themes.
Repeat this exact digest on a capable KVM/VirGL host, with a visible interactive
display, before physical validation. The renderer defaults and approved artwork
remain unchanged; a software-only stall does not justify a driver-support claim.

## Parallels ARM64 installed-desktop follow-up

A user-supplied archive records an approved local desktop test on 2026-10-15
at 20:55:02–20:55:21 America/New_York (2026-10-16 UTC). The reported setup is
Debian 13.7 ARM64 in Parallels with `spicy-artwork` and `spicy-desktop`
`0.1.0~alpha1` installed. This is separate installed-package evidence. The
archive does not identify the installed package hashes, source commit or a
Spicy ISO digest, so it cannot certify the amd64 live image above.

The [reviewed ARM desktop summary](validation/2026-10-15-parallels-arm64.json)
retains the supplied archive/file hashes, command outcomes and review limits.
The supplied script was read without execution; its reports, journal extracts,
KWin responses and all four screenshots were inspected. Raw evidence contains
private desktop contents and identifiers and remains outside the repository.

KWin's own responses before and after each switch confirm KWin 6.3.6,
Qt 6.8.2, Wayland, DRM/EGL/OpenGL, Mesa 25.0.7 and
`virgl (Apple M4 (Compat))`. The active output is 1920×1080 at 100% scaling,
60 Hz. This establishes the compositor renderer for this ARM setup; it is
separate from the earlier software guest's 105% scaling and llvmpipe result.

The `spicy-appearance` Daylight → Night Prowl → Daylight sequence returned 0
for all three requests. Saved preferences and color schemes match each stage.
All four captures and four KWin queries returned 0. Screenshots show the
wallpaper, browser and file-manager palettes changing and returning to Daylight,
with existing windows and the panel retained. This narrow CLI/visual smoke
cycle completed. The Welcome application's controls were not exercised.

Two appearance discrepancies remain:

- Konsole's toolbar/tab strip is dark in Daylight and light in Night Prowl,
  following the preceding selection. The terminal text area's dark profile is
  a separate observation. Successful command exits do not establish a complete
  application refresh.
- All four KWin responses report `breeze_cursors`, size 24. The approved Spicy
  paw was not established as the active cursor, and pointer shape/hotspot checks
  were not performed. The screenshots omit the pointer.

The scripted window lasted 18.968097 seconds, including three five-second
settling waits. Per-command finish times were not recorded. No new KWin unit
journal entries appeared during that interval. Five `GL_INVALID_OPERATION`
messages from `glDrawBuffers` at 20:52:22 and a 30 ms input-processing warning
at 20:48:40 predate the cycle and remain unresolved observations. The short
interval and still images cannot establish animation smoothness, input latency,
absence of transient stalls or sustained graphics stability.

The sole nonzero scripted command was `loginctl show-session self`: the runner
was outside the login session's process scope. Live Wayland evidence comes from
KWin. Earlier sandbox-denied screenshot attempts are distinct from this approved
run and are not counted as installed-desktop failures.

The next targeted checks should record the installed helper hash, saved cursor
and Kvantum settings, and Konsole's per-application color-scheme setting, then
compare existing and newly opened Qt windows after switching. The palette
ordering hypothesis needs reproduction before changing the helper. Welcome UI
operation, reduced motion, lock/unlock, sign-out persistence, application
interaction, sustained use in both themes and the remaining scaling matrix are
still untested for this ARM setup. Full boot identity and the exact amd64 ISO's
accelerated campaign remain separate gates.

## Remaining release gates

The earlier alpha1 software VM produced KWin rendering stalls and D-Bus timeouts;
its rebuilt image also exhibited incomplete redraws after successful login.
The complete interactive appearance flow needs another pass with accelerated
graphics. The native Qt layout checks do not certify the complete Plasma desktop
at every resolution. Native Plymouth rendering now passes; the complete boot
must still be checked for each release image and advertised graphics profile.

The next campaign is VM-first: software baseline, then KVM/VirGL on a host with
usable acceleration. This workspace exposes neither `/dev/kvm` nor `/dev/dri`,
so it cannot certify the accelerated profile. Keep that result blocked until a
capable host exercises it; physical machines follow the VM gate.

Physical hardware, Secure Boot, graphics-driver coverage, suspend/resume,
battery and Bluetooth integration, and application interoperability remain
beta validation work. No graphical installer or Spicy APT repository is
included in this alpha. See [the delivery roadmap](ROADMAP.md).
