# Regression watch — M128e7bh_vs_e7bb vs prior

**New:** `test262_full_m128e7bh.json` tip `70ad3b2b` · **Prior:** `test262_full_m128e7bb.json`

## Headline delta

| Metric | Prior | New | Δ |
|--------|------:|----:|--:|
| Total | 49,723 | 49,723 | +0 |
| Pass | 29,162 | 30,123 | +961 |
| Overall % | 58.65% | 60.58% | +1.93 pp |
| Language pass | 20,679 | 20,964 | +285 |
| Language % | 87.49% | 88.7% | +1.21 pp |
| G2 gap | 1,775 | 1,490 | -285 |

## Pass/fail transitions

| Transition | Count |
|------------|------:|
| **Fixed** (bad→pass) | **1,219** |
| Fixed (language only) | 314 |
| **Regressed** (pass→bad) | **258** |
| Regressed (language only) | 29 |
| Still bad (both) | 19,342 |
| New paths bad | 0 |

## Regressions (pass → fail/error/timeout)

**258 regressions** (language: 29):

### `other` (228)
- **fail** `annexB/built-ins/String/prototype/substr/not-a-constructor.js`
- **fail** `built-ins/Array/from/not-a-constructor.js`
- **fail** `built-ins/Array/isArray/not-a-constructor.js`
- **fail** `built-ins/Array/of/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/Symbol.iterator/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/concat/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/copyWithin/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/entries/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/every/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/fill/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/filter/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/find/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/findIndex/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/findLast/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/findLastIndex/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/flat/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/flatMap/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/forEach/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/includes/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/indexOf/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/join/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/keys/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/lastIndexOf/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/map/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/pop/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/push/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/reduce/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/reduceRight/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/reverse/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/shift/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/slice/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/some/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/sort/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/splice/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/toString/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/unshift/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/values/not-a-constructor.js`
- **fail** `built-ins/AsyncGeneratorPrototype/return/return-suspendedStart-promise.js`
- **fail** `built-ins/BigInt/asIntN/not-a-constructor.js`
- **fail** `built-ins/BigInt/prototype/toString/not-a-constructor.js`
- … +188 more

### `expressions/async-function` (3)
- **fail** `language/expressions/async-function/await-as-identifier-reference-escaped.js`
- **fail** `language/expressions/async-function/early-errors-expression-body-contains-super-property.js`
- **fail** `language/expressions/async-function/named-await-as-label-identifier-escaped.js`

### `expressions/class` (3)
- **fail** `language/expressions/class/static-gen-method-param-dflt-yield.js`
- **fail** `language/expressions/class/static-init-await-binding.js`
- **fail** `language/expressions/class/static-method-param-dflt-yield.js`

### `expressions/dynamic-import` (3)
- **fail** `language/expressions/dynamic-import/escape-sequence-import.js`
- **fail** `language/expressions/dynamic-import/syntax/invalid/nested-async-arrow-function-return-await-import-source-assignment-expr-not-optional.js`
- **fail** `language/expressions/dynamic-import/syntax/invalid/nested-async-gen-await-import-source-assignment-expr-not-optional.js`

### `expressions/async-generator` (2)
- **fail** `language/expressions/async-generator/await-as-label-identifier-escaped.js`
- **fail** `language/expressions/async-generator/dstr/dflt-ary-init-iter-close.js`

### `expressions/compound-assignment` (2)
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-accessor-property-exp.js`
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-method-mod.js`

### `expressions/tagged-template` (2)
- **fail** `language/expressions/tagged-template/tco-call.js`
- **fail** `language/expressions/tagged-template/tco-member.js`

### `not-a-constructor.js` (1)
- **fail** `built-ins/RegExp/prototype/test/not-a-constructor.js`

### `expressions/assignment` (1)
- **fail** `language/expressions/assignment/destructuring/target-assign-throws-iterator-return-get-throws.js`

### `expressions/delete` (1)
- **fail** `language/expressions/delete/identifier-strict-recursive.js`

