# Virtual-machine validation

Start with a reproducible software baseline, then repeat the same image with
accelerated graphics on a host that supports KVM and VirGL. A software VM can
exercise boot and layout; its rendering stalls do not establish graphics-driver
support or the behavior of a real Intel, AMD or NVIDIA GPU.

## Boot a disposable live session

On a Linux host with Python 3, QEMU and OVMF installed:

```sh
./distro/tools/run-vm run distro/dist/spicy-linux-0.1-alpha-amd64.iso \
  --output distro/build/vm/software-1080p --profile software \
  --resolution 1920x1080
```

The launcher attaches the ISO read-only, creates fresh UEFI variables and
attaches no hard disk. The live account is `spicy`; its password is `live`.
No installer is present. Exit the VM before starting a new run, and use a new
output directory so earlier evidence stays intact. `--dry-run` prints the
configuration without creating files or starting QEMU.

Each run records `run.json` with the ISO's computed SHA-256, QEMU command and
start/end times; `vm-profile.json` contains the collector's VM metadata.
`qemu.log` and `serial.log` retain host-side messages. The exact OVMF firmware
and initial variable template are identified by SHA-256. This unsigned OVMF
profile exercises UEFI boot; it does not validate Secure Boot.

Use `--expected-sha256 DIGEST` to enforce a reviewed image checksum, and
`--max-seconds 900` to cap a run. A timeout exits 124; that is a time limit,
not a test result. Networking defaults to off. `--network user` opts into
QEMU's outbound user networking without forwarded host ports.

For KVM with VirGL:

```sh
./distro/tools/run-vm run distro/dist/spicy-linux-0.1-alpha-amd64.iso \
  --output distro/build/vm/accelerated-1080p --profile accelerated
```

This profile requires access to `/dev/kvm` and a GPU render node. GTK selects
the render node automatically. To select a specific GPU, use
`--display headless --render-node /dev/dri/renderD128` with the EGL backend.
It fails if the required devices are unavailable.
Confirm the actual renderer from the guest collector before recording an
accelerated result. `--display headless` uses EGL with the accelerated profile
and no display backend with the software profile.

## Run and capture inside the existing builder

The builder already includes Python, QEMU and OVMF. A software smoke boot
requires neither privileged Docker nor access to `/dev/kvm` or `/dev/dri`:

```sh
docker run --rm --name spicy-vm --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD,dst=/src" \
  spicy-builder:alpha python3 distro/tools/run-vm run \
  distro/dist/spicy-linux-0.1-alpha-amd64.iso \
  --output distro/build/vm/software-headless --profile software \
  --display headless --max-seconds 900
```

Run the capture command in a second terminal while the VM is running:

```sh
docker exec spicy-vm python3 distro/tools/run-vm capture \
  distro/build/vm/software-headless --name plymouth
docker exec spicy-vm python3 distro/tools/run-vm capture \
  distro/build/vm/software-headless --name desktop
docker exec spicy-vm python3 distro/tools/run-vm stop \
  distro/build/vm/software-headless
```

Capture Plymouth during the graphical splash, then capture the desktop after
Plasma appears. Each capture creates a PNG and timestamped JSON using QMP.
Choose a unique name for each frame. Use the same container and `/src` path for
capture and boot so QEMU writes to the intended evidence directory. Screenshots
are observations of the framebuffer; they do not automatically mark a gate
passed. A headless software boot supports smoke captures; use a visible GTK
display for interactive testing.

## Evidence and pass criteria

Record the ISO digest, profile, actual guest resolution/scaling, session type,
renderer and elapsed time alongside every result. Keep software and accelerated
results separate. The requested QEMU mode is a starting point; verify the actual
mode in Plasma Display Configuration and with `kscreen-doctor -o`.

Run `spicy-hardware-report` in the live guest after collecting observations.
Copy `vm-profile.json` into the guest and supply the digest from `run.json`:

```sh
spicy-hardware-report --kind vm --label software-1080p \
  --vm-profile /path/in/guest/vm-profile.json \
  --image-name spicy-linux-0.1-alpha-amd64.iso --iso-sha256 DIGEST \
  --output /path/in/guest/report
```

The externally supplied digest identifies the launcher-tested image; the
guest collector cannot independently prove which ISO was booted. Verify the
boot medium before linking the guest report. Reports saved only in the live
session disappear on shutdown; export them before stopping the VM. Consult
[the collector guide](hardware/README.md) for collection and review details.

| Gate | Check | Evidence required |
| --- | --- | --- |
| Boot | UEFI menu, Plymouth portrait and progress bar, automatic login, Plasma Wayland session | Timed captures and session log; report missing portrait even if the progress bar appears |
| Graphics | Open welcome, switch Daylight/Night Prowl, open common Qt/GTK/browser apps, lock/unlock, repeat for 30 minutes | Actual renderer, compositor/journal errors, operation results and any stalls |
| Scaling | 1280×720, 1920×1080, 2560×1440, ultrawide and 3840×2160; 100%, 125%, 150%, 200% where usable | Actual resolution/scaling and captures of desktop, welcome, sign-in and lock; no clipped controls or distorted art |
| Identity | Portrait boot, portrait-left sign-in, sleeping lock art, separate-tip paw with leading triangle hotspot | Captures and manual pointer/keyboard checks; preserve approved art |
| Accessibility | Keyboard navigation, focus, screen reader, both themes and reduced motion | Recorded steps and outcome; use a visible interactive session |
| Guest devices | Network when enabled, virtual input, display changes and reboot | Guest report and explicit results; virtual devices do not certify physical hardware |

The VM baseline precedes physical validation. Real Wi-Fi, Bluetooth, cameras,
audio, suspend/resume, external displays and discrete graphics remain separate
hardware gates. Installer testing and the signed update channel follow the
stability work in [the roadmap](ROADMAP.md).
