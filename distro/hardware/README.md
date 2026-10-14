# Spicy Linux validation evidence

Start with virtual machines: compare the same exact ISO under the QEMU software
baseline and accelerated graphics where the host supports them. Follow
[the VM campaign](../VM_VALIDATION.md). A successful virtual desktop does not
establish physical hardware or Secure Boot support. Physical Intel/AMD machines
are the next campaign; the installer and signed update channel follow these
gates.

## Collect a run

`spicy-hardware-report` is installed in the live image. The source-tree equivalent
is `python3 distro/scripts/spicy-hardware-report`. Run it as the logged-in Plasma
user, without `sudo`, so session graphics and audio diagnostics reach the correct
session. Use a new output directory on a persistent disk: the live home directory
does not survive reboot.

Before booting, verify the image against the build's checksum:

```sh
cd distro/dist
sha256sum -c spicy-linux-0.1-alpha-amd64.iso.sha256
```

Record that digest and confirm that this is the image selected by the VM launcher
or written to the boot medium. In the guest, substitute its 64-digit digest:

```sh
spicy-hardware-report \
  --image-name spicy-linux-0.1-alpha-amd64.iso \
  --iso-sha256 REPLACE_WITH_VERIFIED_64_DIGIT_SHA256 \
  --kind vm --label qemu-software-cold-boot-01 \
  --output /media/spicy/TESTS/qemu-software-cold-boot-01
```

The supplied digest is labelled `supplied_by_tester`; the collector cannot prove
which image booted. When the ISO file is available in the session, use
`--iso /path/to/image.iso --expected-sha256 DIGEST` instead. A mismatch stops
collection. Each run records image name, digest and verification provenance;
`boot_origin_confirmed` stays false until the tester checks the boot medium.

For a VM, optionally add `--vm-profile /path/to/vm-profile.json`. The launcher
produces this file; these are the accepted declarations (other keys are rejected):

```json
{
  "hypervisor": "QEMU",
  "hypervisor_version": "record installed version",
  "machine": "q35",
  "cpu": "record selected CPU model",
  "firmware": "OVMF",
  "firmware_version": "record firmware package version",
  "graphics": "record selected virtual graphics device",
  "memory_mib": 4096,
  "acceleration": "record TCG or KVM and software or virgl renderer"
}
```

These fields describe the intended VM setup; guest diagnostics provide separate
observations of its actual renderer. For physical machines use `--kind physical`
and a generic label such as `intel-laptop-01`. The collector records manufacturer,
model, firmware version/date, kernel, PCI graphics/network/audio drivers and
selected package versions without collecting hardware serials.

## Review and fill the results

Each invocation creates two JSON files and refuses to overwrite prior runs:

- `observations.json`: session type, KWin and GLX renderer fields, display modes
  and scales, firmware/Secure Boot variables, package versions, device/service
  presence and declared VM setup. Missing commands, timeouts, unreadable firmware
  variables and failed probes remain explicit.
- `results.json`: 18 functional checks plus 80 resolution/scale/theme cases.
  Every case starts `untested`; detected devices and installed signed packages
  never become automatic passes.

Fill each result's `status`, `observed_at_utc`, `notes` and `evidence` with the
observed behavior, actual application versions and relative attachment filenames.
Keep `image` identical in both files. Set `boot_origin_confirmed` in both files
only after matching the selected boot medium to the recorded digest. A reviewed
run should state its scope and reviewer conclusion in `review_status`; this is
a record for review, not an automatic promotion decision.

| Status | Meaning |
| --- | --- |
| `untested` | No test was performed. |
| `pass` | The criterion was exercised and supported by evidence. |
| `fail` | The exercised criterion failed; describe reproduction and symptoms. |
| `blocked` | The setup or prerequisite prevented the test; explain what is needed. |
| `not_applicable` | The declared setup lacks this device/feature; explain why. |

