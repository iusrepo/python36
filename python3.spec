%global pybasever 3.2
%global alphatag  a1

%global pylibdir %{_libdir}/python%{pybasever}
%global dynload_dir %{pylibdir}/lib-dynload

# All bytecode files are now in a __pycache__ subdirectory, with a name
# reflecting the version of the bytecode (to permit sharing of python libraries
# between different runtimes)
# See http://www.python.org/dev/peps/pep-3147/
# For example,
#   foo/bar.py
# now has bytecode at:
#   foo/__pycache__/bar.cpython-32.pyc
#   foo/__pycache__/bar.cpython-32.pyo
%global bytecode_suffixes .cpython-32.py?

# Python's configure script defines SOVERSION, and this is used in the Makefile
# to determine INSTSONAME, the name of the libpython DSO:
#   LDLIBRARY='libpython$(VERSION).so'
#   INSTSONAME="$LDLIBRARY".$SOVERSION
# We mirror this here in order to make it easier to add the -gdb.py hooks.
# (if these get out of sync, the payload of the libs subpackage will fail
# and halt the build)
%global py_SOVERSION 1.0
%global py_INSTSONAME_optimized libpython%{pybasever}.so.%{py_SOVERSION}
%global py_INSTSONAME_debug     libpython%{pybasever}_d.so.%{py_SOVERSION}

%global with_debug_build 1

%global with_gdb_hooks 1

%global with_systemtap 1

# Change from yes to no to turn this off
%global with_computed_gotos yes

# We want to byte-compile the .py files within the packages using the new
# python3 binary.
# 
# Unfortunately, rpmbuild's infrastructure requires us to jump through some
# hoops to avoid byte-compiling with the system python 2 version:
#   /usr/lib/rpm/redhat/macros sets up build policy that (amongst other things)
# defines __os_install_post.  In particular, "brp-python-bytecompile" is
# invoked without an argument thus using the wrong version of python
# (/usr/bin/python, rather than the freshly built python), thus leading to
# numerous syntax errors, and incorrect magic numbers in the .pyc files.  We
# thus override __os_install_post to avoid invoking this script:
%global __os_install_post /usr/lib/rpm/redhat/brp-compress \
  %{!?__debug_package:/usr/lib/rpm/redhat/brp-strip %{__strip}} \
  /usr/lib/rpm/redhat/brp-strip-static-archive %{__strip} \
  /usr/lib/rpm/redhat/brp-strip-comment-note %{__strip} %{__objdump} \
  /usr/lib/rpm/redhat/brp-python-hardlink 
# to remove the invocation of brp-python-bytecompile, whilst keeping the
# invocation of brp-python-hardlink (since this should still work for python3
# pyc/pyo files)


# We need to get a newer configure generated out of configure.in for the following
# patches:
#   patch 55 (systemtap)
#   patch 103 (debug build)
#   patch 104 (more config flags)
#
# For patch 55 (systemtap), we need to get a new header for configure to use
#
# configure.in requires autoconf-2.65, but the version in Fedora is currently
# autoconf-2.66
#
# For now, we'll generate a patch to the generated configure script and
# pyconfig.h.in on a machine that has a local copy of autoconf 2.65
#
# Instructions on obtaining such a copy can be seen at
#   http://bugs.python.org/issue7997
#
# To make it easy to regenerate the patch, this specfile can be run in two
# ways:
# (i) regenerate_autotooling_patch  0 : the normal approach: prep the
# source tree using a pre-generated patch to the "configure" script, and do a
# full build
# (ii) regenerate_autotooling_patch 1 : intended to be run on a developer's
# workstation: prep the source tree without patching configure, then rerun a
# local copy of autoconf-2.65, regenerate the patch, then exit, without doing
# the rest of the build
%global regenerate_autotooling_patch 0


Summary: Version 3 of the Python programming language aka Python 3000
Name: python3
Version: %{pybasever}
Release: 0.1.%{alphatag}%{?dist}
License: Python
Group: Development/Languages
Source: http://python.org/ftp/python/%{version}/Python-%{version}%{alphatag}.tar.bz2

# Avoid having various bogus auto-generated Provides lines for the various
# python c modules' SONAMEs:
Source1: find-provides-without-python-sonames.sh
%global _use_internal_dependency_generator 0
%global __find_provides %{SOURCE1}

# Supply various useful macros for building python 3 modules:
#  __python3, python3_sitelib, python3_sitearch
Source2: macros.python3

# Supply an RPM macro "py_byte_compile" for the python3-devel subpackage
# to enable specfiles to selectively byte-compile individual files and paths
# with different Python runtimes as necessary:
Source3: macros.pybytecompile

# We install a collection of hooks for gdb that make it easier to debug
# executables linked against libpython (such as /usr/lib/python itself)
#
# These hooks are implemented in Python itself (though they are for the version
# of python that gdb is linked with, in this case Python 2.6)
#
# gdb-archer looks for them in the same path as the ELF file, with a -gdb.py suffix.
# We put them in the debuginfo package by installing them to e.g.:
#  /usr/lib/debug/usr/lib/libpython3.1.so.1.0.debug-gdb.py
#
# See https://fedoraproject.org/wiki/Features/EasierPythonDebugging for more
# information
#
# This is the version from 
#  http://bugs.python.org/issue8380
#
# This is Tools/gdb/libpython.py from:
#  http://bugs.python.org/file16902/port-gdb7-hooks-to-py3k.patch
# when applied to r80008 of the py3k branch
Source4: python-gdb.py

# Systemtap tapset to make it easier to use the systemtap static probes
# (actually a template; LIBRARY_PATH will get fixed up during install)
# Written by dmalcolm; not yet sent upstream
Source5: libpython.stp

# Example systemtap script using the tapset
# Written by wcohen, mjw, dmalcolm; not yet sent upstream
Source6: systemtap-example.stp

# Another example systemtap script that uses the tapset
# Written by dmalcolm; not yet sent upstream
Source7: pyfuntop.stp


# Fixup distutils/unixccompiler.py to remove standard library path from rpath:
# Was Patch0 in ivazquez' python3000 specfile:
Patch1:         Python-3.1.1-rpath.patch

# The four TestMIMEAudio tests fail due to "audiotest.au" not being packaged.
# It's simplest to remove them:
Patch3: python-3.2a1-remove-mimeaudio-tests.patch

# ImportTests.test_issue1267 in test_imp.py reads pydoc.py's shebang line and
# checks that it read it correctly.
#
# Since we modify the shebang lines in our packaging, we also need to modify
# the expected value in this test:
Patch4: python-3.2a1-apply-our-changes-to-expected-shebang-for-test_imp.patch

# Patch the Makefile.pre.in so that the generated Makefile doesn't try to build
# a libpythonMAJOR.MINOR.a (bug 550692):
Patch6: python-3.2a1-no-static-lib.patch

# Systemtap support: add statically-defined probe points
# Patch based on upstream bug: http://bugs.python.org/issue4111
# fixed up by mjw and wcohen for 2.6.2, then fixed up by dmalcolm for 2.6.4
# then rewritten by mjw (attachment 390110 of rhbz 545179); ported to 3.1.1 by
# dmalcolm
Patch8: python-3.2a1-systemtap.patch

