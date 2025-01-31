"""
Copyright 2006-2018 Eygene A. Ryabinkin & contributors.

Module that supports distribution-specific functions.
"""
import platform
import os

import distro

# For the former we will just return the value, for an iterable
# we will walk through the values and will return the first
# one that corresponds to the existing file.
__DEF_OS_LOCATIONS = {
    'freebsd': ['/usr/local/share/certs/ca-root-nss.crt'],
    'openbsd': ['/etc/ssl/cert.pem'],
    'dragonfly': ['/etc/ssl/cert.pem'],
    'darwin': [
        # MacPorts, port curl-ca-bundle
        '/opt/local/share/curl/curl-ca-bundle.crt',
        # homebrew, package openssl
        '/usr/local/etc/openssl/cert.pem',
    ],
    'linux-ubuntu': ['/etc/ssl/certs/ca-certificates.crt'],
    'linux-debian': ['/etc/ssl/certs/ca-certificates.crt'],
    'linux-gentoo': ['/etc/ssl/certs/ca-certificates.crt'],
    'linux-fedora': ['/etc/pki/tls/certs/ca-bundle.crt'],
    'linux-redhat': ['/etc/pki/tls/certs/ca-bundle.crt'],
    'linux-suse': ['/etc/ssl/ca-bundle.pem'],
    'linux-opensuse': ['/etc/ssl/ca-bundle.pem'],
    'linux-arch': ['/etc/ssl/certs/ca-certificates.crt'],
}


def get_os_name():
    """
    Finds out OS name.  For non-Linux system it will be just a plain
    OS name (like FreeBSD), for Linux it will be "linux-<distro>",
    where <distro> is the name of the distribution, as returned by
    the first component of platform.linux_distribution.

    Return value will be all-lowercase to avoid confusion about
    proper name capitalisation.

    """
    os_name = platform.system().lower()

    if os_name.startswith('linux'):
        distro_name = distro.id()
        if distro_name:
            os_name = os_name + "-%s" % distro_name
        if os.path.exists('/etc/arch-release'):
            os_name = "linux-arch"

    return os_name


def get_os_sslcertfile_searchpath():
    """Returns search path for CA bundle for the current OS.

    We will return an iterable even if configuration has just
    a single value: it is easier for our callers to be sure
    that they can iterate over result.

    Returned value of None means that there is no search path
    at all.
    """
    os_name = get_os_name()
    location = __DEF_OS_LOCATIONS.get(os_name, None)

    return location


def get_os_sslcertfile():
    """
    Finds out the location for the distribution-specific
    CA certificate file bundle.

    Returns the location of the file or None if there is
    no known CA certificate file or all known locations
    correspond to non-existing filesystem objects.
    """

    location = get_os_sslcertfile_searchpath()
    if location is None:
        return None

    for l_file in location:
        assert isinstance(l_file, str)
        if os.path.exists(l_file) and (os.path.isfile(l_file) or
                                       os.path.islink(l_file)):
            return l_file

    return None
