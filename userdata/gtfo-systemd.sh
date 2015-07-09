# initial idea from
# http://without-systemd.org/wiki/index.php/How_to_remove_systemd_from_a_Debian_jessie/sid_installation
apt-get -y install sysvinit-core sysvinit sysvinit-utils
apt-get remove --purge --auto-remove systemd
cat >/etc/apt/preferences.d/systemd<<EOF
Package: systemd
Pin: origin ""
Pin-Priority: -1

Package: *systemd*
Pin: origin ""
Pin-Priority: -1
EOF