Patch102: python-3.2a1-lib64.patch

# Patch to support building both optimized vs debug stacks DSO ABIs, sharing
# the same .py and .pyc files, using "_d.so" to signify a debug build of an
# extension module.
#
# Based on Debian's patch for the same, 
#  http://patch-tracker.debian.org/patch/series/view/python2.6/2.6.5-2/debug-build.dpatch
# 
# (which was itself based on the upstream Windows build), but with some
# changes:
#
#   * Debian's patch to dynload_shlib.c looks for module_d.so, then module.so,
# but this can potentially find a module built against the wrong DSO ABI.  We
# instead search for just module_d.so in a debug build
#
#   * We remove this change from configure.in's build of the Makefile:
#   SO=$DEBUG_EXT.so
# so that sysconfig.py:customize_compiler stays with shared_lib_extension='.so'
# on debug builds, so that UnixCCompiler.find_library_file can find system
# libraries (otherwise "make sharedlibs" fails to find system libraries,
# erroneously looking e.g. for "libffi_d.so" rather than "libffi.so")
#
#   * We change Lib/distutils/command/build_ext.py:build_ext.get_ext_filename
# to add the _d there, when building an extension.  This way, "make sharedlibs"
# can build ctypes, by finding the sysmtem libffi.so (rather than failing to
# find "libffi_d.so"), and builds the module as _ctypes_d.so
#   
#   * Similarly, update build_ext:get_libraries handling of Py_ENABLE_SHARED by
# appending "_d" to the python library's name for the debug configuration
#
#   * We modify Modules/makesetup to add the "_d" to the generated Makefile
# rules for the various Modules/*.so targets
#
# This may introduce issues when building an extension that links directly
# against another extension (e.g. users of NumPy?), but seems more robust when
# searching for external libraries
#
#   * We don't change Lib/distutils/command/build.py: build.build_purelib to
# embed plat_specifier, leaving it as is, as pure python builds should be
# unaffected by these differences (we'll be sharing the .py and .pyc files)
#
#   * We introduce DEBUG_SUFFIX as well as DEBUG_EXT:
#     - DEBUG_EXT is used by ELF files (names and SONAMEs); it will be "_d" for
# a debug build
#     - DEBUG_SUFFIX is used by filesystem paths; it will be "-debug" for a
# debug build
#
#   Both will be empty in an optimized build.  "_d" contains characters that
# are valid ELF metadata, but this leads to various ugly filesystem paths (such
# as the include path), and DEBUG_SUFFIX allows these paths to have more natural
# names.  Changing this requires changes elsewhere in the distutils code.
#
#   * We add DEBUG_SUFFIX to PYTHON in the Makefile, so that the two
# configurations build parallel-installable binaries with different names
# ("python-debug" vs "python").
#
#   * Similarly, we add DEBUG_SUFFIX within python-config and
#  python$(VERSION)-config, so that the two configuration get different paths
#  for these.
#
#  * Patch runtests.sh to support supplying a value for PYTHON, so that we can
# run the tests against each of the builds

Patch103: python-3.2a1-debug-build.patch

# Add configure-time support for the COUNT_ALLOCS and CALL_PROFILE options
# described at http://svn.python.org/projects/python/trunk/Misc/SpecialBuilds.txt
# so that if they are enabled, they will be in that build's pyconfig.h, so that
# extension modules will reliably use them
Patch104: python-3.1.2-more-configuration-flags.patch

# Add flags for statvfs.f_flag to the constant list in posixmodule (i.e. "os")
# (rhbz:553020); partially upstream as http://bugs.python.org/issue7647
Patch105: python-3.2a1-statvfs-f_flag-constants.patch

# Fix an incompatibility between pyexpat and the system expat-2.0.1 that led to
# a segfault running test_pyexpat.py (rhbz:610312)
# Sent upstream as http://bugs.python.org/issue9054
Patch110: python-3.1.2-fix-expat-issue9054.patch

# Fix race condition in parallel make that could lead to graminit.c failing
# to compile, or linker errors with "undefined reference to
# `_PyParser_Grammar'":
# Not yet sent upstream:
Patch111: python-3.2a1-fix-parallel-make.patch

# COUNT_ALLOCS is useful for debugging, but the upstream behaviour of always
# emitting debug info to stdout on exit is too verbose and makes it harder to
# use the debug build.  Add a "PYTHONDUMPCOUNTS" environment variable which
# must be set to enable the output on exit
# Not yet sent upstream:
Patch125: less-verbose-COUNT_ALLOCS.patch

# This is the generated patch to "configure"; see the description of
#   %{regenerate_autotooling_patch}
# above:
Patch300: autotool-intermediates.patch

BuildRoot: %{_tmppath}/%{name}-%{version}-root
BuildRequires: readline-devel, openssl-devel, gmp-devel
BuildRequires: ncurses-devel, gdbm-devel, zlib-devel, expat-devel
BuildRequires: libGL-devel gcc-c++ libX11-devel glibc-devel
BuildRequires: bzip2 tar /usr/bin/find pkgconfig tcl-devel tk-devel
BuildRequires: tix-devel bzip2-devel sqlite-devel
BuildRequires: autoconf
BuildRequires: db4-devel >= 4.7
BuildRequires: libffi-devel

%if 0%{?with_systemtap}
BuildRequires: systemtap-sdt-devel
%global tapsetdir      /usr/share/systemtap/tapset
%endif

URL: http://www.python.org/

# See notes in bug 532118:
Provides: python(abi) = %{pybasever}

%description
Python 3 is a new version of the language that is incompatible with the 2.x
line of releases. The language is mostly the same, but many details, especially
how built-in objects like dictionaries and strings work, have changed
considerably, and a lot of deprecated features have finally been removed.

%package libs
Summary:        Python 3 runtime libraries
Group:          Development/Libraries
#Requires:       %{name} = %{version}-%{release}

%description libs
This package contains files used to embed Python 3 into applications.

%package devel
Summary: Libraries and header files needed for Python 3 development
Group: Development/Libraries
Requires: %{name}%{?_isa} = %{version}-%{release}
Conflicts: %{name} < %{version}-%{release}

%description devel
This package contains libraries and header files used to build applications 
with and native libraries for Python 3

%package tools
Summary: A collection of tools included with Python 3
Group: Development/Tools
Requires: %{name} = %{version}-%{release}
Requires: %{name}-tkinter = %{version}-%{release}

%description tools
This package contains several tools included with Python 3

%package tkinter
Summary: A GUI toolkit for Python 3
Group: Development/Languages
BuildRequires:  tcl, tk
Requires: %{name} = %{version}-%{release}

%description tkinter
The Tkinter (Tk interface) program is an graphical user interface for
the Python scripting language.

%package test
Summary: The test modules from the main python 3 package
Group: Development/Languages
Requires: %{name} = %{version}-%{release}
Requires: %{name}-tools = %{version}-%{release}

%description test
The test modules from the main %{name} package.
These are in a separate package to save space, as they are almost never used
in production.

You might want to install the python3-test package if you're developing
python 3 code that uses more than just unittest and/or test_support.py.

%if 0%{?with_debug_build}
%package debug
Summary: Debug version of the Python 3 runtime
Group: Applications/System

