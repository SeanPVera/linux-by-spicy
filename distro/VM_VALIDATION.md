# Virtual-machine validation

Start with a reproducible software baseline, then repeat the same image with
accelerated graphics on a host that supports KVM and VirGL. A software VM can
exercise boot and layout; its rendering stalls do not establish graphics-driver
support or the behavior of a real Intel, AMD or NVIDIA GPU.

## Inspect host prerequisites

Record capabilities in the environment that will actually launch QEMU before
choosing an accelerated run:

```sh
./distro/tools/run-vm inspect --display headless \
  --output distro/build/vm/host-preflight.json
```

Use `--display gtk` for an interactive run, and add
`--render-node /dev/dri/renderD129` to inspect a specific headless EGL GPU.
No ISO or firmware is needed. The JSON records QEMU version, bounded help
probes for accelerator/device/display support, and existence, character-device
type and current-user read/write access for `/dev/kvm` and render nodes.
Existing evidence files are never overwritten; omit `--output` to print only.

Each CPU/graphics combination is `blocked` when a known prerequisite is absent,
or `unverified` when no known blocker was found. Missing or failed QEMU help
probes stay explicit. Help listings and file access do not initialize KVM,
EGL or GTK, prove host GL support, or certify the guest renderer. Launch and
guest observations must establish those separately. Run inspection inside a
container when QEMU will run there: host devices are unavailable to the
container unless explicitly passed through.
Debian splits GTK/EGL/VirGL support into the `qemu-system-gui` package;
installation of the base QEMU executable alone does not establish GL support.

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
Allow the graphical session to finish starting before switching virtual
terminals for diagnostics. A VT change during the SDDM-to-KWin handoff can
interrupt startup; record interventions and repeat an affected boot without
them before attributing the result to the image. Capture-only QMP commands
do not send guest keyboard input.
Dry runs check paths and construct the requested command; they skip host
capability checks and are not evidence that a configuration can boot.

Each run records `run.json` with the ISO's computed SHA-256, QEMU command and
start/end times; `vm-profile.json` contains the collector's VM metadata.
`qemu.log` and `serial.log` retain host-side messages. The exact OVMF firmware
and initial variable template are identified by SHA-256. This unsigned OVMF
profile exercises UEFI boot; it does not validate Secure Boot.
`host-capabilities.json` retains the launcher environment's prerequisite
inspection. `run.json` records the resolved CPU acceleration and graphics
choices in addition to the selected base profile.

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

For fault isolation, override CPU acceleration and graphics independently:

```sh
# Retain guest software rendering while removing TCG CPU emulation.
./distro/tools/run-vm run distro/dist/spicy-linux-0.1-alpha-amd64.iso \
  --output distro/build/vm/kvm-software-1080p --profile software --accel kvm

# Retain TCG while testing VirGL through an accessible GPU render node.
./distro/tools/run-vm run distro/dist/spicy-linux-0.1-alpha-amd64.iso \
  --output distro/build/vm/tcg-virgl-1080p --profile software --graphics virgl \
  --display headless --render-node /dev/dri/renderD128
```

`software` still defaults to TCG with `virtio-vga`; `accelerated` still defaults
to KVM with `virtio-vga-gl`. `--accel {tcg,kvm}` and
`--graphics {software,virgl}` replace only the indicated profile setting.
KVM requires accessible `/dev/kvm`; VirGL requires a render node and QEMU's
GL graphics device/backend support independently of the CPU accelerator.
Known missing prerequisites stop the launch before creating a run. The
launcher never silently switches CPU acceleration or graphics. QEMU itself
must initialize the selected backend successfully; verify guest KWin's actual
renderer even after a successful launch.

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

## Installed desktop follow-up

The alpha2 packages include `spicy-desktop-test` for an existing Plasma Wayland
desktop, including Debian ARM64 under Parallels. Its source-tree equivalent is
`python3 distro/scripts/spicy-desktop-test`; keep `spicy-hardware-report` beside
it if copying the source scripts. This test records installed-package evidence
without inventing a booted Spicy ISO digest.

Start from Konsole in the actual desktop session, as its normal user:

```sh
spicy-desktop-test --output "$HOME/Documents/spicy-inspect-01"
```

This collects observations without changing the theme or taking screenshots.
The desktop package supplies the KWin/KScreen query dependencies. Optional
captures and fresh-window comparisons also need Spectacle and Konsole, which
the package recommends. If recommendations were disabled, install them with
`sudo apt install spectacle konsole`.

For the palette/cursor follow-up, leave an existing Konsole window open and run:

```sh
spicy-desktop-test --output "$HOME/Documents/spicy-refresh-alpha2-01" \
  --cycle --capture --fresh-konsole
```

`--cycle` explicitly requests Daylight → Night Prowl → Daylight and leaves
Daylight selected when all stages complete. `--capture` includes the pointer in
full-desktop screenshots. `--fresh-konsole` additionally opens a separate,
temporary Konsole after each switch, captures it and closes only that probe's
process group. Compare the existing and new window's toolbar/tab-strip colors;
the terminal text area may deliberately use its own dark profile.

The test uses the current desktop environment without guessing display/socket
names or borrowing another process's environment. It requires a responding
Wayland KWin and active KScreen output before changing themes. A requested
initial capture must also succeed. A failed/partial theme request, lost desktop
access or failed capture stops the cycle; inspect `report.json` and the private
stdout/stderr files for the exact outcome. If a local agent's sandbox denies
desktop access, approve the specific test invocation as the normal desktop
user using its usual approval controls. Running as root is rejected.

Each helper/capture invocation records start, finish, elapsed time and status.
Appearance snapshots record their own sampling interval and bounded KConfig
probes. Evidence includes installed and selected helper hashes, collector/test
hashes, package versions/architectures, before/after cursor selection, saved
preferences, KWin/KScreen observations and journal extracts. An explicit
`--appearance /path/to/executable/spicy-appearance` can select a candidate
helper without replacing the installed one; its before/after hashes remain
distinct from the installed-file observations.

Outputs use a new private directory and never overwrite previous evidence.
Raw screenshots, command outputs and journals can contain private desktop
contents: review them before sharing. Command completion and a selected cursor
theme do not establish correct pixels, hotspot clicks, smooth motion or sustained
stability. Inspect the pointer and click with the leading triangle; review
cursor-loading errors as well as KWin's selected theme. All visual checks remain
unreviewed until a person or visual reviewer examines that evidence.

This focused cycle does not exercise Welcome's buttons, reduced motion,
lock/unlock, sign-out persistence, extended application use or the full scaling
matrix. Those procedures and the amd64 live-image gate remain separate.

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
