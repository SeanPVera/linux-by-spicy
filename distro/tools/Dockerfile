FROM debian:13-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates dpkg-dev fakeroot python3 python3-pil python3-cairosvg \
    python3-pytest python3-yaml python3-pyside6.qtquick python3-pyside6.qtqml \
    librsvg2-bin x11-apps shellcheck desktop-file-utils fontconfig \
    fonts-atkinson-hyperlegible fonts-noto-core qt6-declarative-dev-tools \
    qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts \
    qml6-module-qtquick-window qml6-module-qtqml-workerscript \
    qml6-module-qt5compat-graphicaleffects xvfb xauth dbus-x11 qt6-style-kvantum \
    live-build debootstrap xorriso squashfs-tools dosfstools mtools \
    isolinux syslinux-common grub-pc-bin grub-efi-amd64-bin \
    qemu-system-x86 ovmf plymouth plymouth-themes plymouth-x11 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN apt-get update && apt-get install -y --no-install-recommends libqt6svg6 qt6-svg-plugins dbus-bin qemu-system-gui \
    && rm -rf /var/lib/apt/lists/*