# The debug build is an all-in-one package version of the regular build, and
# shares the same .py/.pyc files and directories as the regular build.  Hence
# we depend on all of the subpackages of the regular build:
Requires: %{name}%{?_isa} = %{version}-%{release}
Requires: %{name}-libs%{?_isa} = %{version}-%{release}
Requires: %{name}-devel%{?_isa} = %{version}-%{release}
Requires: %{name}-test%{?_isa} = %{version}-%{release}
Requires: %{name}-tkinter%{?_isa} = %{version}-%{release}
Requires: %{name}-tools%{?_isa} = %{version}-%{release}

%description debug
python3-debug provides a version of the Python 3 runtime with numerous debugging
features enabled, aimed at advanced Python users, such as developers of Python
extension modules.

This version uses more memory and will be slower than the regular Python 3 build,
but is useful for tracking down reference-counting issues, and other bugs.

The bytecodes are unchanged, so that .pyc files are compatible between the two
versions of Python 3, but the debugging features mean that C/C++ extension
modules are ABI-incompatible with those built for the standard runtime.

It shares installation directories with the standard Python 3 runtime, so that
.py and .pyc files can be shared.  All compiled extension modules gain a "_d"
suffix ("foo_d.so" rather than "foo.so") so that each Python 3 implementation
can load its own extensions.
%endif # with_debug_build

%prep
%setup -q -n Python-%{version}%{alphatag}
chmod +x %{SOURCE1}

%if 0%{?with_systemtap}
# Provide an example of usage of the tapset:
cp -a %{SOURCE6} .
cp -a %{SOURCE7} .
%endif # with_systemtap

# Ensure that we're using the system copy of various libraries, rather than
# copies shipped by upstream in the tarball:
#   Remove embedded copy of expat:
rm -r Modules/expat || exit 1

#   Remove embedded copy of libffi:
for SUBDIR in darwin libffi libffi_arm_wince libffi_msvc libffi_osx ; do
  rm -r Modules/_ctypes/$SUBDIR || exit 1 ;
done

#   Remove embedded copy of zlib:
rm -r Modules/zlib || exit 1

#
# Apply patches:
#
%patch1 -p1
%patch3 -p1 -b .remove-mimeaudio-tests
%patch4 -p1 -b .apply-our-changes-to-expected-shebang
%patch6 -p1 -b .no-static-lib

%if 0%{?with_systemtap}
%patch8 -p1 -b .systemtap
%endif

%if "%{_lib}" == "lib64"
%patch102 -p1
%endif

%patch103 -p1

%patch104 -p1 -b .more-configuration-flags

%patch105 -p1 -b .statvfs-f-flag-constants

%patch110 -p0 -b .fix-expat-issue9054

%patch111 -p1 -b .parallel-grammar

%patch125 -p1 -b .less-verbose-COUNT_ALLOCS

# Currently (2010-01-15), http://docs.python.org/library is for 2.6, and there
# are many differences between 2.6 and the Python 3 library.
#
# Fix up the URLs within pydoc to point at the documentation for this
# MAJOR.MINOR version:
#
sed --in-place \
    --expression="s|http://docs.python.org/library|http://docs.python.org/%{pybasever}/library|g" \
    Lib/pydoc.py || exit 1

%if ! 0%{regenerate_autotooling_patch}
# Normally we apply the patch to "configure"
# We don't apply the patch if we're working towards regenerating it
%patch300 -p0 -b .autotool-intermediates
%endif

%build
topdir=$(pwd)
export CFLAGS="$RPM_OPT_FLAGS -D_GNU_SOURCE -fPIC -fwrapv"
export CXXFLAGS="$RPM_OPT_FLAGS -D_GNU_SOURCE -fPIC -fwrapv"
export CPPFLAGS="`pkg-config --cflags-only-I libffi`"
export OPT="$RPM_OPT_FLAGS -D_GNU_SOURCE -fPIC -fwrapv"
export LINKCC="gcc"
export CFLAGS="$CFLAGS `pkg-config --cflags openssl`"
export LDFLAGS="$LDFLAGS `pkg-config --libs-only-L openssl`"

%if 0%{regenerate_autotooling_patch}
# If enabled, this code regenerates the patch to "configure", using a
# local copy of autoconf-2.65, then exits the build
#
# The following assumes that the copy is installed to ~/autoconf-2.65/bin
# as per these instructions:
#   http://bugs.python.org/issue7997

for f in pyconfig.h.in configure ; do
    cp $f $f.autotool-intermediates ;
done

# Rerun the autotools:
PATH=~/autoconf-2.65/bin:$PATH autoreconf

# Regenerate the patch:
gendiff . .autotool-intermediates > %{PATCH300}


# Exit the build
exit 1
%endif

# Define a function, for how to perform a "build" of python for a given
# configuration:
BuildPython() {
  ConfName=$1	      
  BinaryName=$2
  SymlinkName=$3
  ExtraConfigArgs=$4
  PathFixWithThisBinary=$5

  ConfDir=build/$ConfName

  echo STARTING: BUILD OF PYTHON FOR CONFIGURATION: $ConfName - %{_bindir}/$BinaryName
  mkdir -p $ConfDir

  pushd $ConfDir

  # Use the freshly created "configure" script, but in the directory two above:
  %global _configure $topdir/configure

%configure \
  --enable-ipv6 \
  --with-wide-unicode \
  --enable-shared \
%if 0%{?with_systemtap}
  --with-dtrace \
  --with-tapset-install-dir=%{tapsetdir} \
%endif
  --with-system-ffi \
  --with-system-expat \
  $ExtraConfigArgs \
  --with-computed-gotos=%{with_computed_gotos} \
  %{nil}


make OPT="$CFLAGS" %{?_smp_mflags}

  popd
  echo FINISHED: BUILD OF PYTHON FOR CONFIGURATION: $ConfDir
}

# Use "BuildPython" to support building with different configurations:

%if 0%{?with_debug_build}
BuildPython debug \
  python-debug \
  python%{pybasever}-debug \
%ifarch %{ix86} x86_64 ppc ppc64
  "--with-pydebug --with-tsc --with-count-allocs --with-call-profile" \
%else
  "--with-pydebug --with-count-allocs --with-call-profile" \
%endif
  false
%endif # with_debug_build

BuildPython optimized \
  python \
  python%{pybasever} \
  "" \
  true


%install
topdir=$(pwd)
rm -fr %{buildroot}
mkdir -p %{buildroot}%{_prefix} %{buildroot}%{_mandir}

InstallPython() {

  ConfName=$1	      
  PyInstSoName=$2

  ConfDir=build/$ConfName

  echo STARTING: INSTALL OF PYTHON FOR CONFIGURATION: $ConfName
  mkdir -p $ConfDir

  pushd $ConfDir

make install DESTDIR=%{buildroot} INSTALL="install -p"


# Copy up the gdb hooks into place; the python file will be autoloaded by gdb
# when visiting libpython.so, provided that the python file is installed to the
# same path as the library (or its .debug file) plus a "-gdb.py" suffix, e.g:
#  /usr/lib/debug/usr/lib64/libpython3.1.so.1.0.debug-gdb.py
# (note that the debug path is /usr/lib/debug for both 32/64 bit)
# 
# Initially I tried:
#  /usr/lib/libpython3.1.so.1.0-gdb.py
# but doing so generated noise when ldconfig was rerun (rhbz:562980)
#
%if 0%{?with_gdb_hooks}
DirHoldingGdbPy=%{_prefix}/lib/debug/%{_libdir}
PathOfGdbPy=$DirHoldingGdbPy/$PyInstSoName.debug-gdb.py

mkdir -p %{buildroot}$DirHoldingGdbPy
cp %{SOURCE4} %{buildroot}$PathOfGdbPy
%endif # with_gdb_hooks

  popd

  echo FINISHED: INSTALL OF PYTHON FOR CONFIGURATION: $ConfName
}

