# Spicy Linux

A Debian 13 / KDE Plasma desktop inspired by Spicy the Cat: his real portrait,
ginger tabby markings, white socks, pink toe beans and red heart tag.

Distribution development lives under `distro/` on the `spicy-distro` branch.
The existing Linux kernel source tree is retained; the live image uses Debian's
supported packaged kernel.

The delivery milestones and acceptance criteria are in
[the distribution roadmap](distro/ROADMAP.md).

## First desktop alpha

- Daylight and Night Prowl color schemes, with a genuinely dark Night Prowl.
- Atkinson Hyperlegible as the interface font, with Noto fallback coverage.
- Faithful illustrated wallpapers, exported from 720p through 4K and for
  common 16:10 and ultrawide screens without stretching Spicy.
- Spicy Soft utility icons with Breeze fallback for the remaining applications.
- Soft Glass Qt application styling through Kvantum and KWin's blur effect.
- Little Tip cursors: a separate triangular pointing tip and trailing white paw
  with pink toe beans. Cursor sizes range from 24 to 128 pixels; text and resize
  shapes inherit Breeze so their meaning stays clear.
- Portrait-led boot, portrait-left sign-in, and sleeping-Spicy lock wallpaper.
- A native welcome app for appearance and reduced-motion preferences.

This milestone is a live desktop alpha. The graphical installer and signed
Spicy update repository are subsequent milestones. Do not use the alpha as
your only copy of important data.

## Build packages

On a Linux machine with Docker:

```sh
./distro/scripts/build-packages
```

The builder uses Debian 13 and produces three packages under `distro/dist/`:
`spicy-artwork`, `spicy-desktop`, and `spicy-release`.

To try the theme on an existing Debian 13 KDE installation, install the artwork
and desktop packages, then open **Welcome to Spicy Linux** from the launcher:

```sh
sudo apt install ./distro/dist/spicy-artwork_*.deb ./distro/dist/spicy-desktop_*.deb
spicy-welcome
```

`spicy-release` supplies the operating-system identity for the live distribution.
It is not needed to try the desktop theme on an existing Debian installation.
Its maintained diversion preserves Debian's original `/etc/os-release` and
restores it when the package is removed.

You can also switch explicitly from a running Plasma session:

```sh
spicy-appearance --theme daylight
spicy-appearance --theme night-prowl
spicy-appearance --reduced-motion on
```

Applying a theme does not reset existing panel layouts. New live-image users get
the Spicy launcher, task panel, system tray and clock on their first login.
Appearance commands have bounded waits so an unresponsive desktop cannot leave
the welcome app busy indefinitely. The app reports when a live refresh remains
incomplete; retry the same preference once the desktop is responding.

## Build the live image

```sh
./distro/scripts/build-live
```

This runs `live-build` in a privileged, disposable container because image
assembly requires filesystem mounts. It produces
`distro/dist/spicy-linux-0.1-alpha-amd64.iso` and its SHA-256 checksum.
The live session uses the account `spicy` and automatically signs in.
Its password is `live` if you lock the screen or sign out.
The image includes no installer; do not copy its live-session automatic-login
configuration into an installed system.

UEFI Secure Boot support is requested through Debian's signed boot packages.
Treat hardware support and Secure Boot compatibility as unverified until the
specific image is boot-tested on the intended machine.

## Validation

```sh
docker run --rm --user "$(id -u):$(id -g)" \
  -e XDG_CACHE_HOME=/tmp/spicy-cache \
  --mount "type=bind,src=$PWD,dst=/src" \
  spicy-builder:alpha sh distro/tools/check-native
```

The checks inspect compiled cursors, click hotspots, actual PNG sizes, text
contrast and the selected art direction. Real Qt renders exercise lower
resolutions through 3840×2160 at 100%, 125%, 150% and 200% scaling. Native
previews and JSON results go under `distro/build/previews/`.

Check the real Plymouth script renderer and Debian's initramfs asset copying in
a separate disposable container (the daemon requires root inside the container):

```sh
docker run --rm --mount "type=bind,src=$PWD,dst=/src" \
  spicy-builder:alpha python3 distro/tools/check-plymouth
```

The Qt checks do not substitute for a boot test of the complete Plasma desktop.
KWin composition is needed for blur; applications using other toolkits retain
their own application styling. Reduced motion is available from the welcome app.
The observed VM results and remaining release gates are recorded in
[the validation notes](distro/VALIDATION.md).

Start the next live-image validation with
[the VM workflow](distro/VM_VALIDATION.md). The
[hardware validation kit](distro/hardware/README.md) records image provenance,
graphics and session observations, and manual results without treating an
unperformed check as a pass. Physical hardware follows the VM campaign.

## Art direction and licensing

The selected choices are recorded in `distro/artwork/direction.json`, including
the custom **7A boot / 7C sign-in / 7B locked** sequence and the separate-tip
paw cursor. Original room photographs are not shipped as wallpaper assets.

New Spicy source code and original artwork use GPL-2.0-only. The derived Kvantum
theme geometry retains its upstream GPL-3.0-or-later license and attribution.
Debian, KDE, Breeze, Atkinson Hyperlegible and other dependencies retain their
respective upstream licenses. The upstream kernel's documentation and licensing
are available in `README`, `COPYING` and `LICENSES/`.
