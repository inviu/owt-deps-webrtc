#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for enum_preprocess.py.

This test suite containss various tests for the C++ -> Java enum generator.
"""

import collections
from datetime import date
import optparse
import os
import sys
import unittest

import java_cpp_enum
from java_cpp_enum import EnumDefinition, GenerateOutput, GetScriptName
from java_cpp_enum import HeaderParser

sys.path.append(os.path.join(os.path.dirname(__file__), "gyp"))
from util import build_utils

class TestPreprocess(unittest.TestCase):
  def testOutput(self):
    definition = EnumDefinition(original_enum_name='ClassName',
                                enum_package='some.package',
                                entries=[('E1', 1), ('E2', '2 << 2')],
                                comments=[('E2', 'This is a comment.'),
                                          ('E1', 'This is a multiple line '
                                                 'comment that is really long. '
                                                 'This is a multiple line '
                                                 'comment that is really '
                                                 'really long.')])
    output = GenerateOutput('path/to/file', definition)
    expected = """
// Copyright %d The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// This file is autogenerated by
//     %s
// From
//     path/to/file

package some.package;

import android.support.annotation.IntDef;

import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;

@IntDef({
    ClassName.E1, ClassName.E2
})
@Retention(RetentionPolicy.SOURCE)
public @interface ClassName {
  /**
   * %s
   * really really long.
   */
  int E1 = 1;
  /**
   * This is a comment.
   */
  int E2 = 2 << 2;
}
"""
    long_comment = ('This is a multiple line comment that is really long. '
                    'This is a multiple line comment that is')
    self.assertEqual(
            expected % (date.today().year, GetScriptName(), long_comment),
            output)

  def testParseSimpleEnum(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum EnumName {
        VALUE_ZERO,
        VALUE_ONE,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('EnumName', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('VALUE_ZERO', 0),
                                              ('VALUE_ONE', 1)]),
                     definition.entries)

  def testParseBitShifts(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum EnumName {
        VALUE_ZERO = 1 << 0,
        VALUE_ONE = 1 << 1,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('EnumName', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('VALUE_ZERO', '1 << 0'),
                                              ('VALUE_ONE', '1 << 1')]),
                     definition.entries)

  def testParseMultilineEnumEntry(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: bar.namespace
      enum Foo {
        VALUE_ZERO = 1 << 0,
        VALUE_ONE =
            SymbolKey | FnKey | AltGrKey | MetaKey | AltKey | ControlKey,
        VALUE_TWO = 1 << 18,
      };
    """.split('\n')
    expected_entries = collections.OrderedDict([
        ('VALUE_ZERO', '1 << 0'),
        ('VALUE_ONE', 'SymbolKey | FnKey | AltGrKey | MetaKey | AltKey | '
         'ControlKey'),
        ('VALUE_TWO', '1 << 18')])
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('bar.namespace', definition.enum_package)
    self.assertEqual(expected_entries, definition.entries)

  def testParseEnumEntryWithTrailingMultilineEntry(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: bar.namespace
      enum Foo {
        VALUE_ZERO = 1,
        VALUE_ONE =
            SymbolKey | FnKey | AltGrKey | MetaKey |
            AltKey | ControlKey | ShiftKey,
      };
    """.split('\n')
    expected_entries = collections.OrderedDict([
        ('VALUE_ZERO', '1'),
        ('VALUE_ONE', 'SymbolKey | FnKey | AltGrKey | MetaKey | AltKey | '
         'ControlKey | ShiftKey')])
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('bar.namespace', definition.enum_package)
    self.assertEqual(expected_entries, definition.entries)

  def testParseNoCommaAfterLastEntry(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: bar.namespace
      enum Foo {
        VALUE_ZERO = 1,

        // This is a multiline
        //
        // comment with an empty line.
        VALUE_ONE = 2
      };
    """.split('\n')
    expected_entries = collections.OrderedDict([
        ('VALUE_ZERO', '1'),
        ('VALUE_ONE', '2')])
    expected_comments = collections.OrderedDict([
        ('VALUE_ONE', 'This is a multiline comment with an empty line.')])
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('bar.namespace', definition.enum_package)
    self.assertEqual(expected_entries, definition.entries)
    self.assertEqual(expected_comments, definition.comments)

  def testParseClassNameOverride(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      // GENERATED_JAVA_CLASS_NAME_OVERRIDE: OverrideName
      enum EnumName {
        FOO
      };

      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      // GENERATED_JAVA_CLASS_NAME_OVERRIDE: OtherOverride
      enum PrefixTest {
        PREFIX_TEST_A,
        PREFIX_TEST_B,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(2, len(definitions))
    definition = definitions[0]
    self.assertEqual('OverrideName', definition.class_name)

    definition = definitions[1]
    self.assertEqual('OtherOverride', definition.class_name)
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 1)]),
                     definition.entries)

  def testParsePreservesCommentsWhenPrefixStripping(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum EnumOne {
        ENUM_ONE_A = 1,
        // Comment there
        ENUM_ONE_B = A,
      };

      enum EnumIgnore {
        C, D, E
      };

      // GENERATED_JAVA_ENUM_PACKAGE: other.package
      // GENERATED_JAVA_PREFIX_TO_STRIP: P_
      enum EnumTwo {
        P_A,
        // This comment spans
        // two lines.
        P_B
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(2, len(definitions))
    definition = definitions[0]
    self.assertEqual('EnumOne', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('A', '1'),
                                              ('B', 'A')]),
                     definition.entries)
    self.assertEqual(collections.OrderedDict([('B', 'Comment there')]),
                     definition.comments)
    definition = definitions[1]
    self.assertEqual('EnumTwo', definition.class_name)
    self.assertEqual('other.package', definition.enum_package)
    self.assertEqual(collections.OrderedDict(
        [('B', 'This comment spans two lines.')]), definition.comments)
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 1)]),
                     definition.entries)

  def testParseTwoEnums(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum AnEnum {
        ENUM_ONE_A = 1,
        ENUM_ONE_B = A,
      };

      enum EnumIgnore {
        C, D, E
      };

      // GENERATED_JAVA_ENUM_PACKAGE: other.package
      enum EnumTwo {
        P_A,
        P_B
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(2, len(definitions))
    definition = definitions[0]
    self.assertEqual('AnEnum', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('ENUM_ONE_A', '1'),
                                              ('ENUM_ONE_B', 'A')]),
                     definition.entries)
    definition = definitions[1]
    self.assertEqual('EnumTwo', definition.class_name)
    self.assertEqual('other.package', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('P_A', 0),
                                              ('P_B', 1)]),
                     definition.entries)

  def testParseSingleLineEnum(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: other.package
      // GENERATED_JAVA_PREFIX_TO_STRIP: P_
      enum EnumTwo { P_A, P_B };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    definition = definitions[0]
    self.assertEqual('EnumTwo', definition.class_name)
    self.assertEqual('other.package', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 1)]),
                     definition.entries)

  def testParseSingleLineAndRegularEnum(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum EnumOne {
        ENUM_ONE_A = 1,
        // Comment there
        ENUM_ONE_B = A,
      };

      // GENERATED_JAVA_ENUM_PACKAGE: other.package
      enum EnumTwo { P_A, P_B };

      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      // GENERATED_JAVA_CLASS_NAME_OVERRIDE: OverrideName
      enum EnumName {
        ENUM_NAME_FOO
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    definition = definitions[0]
    self.assertEqual(
        collections.OrderedDict([('A', '1'), ('B', 'A')]), definition.entries)
    self.assertEqual(collections.OrderedDict([('ENUM_ONE_B', 'Comment there')]),
                     definition.comments)

    self.assertEqual(3, len(definitions))
    definition = definitions[1]
    self.assertEqual(
        collections.OrderedDict([('P_A', 0), ('P_B', 1)]), definition.entries)

    definition = definitions[2]
    self.assertEqual(collections.OrderedDict([('FOO', 0)]), definition.entries)

  def testParseThrowsOnUnknownDirective(self):
    test_data = """
      // GENERATED_JAVA_UNKNOWN: Value
      enum EnumName {
        VALUE_ONE,
      };
    """.split('\n')
    with self.assertRaises(Exception):
      HeaderParser(test_data).ParseDefinitions()

  def testParseReturnsEmptyListWithoutDirectives(self):
    test_data = """
      enum EnumName {
        VALUE_ONE,
      };
    """.split('\n')
    self.assertEqual([], HeaderParser(test_data).ParseDefinitions())

  def testParseEnumClass(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum class Foo {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('A', 0)]),
                     definition.entries)

  def testParseEnumStruct(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum struct Foo {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual(collections.OrderedDict([('A', 0)]),
                     definition.entries)

  def testParseFixedTypeEnum(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum Foo : int {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual('int', definition.fixed_type)
    self.assertEqual(collections.OrderedDict([('A', 0)]),
                     definition.entries)

  def testParseFixedTypeEnumClass(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum class Foo: unsigned short {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual(1, len(definitions))
    definition = definitions[0]
    self.assertEqual('Foo', definition.class_name)
    self.assertEqual('test.namespace', definition.enum_package)
    self.assertEqual('unsigned short', definition.fixed_type)
    self.assertEqual(collections.OrderedDict([('A', 0)]),
                     definition.entries)

  def testParseUnknownFixedTypeRaises(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: test.namespace
      enum class Foo: foo_type {
        FOO_A,
      };
    """.split('\n')
    with self.assertRaises(Exception):
      HeaderParser(test_data).ParseDefinitions()

  def testParseSimpleMultiLineDirective(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: (
      //   test.namespace)
      // GENERATED_JAVA_CLASS_NAME_OVERRIDE: Bar
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual('test.namespace', definitions[0].enum_package)
    self.assertEqual('Bar', definitions[0].class_name)

  def testParseMultiLineDirective(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: (te
      //   st.name
      //   space)
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual('test.namespace', definitions[0].enum_package)

  def testParseMultiLineDirectiveWithOtherDirective(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: (
      //   test.namespace)
      // GENERATED_JAVA_CLASS_NAME_OVERRIDE: (
      //   Ba
      //   r
      //   )
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    definitions = HeaderParser(test_data).ParseDefinitions()
    self.assertEqual('test.namespace', definitions[0].enum_package)
    self.assertEqual('Bar', definitions[0].class_name)

  def testParseMalformedMultiLineDirectiveWithOtherDirective(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: (
      //   test.name
      //   space
      // GENERATED_JAVA_CLASS_NAME_OVERRIDE: Bar
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    with self.assertRaises(Exception):
      HeaderParser(test_data).ParseDefinitions()

  def testParseMalformedMultiLineDirective(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: (
      //   test.name
      //   space
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    with self.assertRaises(Exception):
      HeaderParser(test_data).ParseDefinitions()

  def testParseMalformedMultiLineDirectiveShort(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE: (
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    with self.assertRaises(Exception):
      HeaderParser(test_data).ParseDefinitions()

  def testParseMalformedMultiLineDirectiveMissingBrackets(self):
    test_data = """
      // GENERATED_JAVA_ENUM_PACKAGE:
      // test.namespace
      enum Foo {
        FOO_A,
      };
    """.split('\n')
    with self.assertRaises(Exception):
      HeaderParser(test_data).ParseDefinitions()

  def testEnumValueAssignmentNoneDefined(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('A', None)
    definition.AppendEntry('B', None)
    definition.AppendEntry('C', None)
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 1),
                                              ('C', 2)]),
                     definition.entries)

  def testEnumValueAssignmentAllDefined(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('A', '1')
    definition.AppendEntry('B', '2')
    definition.AppendEntry('C', '3')
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', '1'),
                                              ('B', '2'),
                                              ('C', '3')]),
                     definition.entries)

  def testEnumValueAssignmentReferences(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('A', None)
    definition.AppendEntry('B', 'A')
    definition.AppendEntry('C', None)
    definition.AppendEntry('D', 'C')
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 0),
                                              ('C', 1),
                                              ('D', 1)]),
                     definition.entries)

  def testEnumValueAssignmentSet(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('A', None)
    definition.AppendEntry('B', '2')
    definition.AppendEntry('C', None)
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 2),
                                              ('C', 3)]),
                     definition.entries)

  def testEnumValueAssignmentSetReferences(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('A', None)
    definition.AppendEntry('B', 'A')
    definition.AppendEntry('C', 'B')
    definition.AppendEntry('D', None)
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 0),
                                              ('C', 0),
                                              ('D', 1)]),
                     definition.entries)

  def testEnumValueAssignmentRaises(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('A', None)
    definition.AppendEntry('B', 'foo')
    definition.AppendEntry('C', None)
    with self.assertRaises(Exception):
      definition.Finalize()

  def testExplicitPrefixStripping(self):
    definition = EnumDefinition(original_enum_name='c', enum_package='p')
    definition.AppendEntry('P_A', None)
    definition.AppendEntry('B', None)
    definition.AppendEntry('P_C', None)
    definition.AppendEntry('P_LAST', 'P_C')
    definition.prefix_to_strip = 'P_'
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 1),
                                              ('C', 2),
                                              ('LAST', 2)]),
                     definition.entries)

  def testImplicitPrefixStripping(self):
    definition = EnumDefinition(original_enum_name='ClassName',
                                enum_package='p')
    definition.AppendEntry('CLASS_NAME_A', None)
    definition.AppendEntry('CLASS_NAME_B', None)
    definition.AppendEntry('CLASS_NAME_C', None)
    definition.AppendEntry('CLASS_NAME_LAST', 'CLASS_NAME_C')
    definition.Finalize()
    self.assertEqual(collections.OrderedDict([('A', 0),
                                              ('B', 1),
                                              ('C', 2),
                                              ('LAST', 2)]),
                     definition.entries)

  def testImplicitPrefixStrippingRequiresAllConstantsToBePrefixed(self):
    definition = EnumDefinition(original_enum_name='Name',
                                enum_package='p')
    definition.AppendEntry('A', None)
    definition.AppendEntry('B', None)
    definition.AppendEntry('NAME_LAST', None)
    definition.Finalize()
    self.assertEqual(['A', 'B', 'NAME_LAST'], definition.entries.keys())

  def testGenerateThrowsOnEmptyInput(self):
    with self.assertRaises(Exception):
      original_do_parse = java_cpp_enum.DoParseHeaderFile
      try:
        java_cpp_enum.DoParseHeaderFile = lambda _: []
        for _ in java_cpp_enum.DoGenerate(['file']):
          pass
      finally:
        java_cpp_enum.DoParseHeaderFile = original_do_parse

def main(argv):
  parser = optparse.OptionParser()
  parser.add_option("--stamp", help="File to touch on success.")
  options, _ = parser.parse_args(argv)

  suite = unittest.TestLoader().loadTestsFromTestCase(TestPreprocess)
  unittest.TextTestRunner(verbosity=0).run(suite)

  if options.stamp:
    build_utils.Touch(options.stamp)

if __name__ == '__main__':
  main(sys.argv[1:])