# Use "InstallPython" to support building with different configurations:

# Install the "debug" build first, so that we can move some files aside
%if 0%{?with_debug_build}
InstallPython debug \
  %{py_INSTSONAME_debug}
%endif # with_debug_build

# Now the optimized build:
InstallPython optimized \
  %{py_INSTSONAME_optimized}

mkdir -p ${RPM_BUILD_ROOT}%{pylibdir}/site-packages

mv ${RPM_BUILD_ROOT}%{_bindir}/2to3 ${RPM_BUILD_ROOT}%{_bindir}/python3-2to3

# Development tools
install -m755 -d ${RPM_BUILD_ROOT}%{pylibdir}/Tools
install Tools/README ${RPM_BUILD_ROOT}%{pylibdir}/Tools/
cp -ar Tools/freeze ${RPM_BUILD_ROOT}%{pylibdir}/Tools/
cp -ar Tools/i18n ${RPM_BUILD_ROOT}%{pylibdir}/Tools/
cp -ar Tools/pynche ${RPM_BUILD_ROOT}%{pylibdir}/Tools/
cp -ar Tools/scripts ${RPM_BUILD_ROOT}%{pylibdir}/Tools/

# Documentation tools
install -m755 -d %{buildroot}%{pylibdir}/Doc
cp -ar Doc/tools %{buildroot}%{pylibdir}/Doc/

# Demo scripts
cp -ar Demo %{buildroot}%{pylibdir}/

# Fix for bug #136654
rm -f %{buildroot}%{pylibdir}/email/test/data/audiotest.au %{buildroot}%{pylibdir}/test/audiotest.au

%if "%{_lib}" == "lib64"
install -d %{buildroot}/usr/lib/python%{pybasever}/site-packages
%endif

# Make python3-devel multilib-ready (bug #192747, #139911)
%global _pyconfig32_h pyconfig-32.h
%global _pyconfig64_h pyconfig-64.h

%ifarch ppc64 s390x x86_64 ia64 alpha sparc64
%global _pyconfig_h %{_pyconfig64_h}
%else
%global _pyconfig_h %{_pyconfig32_h}
%endif

%if 0%{?with_debug_build}
%global PyIncludeDirs python%{pybasever} python%{pybasever}-debug
%else
%global PyIncludeDirs python%{pybasever}
%endif

for PyIncludeDir in %{PyIncludeDirs} ; do
  mv %{buildroot}%{_includedir}/$PyIncludeDir/pyconfig.h \
     %{buildroot}%{_includedir}/$PyIncludeDir/%{_pyconfig_h}
  cat > %{buildroot}%{_includedir}/$PyIncludeDir/pyconfig.h << EOF
#include <bits/wordsize.h>

#if __WORDSIZE == 32
#include "%{_pyconfig32_h}"
#elif __WORDSIZE == 64
#include "%{_pyconfig64_h}"
#else
#error "Unknown word size"
#endif
EOF
done

# Fix for bug 201434: make sure distutils looks at the right pyconfig.h file
sed -i -e "s/'pyconfig.h'/'%{_pyconfig_h}'/" %{buildroot}%{pylibdir}/distutils/sysconfig.py

# Switch all shebangs to refer to the specific Python version.
LD_LIBRARY_PATH=./build/optimized ./build/optimized/python \
  Tools/scripts/pathfix.py \
  -i "%{_bindir}/python%{pybasever}" \
  %{buildroot}

# Remove shebang lines from .py files that aren't executable, and
# remove executability from .py files that don't have a shebang line:
find %{buildroot} -name \*.py \
  \( \( \! -perm /u+x,g+x,o+x -exec sed -e '/^#!/Q 0' -e 'Q 1' {} \; \
  -print -exec sed -i '1d' {} \; \) -o \( \
  -perm /u+x,g+x,o+x ! -exec grep -m 1 -q '^#!' {} \; \
  -exec chmod a-x {} \; \) \)

# .xpm and .xbm files should not be executable:
find %{buildroot} \
  \( -name \*.xbm -o -name \*.xpm -o -name \*.xpm.1 \) \
  -exec chmod a-x {} \;

# Remove executable flag from files that shouldn't have it:
chmod a-x \
  %{buildroot}%{pylibdir}/Demo/comparisons/patterns \
  %{buildroot}%{pylibdir}/distutils/tests/Setup.sample \
  %{buildroot}%{pylibdir}/Demo/rpc/test \
  %{buildroot}%{pylibdir}/Tools/README \
  %{buildroot}%{pylibdir}/Demo/scripts/newslist.doc \
  %{buildroot}%{pylibdir}/Demo/md5test/foo

# Get rid of DOS batch files:
find %{buildroot} -name \*.bat -exec rm {} \;

# Get rid of backup files:
find %{buildroot}/ -name "*~" -exec rm -f {} \;
find . -name "*~" -exec rm -f {} \;
rm -f %{buildroot}%{pylibdir}/LICENSE.txt
# Junk, no point in putting in -test sub-pkg
rm -f ${RPM_BUILD_ROOT}/%{pylibdir}/idlelib/testcode.py*

# Get rid of stray patch file from buildroot:
rm -f %{buildroot}%{pylibdir}/test/test_imp.py.apply-our-changes-to-expected-shebang # from patch 4

# Fix end-of-line encodings:
find %{buildroot}/ -name \*.py -exec sed -i 's/\r//' {} \;

# Fix an encoding:
iconv -f iso8859-1 -t utf-8 %{buildroot}/%{pylibdir}/Demo/rpc/README > README.conv && mv -f README.conv %{buildroot}/%{pylibdir}/Demo/rpc/README

# Note that 
#  %{pylibdir}/Demo/distutils/test2to3/setup.py
# is in iso-8859-1 encoding, and that this is deliberate; this is test data
# for the 2to3 tool, and one of the functions of the 2to3 tool is to fixup
# character encodings within python source code

# Do bytecompilation with the new interpreter.
LD_LIBRARY_PATH=. /usr/lib/rpm/brp-python-bytecompile ./python

# Fixup permissions for shared libraries from non-standard 555 to standard 755:
find %{buildroot} \
    -perm 555 -exec chmod 755 {} \;

mkdir -p %{buildroot}/%{_sysconfdir}/rpm
install -m 644 %{SOURCE2} %{buildroot}/%{_sysconfdir}/rpm
install -m 644 %{SOURCE3} %{buildroot}/%{_sysconfdir}/rpm

# Ensure that the curses module was linked against libncursesw.so, rather than
# libncurses.so (bug 539917)
ldd %{buildroot}/%{dynload_dir}/_curses*.so \
    | grep curses \
    | grep libncurses.so && (echo "_curses.so linked against libncurses.so" ; exit 1)

