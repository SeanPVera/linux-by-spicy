# Spicy desktop on Debian ARM64 in Parallels

Use Debian 13 ARM64 with KDE Plasma inside Parallels on the Apple M4 Mac. An
existing Debian 13 ARM64 KDE VM can be upgraded in place after taking a snapshot;
there is no need to reinstall it. This setup installs the current Spicy artwork
and desktop packages. Debian supplies the ARM64 kernel, Qt, KDE and graphics
libraries. Spicy's two packages contain portable artwork, Xcursor data, QML and
Python/shell scripts and are audited as `Architecture: all`, with no compiled
executables or libraries. They use the same appearance fixes merged in PR #1.

The Spicy live ISO is amd64. For an M4 VM, start with Debian's ARM64 installer
and then install these desktop packages. This is an installed desktop setup;
it does not create an ARM64 Spicy live ISO or a signed update repository.

## Prepare the VM

1. If the existing VM already runs Debian 13 ARM64 and KDE, take a Parallels
   snapshot or clone and continue with package installation below. Keep earlier
   Spicy `.deb` files if you want to downgrade later.
2. For a separate new VM, download the ARM64 netinst image from
   [Debian's trixie installer page](https://www.debian.org/releases/trixie/debian-installer/).
   At the October 26, 2026 check, the image is
   [`debian-13.7.0-arm64-netinst.iso`](https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/debian-13.7.0-arm64-netinst.iso).
   Download its `SHA512SUMS` and `SHA512SUMS.sign` from the same directory and
   follow [Debian's verification instructions](https://www.debian.org/CD/verify.html).
   On macOS, `shasum -a 512 debian-13.7.0-arm64-netinst.iso` computes the image
   hash to compare with the verified checksum file. The Debian page supplies
   the current filename if the point release changes.

   The [official SHA256SUMS](https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/SHA256SUMS)
   retrieved for that filename on October 26 records:

   ```text
   6e93fa1759bd9d4b0fc11e938987de6967ee7de5297dac1be27c3a75cc17024b  debian-13.7.0-arm64-netinst.iso
   ```

   This is Debian's published checksum. The cloud preparation has not downloaded
   or booted this installer; verify your downloaded file and Debian's signature.
3. In Parallels choose **Install Windows, Linux, or macOS from an image file**
   and select that ARM64 ISO. Create a new virtual disk for this new VM. A useful
   starting allocation is 4 virtual CPUs, 4 GiB RAM (8 GiB if the Mac has enough
   available memory), and a 64 GiB virtual disk. Keep Parallels' normal Linux
   graphics defaults; do not force software rendering.
4. In Debian's installer create your normal user and select **KDE Plasma** plus
   the standard system utilities. Use the Debian packaged kernel. If you need
   to add KDE to an existing Debian ARM64 installation, run inside the guest:

   ```sh
   sudo apt update
   sudo apt install task-kde-desktop
   ```

   Sign out and select a Plasma Wayland session, then sign in. Parallels Tools
   are optional integration software: install them only through the current
   Parallels **Actions → Install Parallels Tools** flow if needed, following
   [Parallels' Linux guide](https://kb.parallels.com/en/115835). Check its
   [kernel compatibility guidance](https://kb.parallels.com/en/129963) for your
   installed Parallels version before changing kernels.

[Parallels' support matrix](https://kb.parallels.com/en/124223) lists Debian 13
for Apple silicon in Parallels Desktop 26/27; its version-20 section lists
Debian 12/11. Verify your existing Parallels version rather than assuming every
older version officially supports Debian 13. The
[ARM Linux installation guide](https://kb.parallels.com/en/128445) describes the
manual ISO flow. No Parallels purchase or upgrade is performed by this setup.

## Install the checked bundle

Get `spicy-debian-arm64-setup` from the matching GitHub Actions run and extract
it inside the Debian guest. In its extracted directory:

```sh
dpkg --print-architecture                    # must print arm64
sha256sum -c SHA256SUMS
python3 install.py --check
sudo apt update
sudo python3 install.py --install
spicy-welcome
```

The installer checks Debian 13, ARM64, file hashes, exact package names/versions
and `Architecture: all` before invoking apt. Apt resolves native dependencies
from Debian's ARM64 repositories and refuses a solution that removes installed
packages. It retains apt's normal confirmation prompt. Run `spicy-welcome` and
all appearance/test commands as your desktop user in the Plasma session.

Select Daylight or Night Prowl in Welcome, or use:

```sh
spicy-appearance --theme daylight
spicy-appearance --theme night-prowl
spicy-appearance --reduced-motion on
spicy-appearance --reduced-motion off
```

Spicy packages do not replace the Debian kernel. `spicy-release` is omitted
from this bundle, so the installed guest keeps Debian's operating-system
identity. Live-image automatic login, user/password and disk configuration are
not copied into the installed VM. The existing first-login helper leaves
installed-system users' panel layouts alone.

## Rebuild from a pinned source

You can build the portable packages directly inside Debian ARM64 without the
amd64 live-image Docker toolchain. Install these build tools inside the guest:

```sh
sudo apt update
sudo apt install git ca-certificates dpkg-dev python3-cairosvg python3-pil x11-apps
git clone --filter=blob:none --sparse https://github.com/SeanPVera/linux-by-spicy.git
cd linux-by-spicy
git sparse-checkout set distro
git fetch origin YOUR_VERIFIED_SOURCE_COMMIT
git checkout --detach FETCH_HEAD
python3 distro/tools/build.py
python3 distro/tools/build-arm64-setup.py --source-commit "$(git rev-parse HEAD)"
```

Use the full source SHA shown by the downloaded bundle's `bundle.json` or CI
run in place of `YOUR_VERIFIED_SOURCE_COMMIT`. The last command audits payloads,
selects the exact version recorded by the completed build and creates
`distro/dist/spicy-debian-arm64-setup`. It preserves older package archives and
refuses to replace an existing setup directory. Choose a new `--output` path
for another build. The generated checksums detect file corruption; use the
source SHA and trusted repository/Actions download to establish provenance.

## Update and roll back

Debian security and native library updates continue through Debian apt. For a
Spicy update, take another snapshot, retain the prior bundle, download the
new matching bundle, verify it and repeat the install command. There is no
automatic Spicy update channel in this alpha.

For a complete rollback, restore the pre-install Parallels snapshot or clone.
To remove just these packages, first choose Breeze in KDE System Settings
(global theme, application style, icons and cursors), then run:

```sh
sudo apt remove spicy-desktop spicy-artwork
```

Removal does not restore all of your earlier user preferences or remove apt
dependencies automatically. Use the snapshot for exact restoration. To return
to retained earlier Spicy packages, install their exact artwork and desktop
`.deb` paths together with `sudo apt install --allow-downgrades ...`, then select
the desired theme again. Never select packages with an ambiguous multi-version
wildcard.

## Verify on the M4 guest

Record package provenance before testing:

```sh
dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' spicy-artwork spicy-desktop
uname -m
sha256sum /usr/bin/spicy-appearance /usr/bin/spicy-desktop-test
spicy-desktop-test --help
```

Follow **Installed desktop follow-up** in the included `VM_VALIDATION.md`
(also `distro/VM_VALIDATION.md` in the source checkout). If Konsole or Spectacle
was omitted by a no-recommends apt configuration, install them inside the guest
with `sudo apt install konsole kde-spectacle`. The normal capture cycle can be
run from a guest terminal:

```sh
spicy-desktop-test --output "$HOME/spicy-arm64-capture" --cycle --capture --fresh-konsole
```

Use a new output directory each time. If capture fails, preserve that directory;
the independent state-only cycle can run separately without requesting another
capture:

```sh
spicy-desktop-test --output "$HOME/spicy-arm64-state" --cycle
```

Check Welcome's controls, both themes in existing/new Konsole windows, the
actual paw pointer and its tip hotspot, reduced motion, lock/unlock,
sign-out/sign-in, reboot persistence, scaling and sustained use in both themes.
Keep native ARM64 KWin renderer evidence distinct from software-container or
amd64 ISO results. A successful package install or saved preference is not a
visual, responsiveness or hardware-validation pass.

The earlier M4 Parallels alpha1 smoke test reported VirGL and a short successful
CLI theme cycle, with stale Konsole palettes and Breeze cursors still selected.
These alpha2 fixes need a fresh M4 test. Full graphics, interaction, persistence,
physical hardware and Secure Boot acceptance remain pending; this package
setup does not certify the amd64 ISO or firmware-enforced Secure Boot.