Do not interpret VM Ethernet as Wi-Fi, virtual audio as laptop codec coverage, a
virtual suspend as laptop sleep validation, or plain UEFI boot as Secure Boot.
Tests requiring absent physical devices stay untested or have an explained
`not_applicable` status. A resolution unavailable in the VM or monitor is
`blocked` for the broader scaling campaign; it has not passed.

## Acceptance matrix

Use the same ISO digest for the software/accelerated VM comparison. Capture an
initial run, a run after each theme/scaling change when diagnosing a fault, and
a run after resume. Keep cold-boot and follow-up evidence linked by run labels.
The first VM exit gate requires a successful accelerated interactive session,
the approved Plymouth portrait, sign-in/lock/unlock, appearance switching and
the exercised scaling cases. Record software-only stalls as failures and retain
their scope; a good accelerated run does not turn them into passes.

| Check | Repeatable procedure and acceptance evidence |
| --- | --- |
| Image and boot | Cold-boot the selected digest; record VM profile or physical model/firmware, reach Wayland Plasma, confirm usable keyboard and pointer. |
| Plymouth portrait | Capture early boot, including the portrait and discreet progress bar. Portrait must retain its proportions; retain 7A. |
| Sign-in/lock | Sign out, authenticate, lock and unlock. Retain the approved 7C portrait-left sign-in and 7B sleeping lock artwork. |
| Graphics and themes | Use each theme for at least 30 minutes: welcome app, theme switches, window movement, blur, launcher, scrolling and browser video. Record stalls, timeouts, corruption or lost input, with reproduction and elapsed time. |
| Scaling | At 1024×768, 720p, 1280×800, 1366×768, 1080p, 1920×1200, 1440p, 2560×1600, ultrawide and 4K, exercise 100%, 125%, 150% and 200% in both themes. Record actual active mode/scale, readable controls, scroll reachability and screenshot evidence. Check Qt, GTK and browser dialogs; preserve artwork proportions and separate-tip paw gap/hotspot. |
| Secure Boot | Use an enforcing firmware profile with enrolled keys. Record firmware-menu evidence, exact-image boot, `SecureBoot=1`, `SetupMode=0` and `mokutil` when available. Resolve disagreements or unavailable evidence before a pass; signed package presence alone is insufficient. |
| Wi-Fi / Bluetooth | With real devices or declared USB passthrough: connect, use, disconnect and reconnect. Wi-Fi includes a sustained transfer; Bluetooth includes an actual peripheral interaction. Record device/controller model and driver, without addresses or network names. |
| Audio / webcam | Play and record sound; switch speaker/headphone/microphone routes. Preview/capture webcam and reopen it. In VMs record emulated or passed-through device scope. |
| Suspend / power | Perform five suspend/resume cycles, rechecking graphics, input, audio and network. On laptops test AC and battery, charge state and brightness. Capture fresh diagnostics after resume. |
| External displays | Hotplug/unplug/reconnect; change primary display and move windows. Test mixed DPI on two displays and verify pointer clicks, text, sign-in/lock layout and accessible dialogs. VM outputs do not establish physical connector support. |
| Applications / access | Record versions of Dolphin/Kate, a GTK app and Firefox ESR. Exercise keyboard-only navigation, visible focus, contrast, a named screen-reader flow and reduced-motion behavior. |

Save boot screenshots from the host when the guest cannot capture Plymouth.
For a graphics fault, capture diagnostics while the session is still responsive
and record whether the KWin renderer is software or hardware accelerated. The
GLX probe usually describes XWayland and is explicitly not KWin certification.
Keep optional journals locally until reviewed: journals can contain application
titles, usernames, network names and filesystem paths.

The collector omits host/login names, machine UUIDs, serial numbers, MAC/IP
addresses, SSIDs, EDID, raw journals and raw command errors. Review user-supplied
labels/profile values and screenshots before sharing. Reports have private file
permissions by default and do not upload anything.

No physical machine or Secure Boot result is claimed by this kit. Promote only
the exact image and explicitly tested scope recorded in the reviewed matrix.