# Ensure that the debug modules are linked against the debug libpython, and
# likewise for the optimized modules and libpython:
for Module in %{buildroot}/%{dynload_dir}/*.so ; do
    case $Module in
    *_d.so)
        ldd $Module | grep %{py_INSTSONAME_optimized} &&
            (echo Debug module $Module linked against optimized %{py_INSTSONAME_optimized} ; exi 1)
            
        ;;
    *)
        ldd $Module | grep %{py_INSTSONAME_debug} &&
            (echo Optimized module $Module linked against debug %{py_INSTSONAME_optimized} ; exi 1)
        ;;
    esac
done

#
# Systemtap hooks:
#
%if 0%{?with_systemtap}
# Install a tapset for this libpython into tapsetdir, fixing up the path to the
# library:
mkdir -p %{buildroot}%{tapsetdir}
%ifarch ppc64 s390x x86_64 ia64 alpha sparc64
%global libpython_stp_optimized libpython%{pybasever}-64.stp
%global libpython_stp_debug     libpython%{pybasever}-debug-64.stp
%else
%global libpython_stp_optimized libpython%{pybasever}-32.stp
%global libpython_stp_debug     libpython%{pybasever}-debug-32.stp
%endif

sed \
   -e "s|LIBRARY_PATH|%{_libdir}/%{py_INSTSONAME_optimized}|" \
   %{SOURCE6} \
   > %{buildroot}%{tapsetdir}/%{libpython_stp_optimized}

%if 0%{?with_debug_build}
sed \
   -e "s|LIBRARY_PATH|%{_libdir}/%{py_INSTSONAME_debug}|" \
   %{SOURCE6} \
   > %{buildroot}%{tapsetdir}/%{libpython_stp_debug}
%endif # with_debug_build

%endif # with_systemtap

%check
topdir=$(pwd)
CheckPython() {
  ConfName=$1	      
  ConfDir=build/$ConfName

  echo STARTING: CHECKING OF PYTHON FOR CONFIGURATION: $ConfName

# Run the upstream test suite, using the "runtests.sh" harness from the upstream
# tarball.
# I'm seeing occasional hangs in some http tests when running the test suite
# inside Koji.  For that reason I exclude them

LD_LIBRARY_PATH=$ConfDir PYTHON=$ConfDir/python $topdir/runtests.sh -x test_httplib test_http_cookies

# Note that we're running the tests using the version of the code in the builddir,
# not in the buildroot.

# The harness only emits the names of the test scripts it ran, along with a
# summary of the form:
#   2 BAD
# 313 GOOD
#  22 SKIPPED
# 337 total
# As a byproduct it writes files "GOOD", "BAD", "SKIPPED", listing names of
# files (e.g. "test_imp") along with a subdirectory OUT containing files of the
# form $TEST.out
# Each such logfile starts with a line indicating the name of the test

# Output the logs from failing tests, so that they are captured in the rpmbuild
# log:
for TESTNAME in $(cat BAD); do
  cat OUT/$TESTNAME.out ; 
done

# There are 5 expected BAD results here:
#
# (1) test_distutils.py: tries to build an RPM inside the rpmbuild; I'll simply
# let this one fail for now (has trouble linking against -lpython3.1; perhaps
# LD_LIBRARY_PATH is being discarded somewhere?)
#
# (2) test_imp.py: ImportTests.test_issue1267 in test_imp.py reads pydoc.py's
# shebang line and checks that it read it correctly.tests that the shebang line
# is as expected.  Unfortunately if we patch this up in the buildir (in the
# build phase), then the "make install" will try to reference
# /usr/bin/python%{pybasever} which won't exist on a clean build environment.
# So we fix up the shebang lines after this in the install phase, and expect
# this test to fail in the check phase.  It ought to pass when run on the built
# RPMs
#
# (3) test_socket.py:testSockName can fail here if DNS isn't properly set up:
#     my_ip_addr = socket.gethostbyname(socket.gethostname())
# socket.gaierror: [Errno -2] Name or service not known
#
# (4) test_subprocess: merely get "errors occurred"
#
# (5) test_telnet: can get a "socket.error: [Errno 104] Connection reset by peer"
#
# Some additional tests fail when running the test suite as non-root outside of
# the build, due to permissions issues.

  echo FINISHED: CHECKING OF PYTHON FOR CONFIGURATION: $ConfDir

}

# Check each of the configurations:
%if 0%{?with_debug_build}
CheckPython debug
%endif # with_debug_build
CheckPython optimized


%clean
rm -fr %{buildroot}

%post libs -p /sbin/ldconfig

%postun libs -p /sbin/ldconfig

%files
%defattr(-, root, root)
%doc LICENSE README
%{_bindir}/pydoc*
%{_bindir}/python3
%{_bindir}/python%{pybasever}
%{_mandir}/*/*
%dir %{pylibdir}
%dir %{dynload_dir}
%{dynload_dir}/Python-%{version}%{alphatag}-py%{pybasever}.egg-info
%{dynload_dir}/_bisect.so
%{dynload_dir}/_codecs_cn.so
%{dynload_dir}/_codecs_hk.so
%{dynload_dir}/_codecs_iso2022.so
%{dynload_dir}/_codecs_jp.so
%{dynload_dir}/_codecs_kr.so
%{dynload_dir}/_codecs_tw.so
%{dynload_dir}/_collections.so
%{dynload_dir}/_csv.so
%{dynload_dir}/_ctypes.so
%{dynload_dir}/_curses.so
%{dynload_dir}/_curses_panel.so
%{dynload_dir}/_dbm.so
%{dynload_dir}/_elementtree.so
%{dynload_dir}/_gdbm.so
%{dynload_dir}/_hashlib.so
%{dynload_dir}/_heapq.so
%{dynload_dir}/_json.so
%{dynload_dir}/_lsprof.so
%{dynload_dir}/_multibytecodec.so
%{dynload_dir}/_multiprocessing.so
%{dynload_dir}/_pickle.so
%{dynload_dir}/_posixsubprocess.so
%{dynload_dir}/_random.so
%{dynload_dir}/_socket.so
%{dynload_dir}/_sqlite3.so
%{dynload_dir}/_ssl.so
%{dynload_dir}/_struct.so
%{dynload_dir}/array.so
%{dynload_dir}/atexit.so
%{dynload_dir}/audioop.so
%{dynload_dir}/binascii.so
%{dynload_dir}/bz2.so
%{dynload_dir}/cmath.so
%{dynload_dir}/crypt.so
%{dynload_dir}/_datetime.so
%{dynload_dir}/fcntl.so
%{dynload_dir}/grp.so
%{dynload_dir}/itertools.so
%{dynload_dir}/math.so
%{dynload_dir}/mmap.so
%{dynload_dir}/nis.so
%{dynload_dir}/operator.so
%{dynload_dir}/ossaudiodev.so
%{dynload_dir}/parser.so
%{dynload_dir}/pyexpat.so
%{dynload_dir}/readline.so
%{dynload_dir}/resource.so
%{dynload_dir}/select.so
%{dynload_dir}/spwd.so
%{dynload_dir}/syslog.so
%{dynload_dir}/termios.so
%{dynload_dir}/time.so
%{dynload_dir}/unicodedata.so
%{dynload_dir}/zlib.so