### `expressions/does-not-equals` (1)
- **fail** `language/expressions/does-not-equals/S11.9.2_A3.2.js`

### `expressions/exponentiation` (1)
- **fail** `language/expressions/exponentiation/exp-operator-syntax-error-logical-not-unary-expression-base.js`

### `expressions/function` (1)
- **fail** `language/expressions/function/early-body-super-prop.js`

### `expressions/generators` (1)
- **fail** `language/expressions/generators/dstr/ary-init-iter-no-close.js`

### `expressions/in` (1)
- **error** `language/expressions/in/private-field-invalid-identifier-complex.js`

### `expressions/template-literal` (1)
- **fail** `language/expressions/template-literal/invalid-unicode-escape-sequence-8.js`

### `global-code/invalid-private-names-call-expression-this.js` (1)
- **fail** `language/global-code/invalid-private-names-call-expression-this.js`

### `identifiers/part-unicode-11.0.0-class-escaped.js` (1)
- **error** `language/identifiers/part-unicode-11.0.0-class-escaped.js`

### `identifiers/part-unicode-5.2.0-escaped.js` (1)
- **error** `language/identifiers/part-unicode-5.2.0-escaped.js`

### `identifiers/vals-rus-alpha-lower-via-escape-hex.js` (1)
- **error** `language/identifiers/vals-rus-alpha-lower-via-escape-hex.js`

### `module-code/instn-star-props-nrml.js` (1)
- **error** `language/module-code/instn-star-props-nrml.js`

### `statements/class` (1)
- **error** `language/statements/class/elements/private-static-method-shadowed-by-method-on-nested-class.js`

## Fixed sample (language, first 80)

