# Desktop alpha validation

## Automated checks

- Five asset checks cover the compiled cursor sizes and click hotspots,
  disconnected tip/paw silhouettes, wallpaper exports, text contrast and
  the approved art selections.
- Nineteen additional behavior checks cover stalled appearance subprocesses,
  Qt process failure/retry handling, and evidence collection with missing tools,
  checksum failures, private-field filtering and firmware access failures.
  The combined automated suite contains 24 passing tests.
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

The [VM launcher](VM_VALIDATION.md) records the exact ISO and firmware hashes,
disposable boot profile and timed QMP captures. The
[guest evidence collector](hardware/README.md) records actual session/renderer
observations and explicit missing or failed probes. All 18 functional checks and
80 scale/theme cases start untested. ISO builds regenerate local packages so
an existing `.deb` cannot silently omit source fixes.

## Live-image observations

The Debian 13 amd64 image was booted with OVMF UEFI firmware in QEMU using
software emulation, 4 GB of RAM and a virtual graphics device. The boot reached
SDDM, authenticated the `spicy` account automatically, and started Plasma on
Wayland. The Daylight desktop, portrait launcher and sleeping-Spicy lock
wallpaper rendered. Unlocking with the live-session password `live` succeeded.

The boot review found and corrected a missing `user-setup` dependency, a
Daylight lock-screen contrast issue, and a redundant first-login theme
application that could prevent the welcome app from opening after a timeout.
Firmware menus also received Spicy's portrait and consistent live-account
settings for the fallback entry.

## Remaining release gates

This software-only VM produced KWin rendering stalls and D-Bus timeouts.
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
