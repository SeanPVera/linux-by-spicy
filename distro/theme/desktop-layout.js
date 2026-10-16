// SPDX-License-Identifier: GPL-2.0-only
// Used only for a new desktop layout, not on every theme change.
var panel = new Panel;
panel.location = "bottom";
panel.height = gridUnit * 3;
var launcher = panel.addWidget("org.kde.plasma.kickoff");
launcher.currentConfigGroup = ["General"];
launcher.writeConfig("icon", "spicy-linux");
panel.addWidget("org.kde.plasma.icontasks");
panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("org.kde.plasma.digitalclock");
panel.addWidget("org.kde.plasma.showdesktop");
var screens = desktops();
for (var i = 0; i < screens.length; ++i) {
    screens[i].wallpaperPlugin = "org.kde.image";
    screens[i].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    screens[i].writeConfig("Image", "file:///usr/share/wallpapers/SpicyDaylight/contents/images/3840x2160.png");
}
