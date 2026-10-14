# Desktop alpha validation

## Automated checks

- Five asset checks cover the compiled cursor sizes and click hotspots,
  disconnected tip/paw silhouettes, wallpaper exports, text contrast and
  the approved art selections.
- Twenty-four additional behavior checks cover stalled appearance subprocesses,
  Qt process failure/retry handling, and evidence collection with missing tools,
  checksum failures, private-field filtering, firmware access failures and the
  distinction between collector and KWin process environments. Twelve VM
  launcher checks cover independent CPU/graphics choices, blocked prerequisites,
  bounded probes, retained launch metadata and evidence preservation.
  The combined automated suite contains 41 passing tests.
- Real Qt renders exercise 80 welcome layouts and 40 sign-in layouts across
  ten physical resolutions, from 1024×768 through 3840×2160, at 100%, 125%,
  150% and 200% scaling. The actual Atkinson Hyperlegible font is loaded.
- The sign-in preview checks that failed authentication clears the password.
  Preview authentication uses a mock; SDDM performs real authentication.
- Native checks report zero QML warnings. Shell scripts and desktop entries
  pass their format checks, and the live-build profile validates.
- The release-identity package passes install, reinstall and removal checks;
  removal restores Debian's original identity.

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

## Remaining release gates

The earlier software-only VM produced KWin rendering stalls and D-Bus timeouts;
the rebuilt image also exhibited incomplete redraws after successful login.
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
