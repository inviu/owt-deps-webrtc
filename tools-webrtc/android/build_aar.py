#!/usr/bin/env python

# Copyright (c) 2017 The WebRTC project authors. All Rights Reserved.
#
# Use of this source code is governed by a BSD-style license
# that can be found in the LICENSE file in the root of the source
# tree. An additional intellectual property rights grant can be found
# in the file PATENTS.  All contributing project authors may
# be found in the AUTHORS file in the root of the source tree.

"""Script to generate libwebrtc.aar for distribution.

The script has to be run from the root src folder.
./tools-webrtc/android/build_aar.py

.aar-file is just a zip-archive containing the files of the library. The file
structure generated by this script looks like this:
 - AndroidManifest.xml
 - classes.jar
 - libs/
   - armeabi-v7a/
     - libjingle_peerconnection_so.so
   - x86/
     - libjingle_peerconnection_so.so
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile


DEFAULT_ARCHS = ['armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64']
NEEDED_SO_FILES = ['libjingle_peerconnection_so.so']
JAR_FILE = 'lib.java/webrtc/sdk/android/libwebrtc.jar'
MANIFEST_FILE = 'webrtc/sdk/android/AndroidManifest.xml'
TARGETS = [
  'webrtc/sdk/android:libwebrtc',
  'webrtc/sdk/android:libjingle_peerconnection_so',
]


def _ParseArgs():
  parser = argparse.ArgumentParser(description='libwebrtc.aar generator.')
  parser.add_argument('--output', default='libwebrtc.aar',
      help='Output file of the script.')
  parser.add_argument('--arch', default=DEFAULT_ARCHS, nargs='*',
      help='Architectures to build. Defaults to %(default)s.')
  parser.add_argument('--use-goma', action='store_true', default=False,
      help='Use goma.')
  parser.add_argument('--verbose', action='store_true', default=False,
      help='Debug logging.')
  parser.add_argument('--extra-gn-args', default=[], nargs='*',
      help='Additional GN args to be used during Ninja generation.')
  return parser.parse_args()


def _RunGN(args):
  cmd = ['gn']
  cmd.extend(args)
  logging.debug('Running: %r', cmd)
  subprocess.check_call(cmd)


def _RunNinja(output_directory, args):
  cmd = ['ninja', '-C', output_directory]
  cmd.extend(args)
  logging.debug('Running: %r', cmd)
  subprocess.check_call(cmd)


def _EncodeForGN(value):
  """Encodes value as a GN literal."""
  if type(value) is str:
    return '"' + value + '"'
  elif type(value) is bool:
    return repr(value).lower()
  else:
    return repr(value)


def _GetOutputDirectory(tmp_dir, arch):
  """Returns the GN output directory for the target architecture."""
  return os.path.join(tmp_dir, arch)


def _GetTargetCpu(arch):
  """Returns target_cpu for the GN build with the given architecture."""
  if arch in ['armeabi', 'armeabi-v7a']:
    return 'arm'
  elif arch == 'arm64-v8a':
    return 'arm64'
  elif arch == 'x86':
    return 'x86'
  elif arch == 'x86_64':
    return 'x64'
  else:
    raise Exception('Unknown arch: ' + arch)


def _GetArmVersion(arch):
  """Returns arm_version for the GN build with the given architecture."""
  if arch == 'armeabi':
    return 6
  elif arch == 'armeabi-v7a':
    return 7
  elif arch in ['arm64-v8a', 'x86', 'x86_64']:
    return None
  else:
    raise Exception('Unknown arch: ' + arch)


def Build(tmp_dir, arch, use_goma, extra_gn_args):
  """Generates target architecture using GN and builds it using ninja."""
  logging.info('Building: %s', arch)
  output_directory = _GetOutputDirectory(tmp_dir, arch)
  gn_args = {
    'target_os': 'android',
    'is_debug': False,
    'is_component_build': False,
    'target_cpu': _GetTargetCpu(arch),
    'use_goma': use_goma
  }
  arm_version = _GetArmVersion(arch)
  if arm_version:
    gn_args['arm_version'] = arm_version
  gn_args_str = '--args=' + ' '.join([
      k + '=' + _EncodeForGN(v) for k, v in gn_args.items()] + extra_gn_args)

  _RunGN(['gen', output_directory, gn_args_str])

  ninja_args = TARGETS
  if use_goma:
    ninja_args.extend(['-j', '200'])
  _RunNinja(output_directory, ninja_args)


def CollectCommon(aar_file, tmp_dir, arch):
  """Collects architecture independent files into the .aar-archive."""
  logging.info('Collecting common files.')
  output_directory = _GetOutputDirectory(tmp_dir, arch)
  aar_file.write(MANIFEST_FILE, 'AndroidManifest.xml')
  aar_file.write(os.path.join(output_directory, JAR_FILE), 'classes.jar')


def Collect(aar_file, tmp_dir, arch):
  """Collects architecture specific files into the .aar-archive."""
  logging.info('Collecting: %s', arch)
  output_directory = _GetOutputDirectory(tmp_dir, arch)

  abi_dir = os.path.join('jni', arch)
  for so_file in NEEDED_SO_FILES:
    aar_file.write(os.path.join(output_directory, so_file),
                   os.path.join(abi_dir, so_file))


def main():
  args = _ParseArgs()
  logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

  tmp_dir = tempfile.mkdtemp()

  for arch in args.arch:
    Build(tmp_dir, arch, args.use_goma, args.extra_gn_args)

  with zipfile.ZipFile(args.output, 'w') as aar_file:
    # Architecture doesn't matter here, arbitrarily using the first one.
    CollectCommon(aar_file, tmp_dir, args.arch[0])
    for arch in args.arch:
      Collect(aar_file, tmp_dir, arch)

  shutil.rmtree(tmp_dir, True)


if __name__ == '__main__':
  sys.exit(main())