%dir %{pylibdir}/site-packages
%{pylibdir}/site-packages/README
%{pylibdir}/*.py
%{pylibdir}/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/wsgiref.egg-info
%dir %{pylibdir}/ctypes
%{pylibdir}/ctypes/*.py
%{pylibdir}/ctypes/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/ctypes/macholib
%{pylibdir}/curses
%dir %{pylibdir}/dbm
%{pylibdir}/dbm/*.py
%{pylibdir}/dbm/__pycache__/*%{bytecode_suffixes}
%dir %{pylibdir}/distutils
%{pylibdir}/distutils/*.py
%{pylibdir}/distutils/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/distutils/README
%{pylibdir}/distutils/command
%dir %{pylibdir}/email
%{pylibdir}/email/*.py
%{pylibdir}/email/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/email/mime
%{pylibdir}/encodings
%{pylibdir}/html
%{pylibdir}/http
%{pylibdir}/idlelib
%dir %{pylibdir}/importlib
%{pylibdir}/importlib/*.py
%{pylibdir}/importlib/__pycache__/*%{bytecode_suffixes}
%dir %{pylibdir}/json
%{pylibdir}/json/*.py
%{pylibdir}/json/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/lib2to3
%exclude %{pylibdir}/lib2to3/tests
%{pylibdir}/logging
%{pylibdir}/multiprocessing
%{pylibdir}/plat-linux2
%{pylibdir}/pydoc_data
%dir %{pylibdir}/sqlite3
%{pylibdir}/sqlite3/*.py
%{pylibdir}/sqlite3/__pycache__/*%{bytecode_suffixes}
%dir %{pylibdir}/test
%{pylibdir}/test/__init__.py
%{pylibdir}/test/__pycache__/__init__%{bytecode_suffixes}
%dir %{pylibdir}/unittest
%{pylibdir}/unittest/*.py
%{pylibdir}/unittest/__pycache__/*%{bytecode_suffixes}
%{pylibdir}/urllib
%{pylibdir}/wsgiref
%{pylibdir}/xml
%{pylibdir}/xmlrpc
%if "%{_lib}" == "lib64"
%attr(0755,root,root) %dir %{_prefix}/lib/python%{pybasever}
%attr(0755,root,root) %dir %{_prefix}/lib/python%{pybasever}/site-packages
%endif

# "Makefile" and the config-32/64.h file are needed by
# distutils/sysconfig.py:_init_posix(), so we include them in the core
# package, along with their parent directories (bug 531901):
%dir %{pylibdir}/config
%{pylibdir}/config/Makefile
%dir %{_includedir}/python%{pybasever}
%{_includedir}/python%{pybasever}/%{_pyconfig_h}

%files libs
%defattr(-,root,root,-)
%{_libdir}/%{py_INSTSONAME_optimized}
%if 0%{?with_systemtap}
%{tapsetdir}/%{libpython_stp_optimized}
%doc systemtap-example.stp pyfuntop.stp
%endif

%files devel
%defattr(-,root,root)
%{pylibdir}/config/*
%exclude %{pylibdir}/config/Makefile
/usr/include/python%{pybasever}/*.h
%exclude /usr/include/python%{pybasever}/%{_pyconfig_h}
%doc Misc/README.valgrind Misc/valgrind-python.supp Misc/gdbinit
%{_bindir}/python3-config
%{_bindir}/python%{pybasever}-config
%{_libdir}/libpython%{pybasever}.so
%{_libdir}/pkgconfig/python-%{pybasever}.pc
%{_libdir}/pkgconfig/python3.pc
%config(noreplace) %{_sysconfdir}/rpm/macros.python3
%config(noreplace) %{_sysconfdir}/rpm/macros.pybytecompile

%files tools
%defattr(-,root,root,755)
%{_bindir}/python3-2to3
%{_bindir}/idle*
%{pylibdir}/Tools
%doc %{pylibdir}/Demo
%exclude %{pylibdir}/Demo/distutils
%exclude %{pylibdir}/Demo/md5test
%doc %{pylibdir}/Doc

%files tkinter
%defattr(-,root,root,755)
%{pylibdir}/tkinter
%exclude %{pylibdir}/tkinter/test
%{dynload_dir}/_tkinter.so

%files test
%defattr(-, root, root)
%{pylibdir}/ctypes/test
%{pylibdir}/distutils/tests
%{pylibdir}/email/test
%{pylibdir}/importlib/test
%{pylibdir}/json/tests
%{pylibdir}/sqlite3/test
%{pylibdir}/test
%{dynload_dir}/_ctypes_test.so
%{dynload_dir}/_testcapi.so
%{pylibdir}/lib2to3/tests
%doc %{pylibdir}/Demo/distutils
%doc %{pylibdir}/Demo/md5test
%{pylibdir}/tkinter/test
%dir %{pylibdir}/unittest/test
%{pylibdir}/unittest/test/*.py
%{pylibdir}/unittest/test/__pycache__/*%{bytecode_suffixes}


# We don't bother splitting the debug build out into further subpackages:
# if you need it, you're probably a developer.

# Hence the manifest is the combination of analogous files in the manifests of
# all of the other subpackages

%if 0%{?with_debug_build}
%files debug
%defattr(-,root,root,-)

# Analog of the core subpackage's files:
%{_bindir}/python3-debug
%{_bindir}/python%{pybasever}-debug

# ...with debug builds of the built-in "extension" modules:
%{dynload_dir}/_bisect_d.so
%{dynload_dir}/_codecs_cn_d.so
%{dynload_dir}/_codecs_hk_d.so
%{dynload_dir}/_codecs_iso2022_d.so
%{dynload_dir}/_codecs_jp_d.so
%{dynload_dir}/_codecs_kr_d.so
%{dynload_dir}/_codecs_tw_d.so
%{dynload_dir}/_collections_d.so
%{dynload_dir}/_csv_d.so
%{dynload_dir}/_ctypes_d.so
%{dynload_dir}/_curses_d.so
%{dynload_dir}/_curses_panel_d.so
%{dynload_dir}/_dbm_d.so
%{dynload_dir}/_elementtree_d.so
%{dynload_dir}/_gdbm_d.so
%{dynload_dir}/_hashlib_d.so
%{dynload_dir}/_heapq_d.so
%{dynload_dir}/_json_d.so
%{dynload_dir}/_lsprof_d.so
%{dynload_dir}/_md5_d.so
%{dynload_dir}/_multibytecodec_d.so
%{dynload_dir}/_multiprocessing_d.so
%{dynload_dir}/_pickle_d.so
%{dynload_dir}/_posixsubprocess_d.so
%{dynload_dir}/_random_d.so
%{dynload_dir}/_sha1_d.so
%{dynload_dir}/_sha256_d.so
%{dynload_dir}/_sha512_d.so
%{dynload_dir}/_socket_d.so
%{dynload_dir}/_sqlite3_d.so
%{dynload_dir}/_ssl_d.so
%{dynload_dir}/_struct_d.so
%{dynload_dir}/array_d.so
%{dynload_dir}/atexit_d.so
%{dynload_dir}/audioop_d.so
%{dynload_dir}/binascii_d.so
%{dynload_dir}/bz2_d.so
%{dynload_dir}/cmath_d.so
%{dynload_dir}/crypt_d.so
%{dynload_dir}/_datetime_d.so
%{dynload_dir}/fcntl_d.so
%{dynload_dir}/grp_d.so
%{dynload_dir}/itertools_d.so
%{dynload_dir}/math_d.so
%{dynload_dir}/mmap_d.so
%{dynload_dir}/nis_d.so
%{dynload_dir}/operator_d.so
%{dynload_dir}/ossaudiodev_d.so
%{dynload_dir}/parser_d.so
%{dynload_dir}/pyexpat_d.so
%{dynload_dir}/readline_d.so
%{dynload_dir}/resource_d.so
%{dynload_dir}/select_d.so
%{dynload_dir}/spwd_d.so
%{dynload_dir}/syslog_d.so
%{dynload_dir}/termios_d.so
%{dynload_dir}/time_d.so
%{dynload_dir}/unicodedata_d.so
%{dynload_dir}/zlib_d.so

# No need to split things out the "Makefile" and the config-32/64.h file as we
# do for the regular build above (bug 531901), since they're all in one package
# now; they're listed below, under "-devel":

# Analog of the -libs subpackage's files:
%{_libdir}/%{py_INSTSONAME_debug}
%if 0%{?with_systemtap}
%{tapsetdir}/%{libpython_stp_debug}
%endif

# Analog of the -devel subpackage's files:
%dir %{pylibdir}/config-debug
%{pylibdir}/config-debug/*
%{_includedir}/python%{pybasever}-debug/*.h
%{_bindir}/python3-debug-config
%{_bindir}/python%{pybasever}-debug-config
%{_libdir}/libpython%{pybasever}_d.so
%{_libdir}/pkgconfig/python-%{pybasever}-debug.pc
%{_libdir}/pkgconfig/python3-debug.pc

# Analog of the -tools subpackage's files:
#  None for now; we could build precanned versions that have the appropriate
# shebang if needed

# Analog  of the tkinter subpackage's files:
%{dynload_dir}/_tkinter_d.so

# Analog  of the -test subpackage's files:
%{dynload_dir}/_ctypes_test_d.so
%{dynload_dir}/_testcapi_d.so

%endif # with_debug_build

# We put the debug-gdb.py file inside /usr/lib/debug to avoid noise from
# ldconfig (rhbz:562980).
# 
# The /usr/lib/rpm/redhat/macros defines %__debug_package to use
# debugfiles.list, and it appears that everything below /usr/lib/debug and
# (/usr/src/debug) gets added to this file (via LISTFILES) in
# /usr/lib/rpm/find-debuginfo.sh
# 
# Hence by installing it below /usr/lib/debug we ensure it is added to the
# -debuginfo subpackage
# (if it doesn't, then the rpmbuild ought to fail since the debug-gdb.py 
# payload file would be unpackaged)


%changelog
* Sun Aug 22 2010 Thomas Spura <tomspur@fedoraproject.org> - 3.2-0.1.a1
- on 64bit "stdlib" was still "/usr/lib/python*" (modify *lib64.patch)
- make find-provides-without-python-sonames.sh 64bit aware

* Sat Aug 21 2010 David Malcolm <dmalcolm@redhat.com> - 3.2-0.0.a1
- 3.2a1; add alphatag
- rework %%files in the light of PEP 3147 (__pycache__)
- drop our configuration patch to Setup.dist (patch 0): setup.py should do a
better job of things, and the %%files explicitly lists our modules (r82746
appears to break the old way of doing things).  This leads to various modules
changing from "foomodule.so" to "foo.so".  It also leads to the optimized build
dropping the _sha1, _sha256 and _sha512 modules, but these are provided by
_hashlib; _weakref becomes a builtin module; xxsubtype goes away (it's only for
testing/devel purposes)
- fixup patches 3, 4, 6, 8, 102, 103, 105, 111 for the rebase
- remove upstream patches: 7 (system expat), 106, 107, 108 (audioop reformat
plus CVE-2010-1634 and CVE-2010-2089), 109 (CVE-2008-5983)
- add machinery for rebuilding "configure" and friends, using the correct
version of autoconf (patch 300)
- patch the debug build's usage of COUNT_ALLOCS to be less verbose (patch 125)
- "modulator" was removed upstream
- drop "-b" from patch applications affecting .py files to avoid littering the
installation tree

* Thu Aug 19 2010 Toshio Kuratomi <toshio@fedoraproject.org> - 3.1.2-13
- Turn on computed-gotos.
- Fix for parallel make and graminit.c

* Fri Jul  2 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-12
- rebuild

* Fri Jul  2 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-11
- Fix an incompatibility between pyexpat and the system expat-2.0.1 that led to
a segfault running test_pyexpat.py (patch 110; upstream issue 9054; rhbz#610312)

* Fri Jun  4 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-10
- ensure that the compiler is invoked with "-fwrapv" (rhbz#594819)
- reformat whitespace in audioop.c (patch 106)
- CVE-2010-1634: fix various integer overflow checks in the audioop
module (patch 107)
- CVE-2010-2089: further checks within the audioop module (patch 108)
- CVE-2008-5983: the new PySys_SetArgvEx entry point from r81399 (patch 109)

* Thu May 27 2010 Dan Horák <dan[at]danny.cz> - 3.1.2-9
- reading the timestamp counter is available only on some arches (see Python/ceval.c)

* Wed May 26 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-8
- add flags for statvfs.f_flag to the constant list in posixmodule (i.e. "os")
(patch 105)

* Tue May 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-7
- add configure-time support for COUNT_ALLOCS and CALL_PROFILE debug options
(patch 104); enable them and the WITH_TSC option within the debug build

* Mon May 24 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-6
- build and install two different configurations of Python 3: debug and
standard, packaging the debug build in a new "python3-debug" subpackage
(patch 103)

* Tue Apr 13 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-5
- exclude test_http_cookies when running selftests, due to hang seen on
http://koji.fedoraproject.org/koji/taskinfo?taskID=2088463 (cancelled after
11 hours)
- update python-gdb.py from v5 to py3k version submitted upstream

* Wed Mar 31 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-4
- update python-gdb.py from v4 to v5 (improving performance and stability,
adding commands)

* Thu Mar 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-3
- update python-gdb.py from v3 to v4 (fixing infinite recursion on reference
cycles and tracebacks on bytes 0x80-0xff in strings, adding handlers for sets
and exceptions)

* Wed Mar 24 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-2
- refresh gdb hooks to v3 (reworking how they are packaged)

* Sun Mar 21 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.2-1
- update to 3.1.2: http://www.python.org/download/releases/3.1.2/
- drop upstreamed patch 2 (.pyc permissions handling)
- drop upstream patch 5 (fix for the test_tk and test_ttk_* selftests)
- drop upstreamed patch 200 (path-fixing script)

* Sat Mar 20 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-28
- fix typo in libpython.stp (rhbz:575336)

* Fri Mar 12 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-27
- add pyfuntop.stp example (source 7)
- convert usage of $$RPM_BUILD_ROOT to %%{buildroot} throughout, for
consistency with python.spec

* Mon Feb 15 2010 Thomas Spura <tomspur@fedoraproject.org> - 3.1.1-26
- rebuild for new package of redhat-rpm-config (rhbz:564527)
- use 'install -p' when running 'make install'

* Fri Feb 12 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-25
- split configure options into multiple lines for easy of editing
- add systemtap static markers (wcohen, mjw, dmalcolm; patch 8), a systemtap
tapset defining "python.function.entry" and "python.function.return" to make
the markers easy to use (dmalcolm; source 5), and an example of using the
tapset to the docs (dmalcolm; source 6) (rhbz:545179)

* Mon Feb  8 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-24
- move the -gdb.py file from %%{_libdir}/INSTSONAME-gdb.py to
%%{_prefix}/lib/debug/%%{_libdir}/INSTSONAME.debug-gdb.py to avoid noise from
ldconfig (bug 562980), and which should also ensure it becomes part of the
debuginfo subpackage, rather than the libs subpackage
- introduce %%{py_SOVERSION} and %%{py_INSTSONAME} to reflect the upstream
configure script, and to avoid fragile scripts that try to figure this out
dynamically (e.g. for the -gdb.py change)

* Mon Feb  8 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-23
- add gdb hooks for easier debugging (Source 4)

* Thu Jan 28 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-22
- update python-3.1.1-config.patch to remove downstream customization of build
of pyexpat and elementtree modules
- add patch adapted from upstream (patch 7) to add support for building against
system expat; add --with-system-expat to "configure" invocation
- remove embedded copies of expat and zlib from source tree during "prep"

* Mon Jan 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-21
- introduce %%{dynload_dir} macro
- explicitly list all lib-dynload files, rather than dynamically gathering the
payload into a temporary text file, so that we can be sure what we are
shipping
- introduce a macros.pybytecompile source file, to help with packaging python3
modules (Source3; written by Toshio)
- rename "2to3-3" to "python3-2to3" to better reflect python 3 module packaging
plans

* Mon Jan 25 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-20
- change python-3.1.1-config.patch to remove our downstream change to curses
configuration in Modules/Setup.dist, so that the curses modules are built using
setup.py with the downstream default (linking against libncursesw.so, rather
than libncurses.so), rather than within the Makefile; add a test to %%install
to verify the dso files that the curses module is linked against the correct
DSO (bug 539917; changes _cursesmodule.so -> _curses.so)

* Fri Jan 22 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-19
- add %%py3dir macro to macros.python3 (to be used during unified python 2/3
builds for setting up the python3 copy of the source tree)

* Wed Jan 20 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-18
- move lib2to3 from -tools subpackage to main package (bug 556667)

* Sun Jan 17 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-17
- patch Makefile.pre.in to avoid building static library (patch 6, bug 556092)

* Fri Jan 15 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-16
- use the %%{_isa} macro to ensure that the python-devel dependency on python
is for the correct multilib arch (#555943)
- delete bundled copy of libffi to make sure we use the system one

* Fri Jan 15 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-15
- fix the URLs output by pydoc so they point at python.org's 3.1 build of the
docs, rather than the 2.6 build

* Wed Jan 13 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-14
- replace references to /usr with %%{_prefix}; replace references to
/usr/include with %%{_includedir} (Toshio)

* Mon Jan 11 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-13
- fix permission on find-provides-without-python-sonames.sh from 775 to 755

* Mon Jan 11 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-12
- remove build-time requirements on tix and tk, since we already have
build-time requirements on the -devel subpackages for each of these (Thomas
Spura)
- replace usage of %%define with %%global (Thomas Spura)
- remove forcing of CC=gcc as this old workaround for bug 109268 appears to
longer be necessary
- move various test files from the "tools"/"tkinter" subpackages to the "test"
subpackage

* Thu Jan  7 2010 David Malcolm <dmalcolm@redhat.com> - 3.1.1-11
- add %%check section (thanks to Thomas Spura)
- update patch 4 to use correct shebang line
- get rid of stray patch file from buildroot

* Tue Nov 17 2009 Andrew McNabb <amcnabb@mcnabbs.org> - 3.1.1-10
- switched a few instances of "find |xargs" to "find -exec" for consistency.
- made the description of __os_install_post more accurate.

* Wed Nov  4 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-9
- add macros.python3 to the -devel subpackage, containing common macros for use
when packaging python3 modules

* Tue Nov  3 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-8
- add a provides of "python(abi)" (see bug 532118)
- fix issues identified by a.badger in package review (bug 526126, comment 39):
  - use "3" thoughout metadata, rather than "3.*"
  - remove conditional around "pkg-config openssl"
  - use standard cleanup of RPM_BUILD_ROOT
  - replace hardcoded references to /usr with _prefix macro
  - stop removing egg-info files
  - use /usr/bin/python3.1 rather than /use/bin/env python3.1 when fixing
up shebang lines
  - stop attempting to remove no-longer-present .cvsignore files
  - move the post/postun sections above the "files" sections

* Thu Oct 29 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-7
- remove commented-away patch 51 (python-2.6-distutils_rpm.patch): the -O1
flag is used by default in the upstream code
- "Makefile" and the config-32/64.h file are needed by distutils/sysconfig.py
_init_posix(), so we include them in the core package, along with their parent
directories (bug 531901)

* Tue Oct 27 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-6
- reword description, based on suggestion by amcnabb
- fix the test_email and test_imp selftests (patch 3 and patch 4 respectively)
- fix the test_tk and test_ttk_* selftests (patch 5)
- fix up the specfile's handling of shebang/perms to avoid corrupting
test_httpservers.py (sed command suggested by amcnabb)

* Thu Oct 22 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-5
- fixup importlib/_bootstrap.py so that it correctly handles being unable to
open .pyc files for writing (patch 2, upstream issue 7187)
- actually apply the rpath patch (patch 1)

* Thu Oct 22 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-4
- update patch0's setup of the crypt module to link it against libcrypt
- update patch0 to comment "datetimemodule" back out, so that it is built
using setup.py (see Setup, option 3), thus linking it statically against
timemodule.c and thus avoiding a run-time "undefined symbol:
_PyTime_DoubleToTimet" failure on "import datetime"

* Wed Oct 21 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-3
- remove executable flag from various files that shouldn't have it
- fix end-of-line encodings
- fix a character encoding

* Tue Oct 20 2009 David Malcolm <dmalcolm@redhat.com> - 3.1.1-2
- disable invocation of brp-python-bytecompile in postprocessing, since
it would be with the wrong version of python (adapted from ivazquez'
python3000 specfile)
- use a custom implementation of __find_provides in order to filter out bogus
provides lines for the various .so modules
- fixup distutils/unixccompiler.py to remove standard library path from rpath
(patch 1, was Patch0 in ivazquez' python3000 specfile)
- split out libraries into a -libs subpackage
- update summaries and descriptions, basing content on ivazquez' specfile
- fixup executable permissions on .py, .xpm and .xbm files, based on work in
ivazquez's specfile
- get rid of DOS batch files
- fixup permissions for shared libraries from non-standard 555 to standard 755
- move /usr/bin/python*-config to the -devel subpackage
- mark various directories as being documentation

* Thu Sep 24 2009 Andrew McNabb <amcnabb@mcnabbs.org> 3.1.1-1
- Initial package for Python 3.

