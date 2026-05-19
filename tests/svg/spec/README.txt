W3C SVG Test Suite Files
========================

This directory is reserved for test files from the official W3C SVG Test Suite.

The W3C SVG Test Suite provides a comprehensive set of tests for validating
conformance to the SVG specification. These tests cover a wide range of SVG
features including rendering, DOM interaction, animation, and more.

Source:
  https://www.w3.org/Graphics/SVG/Test/

To populate this directory, download the desired test suite files from the W3C
SVG test repository. The SVG 1.1 Second Edition test suite and the SVG 2 test
suite are both applicable depending on the level of specification conformance
being targeted.

SVG 1.1 Test Suite:
  https://www.w3.org/Graphics/SVG/Test/20110816/

SVG 2 Test Suite (in development):
  https://github.com/nicolo-ribaudo/svg2-tests (community mirror)
  https://test.csswg.org/harness/suite/svg2/

Notes:
- Test files in this directory are subject to the W3C Software License.
- Do not modify the original test files; place any custom tests in the
  ../basic/ directory instead.
- Reference images (expected rendering output) should be stored alongside
  the test SVG files when available.
