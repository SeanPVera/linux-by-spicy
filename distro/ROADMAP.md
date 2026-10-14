# Spicy Linux delivery plan

Spicy Linux is an everyday desktop built on Debian 13 and KDE Plasma 6.
Debian supplies the kernel, drivers, package manager and security updates.
Spicy packages supply the desktop experience and distribution identity.
The upstream kernel tree in this repository does not become a new kernel fork.

## 1. Live desktop alpha

The first deliverable is a USB-bootable desktop for reviewing the approved
Spicy artwork and exercising the complete login-to-desktop experience.

- Package the Daylight and Night Prowl themes, faithful illustrations, soft
  icons, Atkinson Hyperlegible font defaults and separate-tip paw cursors.
- Integrate the portrait boot screen, portrait-left sign-in screen, sleeping
  lock wallpaper and native welcome app.
- Check layouts across lower resolutions through 4K at fractional scaling.
- Build the ISO in a disposable container and inspect a real VM boot.
- Retain the Debian authentication components and packaged kernel.

The alpha has no installer or Spicy update channel. Generated packages,
wallpaper exports and ISO files stay out of Git; CI publishes build artifacts.

## 2. Hardware and everyday-use beta

Start with repeatable VM runs: compare the explicit software baseline with an
accelerated graphics profile where the host supports it. Exercise appearance
changes, reduced motion, boot portrait, sign-in and lock/unlock before extending
the campaign to physical machines. Record the exact ISO digest and VM profile
using [the VM workflow](VM_VALIDATION.md) and
[the validation kit](hardware/README.md). A software-only run does not establish
accelerated graphics stability.

Test real Intel/AMD laptops and desktops before describing hardware support.
Cover Wi-Fi, Bluetooth, audio, webcams, suspend/resume, external monitors and
common integrated/discrete graphics. Record the machine and firmware versions
with every result.

Review the actual Plasma desktop and common Qt, GTK and browser applications
at 720p, 1080p, 1440p, ultrawide and 4K, including 125%, 150% and 200% scaling.
Check keyboard navigation, focus indicators, screen-reader behavior, contrast
and reduced motion. Extend toolkit styling where a visible mismatch remains.

The exit condition is a documented hardware matrix and repeatable successful
daily-use sessions in both themes, with no unresolved login or data-loss bugs.

## 3. Installable beta

Integrate Calamares using maintained Debian components rather than writing an
installer. Develop and review its partitioning, encryption, account creation,
locale, bootloader and post-install steps in disposable VMs first.

Installed systems must disable the live account and automatic login, preserve
the user's chosen locale and theme, and receive Debian security updates.
Exercise clean installs, encrypted installs, installation beside another OS,
reboots and recovery. Test Secure Boot with the exact release image and
supported firmware; requesting signed packages alone is not verification.

## 4. Maintainable releases

Publish a signed APT repository for the Spicy packages, with signing keys held
outside this repository and a documented rotation/recovery process. Keep Debian
repositories as the source of the base operating system.

Produce versioned ISOs, checksums, signed release manifests, dependency/license
inventories and release notes. Test package upgrades and removals, including
release-identity restoration. Keep an earlier tested image available while a
candidate is evaluated.

## 5. First supported release

Choose a support window and tested hardware scope that the maintainers can
sustain. Document security-update handling, issue reporting, backups and
recovery. Promote a candidate only after installation, upgrade, accessibility
and hardware checks pass for the advertised scope.

Future features such as additional cat animations, a custom application store
or a different kernel should have their own justification and maintenance
budget after the everyday desktop is dependable.