- `language/arguments-object/mapped/nonconfigurable-descriptors-define-failure.js`
- `language/directive-prologue/get-accsr-inside-func-expr-runtime.js`
- `language/directive-prologue/get-accsr-runtime.js`
- `language/expressions/array/spread-err-mult-err-itr-get-call.js`
- `language/expressions/array/spread-err-mult-err-itr-get-get.js`
- `language/expressions/array/spread-err-mult-err-itr-step.js`
- `language/expressions/array/spread-err-mult-err-itr-value.js`
- `language/expressions/array/spread-err-sngl-err-itr-get-call.js`
- `language/expressions/array/spread-err-sngl-err-itr-get-get.js`
- `language/expressions/array/spread-err-sngl-err-itr-step.js`
- `language/expressions/array/spread-err-sngl-err-itr-value.js`
- `language/expressions/arrow-function/dstr/ary-init-iter-get-err.js`
- `language/expressions/arrow-function/dstr/dflt-ary-init-iter-get-err.js`
- `language/expressions/arrow-function/dstr/dflt-obj-ptrn-id-get-value-err.js`
- `language/expressions/arrow-function/dstr/dflt-obj-ptrn-prop-id-get-value-err.js`
- `language/expressions/arrow-function/dstr/obj-ptrn-id-get-value-err.js`
- `language/expressions/arrow-function/dstr/obj-ptrn-prop-id-get-value-err.js`
- `language/expressions/assignment/dstr/array-elem-iter-get-err.js`
- `language/expressions/assignment/dstr/array-elem-trlg-iter-get-err.js`
- `language/expressions/assignment/dstr/array-elision-iter-get-err.js`
- `language/expressions/assignment/dstr/array-empty-iter-get-err.js`
- `language/expressions/assignment/dstr/array-rest-iter-get-err.js`
- `language/expressions/async-arrow-function/prototype.js`
- `language/expressions/call/spread-err-mult-err-itr-get-call.js`
- `language/expressions/call/spread-err-mult-err-itr-get-get.js`
- `language/expressions/call/spread-err-mult-err-itr-step.js`
- `language/expressions/call/spread-err-mult-err-itr-value.js`
- `language/expressions/call/spread-err-sngl-err-itr-get-call.js`
- `language/expressions/call/spread-err-sngl-err-itr-get-get.js`
- `language/expressions/call/spread-err-sngl-err-itr-step.js`
- `language/expressions/call/spread-err-sngl-err-itr-value.js`
- `language/expressions/call/with-base-obj.js`
- `language/expressions/class/dstr/meth-ary-init-iter-get-err.js`
- `language/expressions/class/dstr/meth-dflt-ary-init-iter-get-err.js`
- `language/expressions/class/dstr/meth-dflt-obj-ptrn-id-get-value-err.js`
- `language/expressions/class/dstr/meth-dflt-obj-ptrn-prop-id-get-value-err.js`
- `language/expressions/class/dstr/meth-obj-ptrn-id-get-value-err.js`
- `language/expressions/class/dstr/meth-obj-ptrn-prop-id-get-value-err.js`
- `language/expressions/class/dstr/meth-static-ary-init-iter-get-err.js`
- `language/expressions/class/dstr/meth-static-dflt-ary-init-iter-get-err.js`
- `language/expressions/class/dstr/meth-static-dflt-obj-ptrn-id-get-value-err.js`
- `language/expressions/class/dstr/meth-static-dflt-obj-ptrn-prop-id-get-value-err.js`
- `language/expressions/class/dstr/meth-static-obj-ptrn-id-get-value-err.js`
- `language/expressions/class/dstr/meth-static-obj-ptrn-prop-id-get-value-err.js`
- `language/expressions/class/elements/arrow-body-direct-eval-err-contains-arguments.js`
- `language/expressions/class/elements/arrow-body-indirect-eval-err-contains-newtarget.js`
- `language/expressions/class/elements/arrow-body-private-direct-eval-err-contains-arguments.js`
- `language/expressions/class/elements/arrow-body-private-indirect-eval-err-contains-newtarget.js`
- `language/expressions/class/elements/direct-eval-err-contains-arguments.js`
- `language/expressions/class/elements/evaluation-error/computed-name-toprimitive-err.js`
- `language/expressions/class/elements/evaluation-error/computed-name-tostring-err.js`
- `language/expressions/class/elements/evaluation-error/computed-name-valueof-err.js`
- `language/expressions/class/elements/indirect-eval-err-contains-newtarget.js`
- `language/expressions/class/elements/init-err-evaluation.js`
- `language/expressions/class/elements/nested-indirect-eval-err-contains-newtarget.js`
- `language/expressions/class/elements/nested-private-indirect-eval-err-contains-newtarget.js`
- `language/expressions/class/elements/private-direct-eval-err-contains-arguments.js`
- `language/expressions/class/elements/private-field-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/private-field-access-on-inner-function.js`
- `language/expressions/class/elements/private-getter-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/private-getter-access-on-inner-function.js`
- `language/expressions/class/elements/private-indirect-eval-err-contains-newtarget.js`
- `language/expressions/class/elements/private-method-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/private-method-access-on-inner-function.js`
- `language/expressions/class/elements/private-method-shadowed-by-getter-on-nested-class.js`
- `language/expressions/class/elements/private-setter-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/private-setter-access-on-inner-function.js`
- `language/expressions/class/elements/static-private-getter-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/static-private-getter-access-on-inner-function.js`
- `language/expressions/class/elements/static-private-getter.js`
- `language/expressions/class/elements/static-private-method-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/static-private-method-access-on-inner-function.js`
- `language/expressions/class/elements/static-private-method-and-instance-method-brand-check.js`
- `language/expressions/class/elements/static-private-setter-access-on-inner-arrow-function.js`
- `language/expressions/class/elements/static-private-setter-access-on-inner-function.js`
- `language/expressions/class/elements/static-private-setter.js`
- `language/expressions/class/private-static-field-multiple-evaluations-of-class-direct-eval.js`
- `language/expressions/class/private-static-field-multiple-evaluations-of-class-eval-indirect.js`
- `language/expressions/class/private-static-field-multiple-evaluations-of-class-factory.js`
- `language/expressions/class/private-static-field-multiple-evaluations-of-class-function-ctor.js`
- … +234 more language fixes

