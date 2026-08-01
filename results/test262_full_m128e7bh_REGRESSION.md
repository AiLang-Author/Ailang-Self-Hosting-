# Regression watch — M128e7bh vs prior

**New:** `test262_full_m128e7bh.json` tip `70ad3b2b` · **Prior:** `test262_full_m128e7x.json`

## Headline delta

| Metric | Prior | New | Δ |
|--------|------:|----:|--:|
| Total | 49,723 | 49,723 | +0 |
| Pass | 30,505 | 30,123 | -382 |
| Overall % | 61.35% | 60.58% | -0.77 pp |
| Language pass | 21,607 | 20,964 | -643 |
| Language % | 91.42% | 88.7% | -2.72 pp |
| G2 gap | 847 | 1,490 | +643 |

## Pass/fail transitions

| Transition | Count |
|------------|------:|
| **Fixed** (bad→pass) | **1,631** |
| Fixed (language only) | 890 |
| **Regressed** (pass→bad) | **2,013** |
| Regressed (language only) | 1,589 |
| Still bad (both) | 17,587 |
| New paths bad | 0 |

## Regressions (pass → fail/error/timeout)

**2013 regressions** (language: 1589):

### `statements/class` (861)
- **error** `language/statements/class/accessor-name-inst/literal-string-default-escaped.js`
- **error** `language/statements/class/accessor-name-static/literal-string-default-escaped.js`
- **error** `language/statements/class/async-gen-method-static/dflt-params-ref-prior.js`
- **fail** `language/statements/class/async-gen-method-static/forbidden-ext/b2/cls-decl-async-gen-meth-static-forbidden-ext-indirect-access-own-prop-caller-value.js`
- **error** `language/statements/class/async-gen-method-static/yield-as-label-identifier-escaped.js`
- **fail** `language/statements/class/async-gen-method-static/yield-promise-reject-next-for-await-of-async-iterator.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-async-next.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-getiter-async-not-callable-string-throw.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-getiter-async-returns-symbol-throw.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-getiter-sync-not-callable-symbol-throw.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-next-call-done-get-abrupt.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-next-not-callable-object-throw.js`
- **fail** `language/statements/class/async-gen-method-static/yield-star-next-then-non-callable-object-fulfillpromise.js`
- **fail** `language/statements/class/async-gen-method/params-trailing-comma-multiple.js`
- **fail** `language/statements/class/async-gen-method/yield-promise-reject-next-yield-star-sync-iterator.js`
- **fail** `language/statements/class/async-gen-method/yield-star-expr-abrupt.js`
- **fail** `language/statements/class/async-gen-method/yield-star-getiter-async-returns-abrupt.js`
- **fail** `language/statements/class/async-gen-method/yield-star-getiter-sync-get-abrupt.js`
- **fail** `language/statements/class/async-gen-method/yield-star-getiter-sync-returns-null-throw.js`
- **error** `language/statements/class/async-gen-method/yield-star-next-call-done-get-abrupt.js`
- **fail** `language/statements/class/async-gen-method/yield-star-next-get-abrupt.js`
- **fail** `language/statements/class/async-gen-method/yield-star-next-not-callable-undefined-throw.js`
- **fail** `language/statements/class/async-gen-method/yield-star-next-then-non-callable-undefined-fulfillpromise.js`
- **fail** `language/statements/class/async-method-static/dflt-params-abrupt.js`
- **fail** `language/statements/class/async-method-static/dflt-params-trailing-comma.js`
- **fail** `language/statements/class/async-method-static/params-trailing-comma-single.js`
- **fail** `language/statements/class/async-method-static/returns-async-function.js`
- **fail** `language/statements/class/async-method/dflt-params-abrupt.js`
- **fail** `language/statements/class/async-method/dflt-params-trailing-comma.js`
- **fail** `language/statements/class/async-method/params-trailing-comma-single.js`
- **fail** `language/statements/class/async-method/returns-async-function.js`
- **fail** `language/statements/class/cpn-class-decl-accessors-computed-property-name-from-assignment-expression-bitwise-or.js`
- **error** `language/statements/class/cpn-class-decl-accessors-computed-property-name-from-assignment-expression-logical-and.js`
- **error** `language/statements/class/cpn-class-decl-accessors-computed-property-name-from-condition-expression-true.js`
- **fail** `language/statements/class/cpn-class-decl-accessors-computed-property-name-from-decimal-e-notational-literal.js`
- **fail** `language/statements/class/cpn-class-decl-accessors-computed-property-name-from-generator-function-declaration.js`
- **fail** `language/statements/class/cpn-class-decl-accessors-computed-property-name-from-numeric-literal.js`
- **error** `language/statements/class/cpn-class-decl-computed-property-name-from-assignment-expression-bitwise-or.js`
- **fail** `language/statements/class/cpn-class-decl-computed-property-name-from-decimal-literal.js`
- **error** `language/statements/class/cpn-class-decl-computed-property-name-from-exponetiation-expression.js`
- … +821 more

### `expressions/class` (504)
- **fail** `language/expressions/class/decorator/syntax/valid/decorator-call-expr-identifier-reference-yield.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-init-iter-close.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-init-iter-no-close.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-name-iter-val.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-elem-init.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-elem-iter.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-elision-init.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-elision-iter.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-empty-init.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-empty-iter.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-rest-init.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-ary-rest-iter.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-exhausted.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-fn-name-arrow.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-fn-name-class.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-fn-name-cover.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-fn-name-fn.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-fn-name-gen.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-hole.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-skipped.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-init-undef.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-iter-complete.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-iter-done.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-iter-val-array-prototype.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-id-iter-val.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-obj-id-init.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-obj-id.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-obj-prop-id-init.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elem-obj-prop-id.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elision-exhausted.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-elision.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-empty.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-ary-elem.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-ary-elision.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-ary-empty.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-ary-rest.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-id-direct.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-id-elision.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-id-exhausted.js`
- **fail** `language/expressions/class/dstr/async-private-gen-meth-ary-ptrn-rest-id.js`
- … +464 more

### `other` (423)
- **fail** `annexB/built-ins/String/prototype/substr/not-a-constructor.js`
- **fail** `built-ins/Array/from/not-a-constructor.js`
- **fail** `built-ins/Array/isArray/not-a-constructor.js`
- **fail** `built-ins/Array/of/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/Symbol.iterator/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/concat/create-species-abrupt.js`
- **fail** `built-ins/Array/prototype/concat/create-species-non-ctor.js`
- **fail** `built-ins/Array/prototype/concat/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/copyWithin/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/copyWithin/return-abrupt-from-end.js`
- **fail** `built-ins/Array/prototype/copyWithin/return-abrupt-from-start.js`
- **fail** `built-ins/Array/prototype/copyWithin/return-abrupt-from-target.js`
- **fail** `built-ins/Array/prototype/entries/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/every/15.4.4.16-4-1.js`
- **fail** `built-ins/Array/prototype/every/15.4.4.16-4-3.js`
- **fail** `built-ins/Array/prototype/every/15.4.4.16-4-4.js`
- **fail** `built-ins/Array/prototype/every/15.4.4.16-4-5.js`
- **fail** `built-ins/Array/prototype/every/15.4.4.16-4-6.js`
- **fail** `built-ins/Array/prototype/every/15.4.4.16-4-7.js`
- **fail** `built-ins/Array/prototype/every/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/fill/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/fill/return-abrupt-from-end.js`
- **fail** `built-ins/Array/prototype/fill/return-abrupt-from-start.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-2-10.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-4-1.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-4-3.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-4-4.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-4-5.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-4-6.js`
- **fail** `built-ins/Array/prototype/filter/15.4.4.20-4-7.js`
- **fail** `built-ins/Array/prototype/filter/create-species-abrupt.js`
- **fail** `built-ins/Array/prototype/filter/create-species-non-ctor.js`
- **fail** `built-ins/Array/prototype/filter/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/find/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/find/return-abrupt-from-predicate-call.js`
- **fail** `built-ins/Array/prototype/findIndex/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/findIndex/return-abrupt-from-predicate-call.js`
- **fail** `built-ins/Array/prototype/findLast/not-a-constructor.js`
- **fail** `built-ins/Array/prototype/findLast/return-abrupt-from-predicate-call.js`
- **fail** `built-ins/Array/prototype/findLastIndex/not-a-constructor.js`
- … +383 more

### `eval-code/direct` (52)
- **fail** `annexB/language/eval-code/direct/func-block-decl-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-block-decl-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-block-decl-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-block-decl-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-block-decl-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-a-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-a-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-a-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-a-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-a-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-b-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-b-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-b-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-b-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-decl-b-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-stmt-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-stmt-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-stmt-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-stmt-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-else-stmt-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-no-else-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-no-else-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-no-else-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-no-else-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-decl-no-else-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-stmt-else-decl-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-if-stmt-else-decl-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-stmt-else-decl-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-if-stmt-else-decl-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-if-stmt-else-decl-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-switch-case-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-switch-case-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-switch-case-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-switch-case-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-switch-case-eval-func-update.js`
- **fail** `annexB/language/eval-code/direct/func-switch-dflt-eval-func-block-scoping.js`
- **fail** `annexB/language/eval-code/direct/func-switch-dflt-eval-func-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/direct/func-switch-dflt-eval-func-existing-fn-no-init.js`
- **fail** `annexB/language/eval-code/direct/func-switch-dflt-eval-func-existing-var-update.js`
- **fail** `annexB/language/eval-code/direct/func-switch-dflt-eval-func-update.js`
- … +12 more

### `statements/for-of` (25)
- **error** `language/statements/for-of/dstr/const-ary-ptrn-elem-id-init-undef.js`
- **error** `language/statements/for-of/dstr/const-ary-ptrn-elem-id-iter-val-array-prototype.js`
- **fail** `language/statements/for-of/dstr/const-ary-ptrn-elem-id-iter-val-err.js`
- **error** `language/statements/for-of/dstr/const-ary-ptrn-elem-id-iter-val.js`
- **error** `language/statements/for-of/dstr/const-ary-ptrn-elem-obj-id.js`
- **fail** `language/statements/for-of/dstr/const-ary-ptrn-rest-id-iter-val-err.js`
- **error** `language/statements/for-of/dstr/const-obj-ptrn-id-init-fn-name-arrow.js`
- **error** `language/statements/for-of/dstr/const-obj-ptrn-id-init-fn-name-class.js`
- **error** `language/statements/for-of/dstr/const-obj-ptrn-id-init-fn-name-cover.js`
- **error** `language/statements/for-of/dstr/const-obj-ptrn-prop-ary-init.js`
- **error** `language/statements/for-of/dstr/const-obj-ptrn-prop-ary-trailing-comma.js`
- **error** `language/statements/for-of/dstr/let-ary-ptrn-elem-id-init-undef.js`
- **error** `language/statements/for-of/dstr/let-ary-ptrn-elem-id-iter-val-array-prototype.js`
- **fail** `language/statements/for-of/dstr/let-ary-ptrn-elem-id-iter-val-err.js`
- **error** `language/statements/for-of/dstr/let-ary-ptrn-elem-id-iter-val.js`
- **error** `language/statements/for-of/dstr/let-ary-ptrn-elem-obj-id.js`
- **fail** `language/statements/for-of/dstr/let-ary-ptrn-rest-id-iter-val-err.js`
- **error** `language/statements/for-of/dstr/let-obj-ptrn-id-init-fn-name-class.js`
- **error** `language/statements/for-of/dstr/let-obj-ptrn-id-init-fn-name-cover.js`
- **error** `language/statements/for-of/dstr/let-obj-ptrn-prop-ary-init.js`
- **error** `language/statements/for-of/dstr/let-obj-ptrn-prop-ary-trailing-comma.js`
- **error** `language/statements/for-of/dstr/let-obj-ptrn-prop-ary.js`
- **fail** `language/statements/for-of/dstr/var-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/for-of/dstr/var-ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/statements/for-of/iterator-next-result-value-attr-error.js`

### `eval-code/indirect` (11)
- **fail** `annexB/language/eval-code/indirect/global-block-decl-eval-global-existing-global-update.js`
- **fail** `annexB/language/eval-code/indirect/global-if-decl-else-decl-a-eval-global-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/indirect/global-if-decl-else-decl-b-eval-global-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/indirect/global-if-decl-else-stmt-eval-global-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/indirect/global-if-decl-no-else-eval-global-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/indirect/global-if-stmt-else-decl-eval-global-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/indirect/global-switch-case-eval-global-existing-block-fn-update.js`
- **fail** `annexB/language/eval-code/indirect/global-switch-dflt-eval-global-existing-block-fn-update.js`
- **fail** `language/eval-code/indirect/var-env-func-init-global-new.js`
- **fail** `language/eval-code/indirect/var-env-var-init-global-new.js`
- **fail** `language/eval-code/indirect/var-env-var-strict.js`

### `expressions/assignment` (6)
- **fail** `language/expressions/assignment/destructuring/target-assign-throws-iterator-return-get-throws.js`
- **fail** `language/expressions/assignment/dstr/array-elem-put-prop-ref-user-err.js`
- **fail** `language/expressions/assignment/dstr/array-rest-put-prop-ref-user-err-iter-close-skip.js`
- **fail** `language/expressions/assignment/dstr/array-rest-put-prop-ref-user-err.js`
- **fail** `language/expressions/assignment/dstr/obj-prop-put-prop-ref-user-err.js`
- **fail** `language/expressions/assignment/dstr/obj-rest-getter-abrupt-get-error.js`

### `expressions/object` (6)
- **fail** `language/expressions/object/dstr/meth-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/expressions/object/dstr/meth-ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/expressions/object/dstr/meth-dflt-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/expressions/object/dstr/meth-dflt-ary-ptrn-rest-id-iter-val-err.js`
- **error** `language/expressions/object/identifier-shorthand-static-init-await-valid.js`
- **fail** `language/expressions/object/scope-setter-body-lex-distinc.js`

### `statements/function` (6)
- **fail** `language/statements/function/dflt-params-duplicates.js`
- **fail** `language/statements/function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/statements/function/early-body-super-call.js`
- **fail** `language/statements/function/early-params-super-prop.js`
- **fail** `language/statements/function/param-dflt-yield-strict.js`
- **error** `language/statements/function/static-init-await-binding-invalid.js`

### `expressions/function` (5)
- **fail** `language/expressions/function/dstr/ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/expressions/function/dstr/ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/expressions/function/dstr/dflt-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/expressions/function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/expressions/function/early-body-super-prop.js`

### `computed-property-names/class` (4)
- **fail** `language/computed-property-names/class/accessor/getter-duplicates.js`
- **error** `language/computed-property-names/class/method/constructor-can-be-generator.js`
- **error** `language/computed-property-names/class/method/constructor-duplicate-1.js`
- **error** `language/computed-property-names/class/static/setter-constructor.js`

### `expressions/arrow-function` (4)
- **fail** `language/expressions/arrow-function/dstr/ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/expressions/arrow-function/dstr/ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js`

### `statements/for` (4)
- **fail** `language/statements/for/dstr/const-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/for/dstr/const-ary-ptrn-rest-id-iter-val-err.js`
- **fail** `language/statements/for/dstr/let-ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/for/dstr/let-ary-ptrn-rest-id-iter-val-err.js`

### `statements/with` (4)
- **fail** `language/statements/with/get-binding-value-call-with-proxy-env.js`
- **fail** `language/statements/with/get-binding-value-idref-with-proxy-env.js`
- **fail** `language/statements/with/set-mutable-binding-idref-compound-assign-with-proxy-env.js`
- **fail** `language/statements/with/set-mutable-binding-idref-with-proxy-env.js`

### `expressions/async-function` (3)
- **fail** `language/expressions/async-function/await-as-identifier-reference-escaped.js`
- **fail** `language/expressions/async-function/early-errors-expression-body-contains-super-property.js`
- **fail** `language/expressions/async-function/named-await-as-label-identifier-escaped.js`

### `expressions/dynamic-import` (3)
- **fail** `language/expressions/dynamic-import/escape-sequence-import.js`
- **fail** `language/expressions/dynamic-import/syntax/invalid/nested-async-arrow-function-return-await-import-source-assignment-expr-not-optional.js`
- **fail** `language/expressions/dynamic-import/syntax/invalid/nested-async-gen-await-import-source-assignment-expr-not-optional.js`

### `statements/variable` (3)
- **fail** `language/statements/variable/S12.2_A11.js`
- **fail** `language/statements/variable/dstr/ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/variable/dstr/ary-ptrn-rest-id-iter-val-err.js`

### `expressions/async-generator` (2)
- **fail** `language/expressions/async-generator/await-as-label-identifier-escaped.js`
- **fail** `language/expressions/async-generator/dstr/dflt-ary-init-iter-close.js`

### `expressions/compound-assignment` (2)
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-accessor-property-exp.js`
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-method-mod.js`

### `expressions/new.target` (2)
- **error** `language/expressions/new.target/value-via-super-call.js`
- **error** `language/expressions/new.target/value-via-super-property.js`

### `expressions/super` (2)
- **error** `language/expressions/super/call-spread-mult-obj-undefined.js`
- **error** `language/expressions/super/prop-expr-cls-null-proto.js`

### `expressions/tagged-template` (2)
- **fail** `language/expressions/tagged-template/tco-call.js`
- **fail** `language/expressions/tagged-template/tco-member.js`

### `expressions/this` (2)
- **fail** `language/expressions/this/S11.1.1_A4.1.js`
- **fail** `language/expressions/this/S11.1.1_A4.2.js`

### `statements/const` (2)
- **fail** `language/statements/const/dstr/ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/const/dstr/ary-ptrn-rest-id-iter-val-err.js`

### `statements/generators` (2)
- **fail** `language/statements/generators/dflt-params-duplicates.js`
- **fail** `language/statements/generators/yield-as-binding-identifier-escaped.js`

### `statements/if` (2)
- **fail** `language/statements/if/if-fun-no-else-strict.js`
- **fail** `language/statements/if/labelled-fn-stmt-lone.js`

### `statements/labeled` (2)
- **fail** `language/statements/labeled/continue.js`
- **fail** `language/statements/labeled/decl-gen.js`

### `statements/let` (2)
- **fail** `language/statements/let/dstr/ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/let/dstr/ary-ptrn-rest-id-iter-val-err.js`

### `statements/try` (2)
- **fail** `language/statements/try/dstr/ary-ptrn-elem-id-iter-val-err.js`
- **fail** `language/statements/try/dstr/obj-ptrn-rest-getter.js`

### `not-a-constructor.js` (1)
- **fail** `built-ins/RegExp/prototype/test/not-a-constructor.js`

### `arguments-object/cls-decl-async-gen-meth-args-trailing-comma-spread-operator.js` (1)
- **error** `language/arguments-object/cls-decl-async-gen-meth-args-trailing-comma-spread-operator.js`

### `arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-multiple.js` (1)
- **error** `language/arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-multiple.js`

### `arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-null.js` (1)
- **fail** `language/arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-null.js`

### `arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-single-args.js` (1)
- **error** `language/arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-single-args.js`

### `arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-undefined.js` (1)
- **fail** `language/arguments-object/cls-decl-async-private-gen-meth-args-trailing-comma-undefined.js`

### `arguments-object/cls-decl-async-private-gen-meth-static-args-trailing-comma-multiple.js` (1)
- **error** `language/arguments-object/cls-decl-async-private-gen-meth-static-args-trailing-comma-multiple.js`

### `arguments-object/cls-decl-async-private-gen-meth-static-args-trailing-comma-single-args.js` (1)
- **error** `language/arguments-object/cls-decl-async-private-gen-meth-static-args-trailing-comma-single-args.js`

### `arguments-object/cls-decl-gen-meth-static-args-trailing-comma-null.js` (1)
- **error** `language/arguments-object/cls-decl-gen-meth-static-args-trailing-comma-null.js`

### `arguments-object/cls-decl-private-gen-meth-args-trailing-comma-null.js` (1)
- **fail** `language/arguments-object/cls-decl-private-gen-meth-args-trailing-comma-null.js`

### `arguments-object/cls-decl-private-gen-meth-args-trailing-comma-single-args.js` (1)
- **fail** `language/arguments-object/cls-decl-private-gen-meth-args-trailing-comma-single-args.js`

### `arguments-object/cls-decl-private-gen-meth-args-trailing-comma-spread-operator.js` (1)
- **error** `language/arguments-object/cls-decl-private-gen-meth-args-trailing-comma-spread-operator.js`

### `arguments-object/cls-decl-private-gen-meth-args-trailing-comma-undefined.js` (1)
- **fail** `language/arguments-object/cls-decl-private-gen-meth-args-trailing-comma-undefined.js`

### `arguments-object/cls-decl-private-meth-args-trailing-comma-multiple.js` (1)
- **fail** `language/arguments-object/cls-decl-private-meth-args-trailing-comma-multiple.js`

### `arguments-object/cls-decl-private-meth-args-trailing-comma-null.js` (1)
- **fail** `language/arguments-object/cls-decl-private-meth-args-trailing-comma-null.js`

### `arguments-object/cls-decl-private-meth-args-trailing-comma-single-args.js` (1)
- **fail** `language/arguments-object/cls-decl-private-meth-args-trailing-comma-single-args.js`

### `arguments-object/cls-decl-private-meth-args-trailing-comma-spread-operator.js` (1)
- **fail** `language/arguments-object/cls-decl-private-meth-args-trailing-comma-spread-operator.js`

### `arguments-object/cls-decl-private-meth-args-trailing-comma-undefined.js` (1)
- **fail** `language/arguments-object/cls-decl-private-meth-args-trailing-comma-undefined.js`

### `arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-multiple.js` (1)
- **fail** `language/arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-multiple.js`

### `arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-null.js` (1)
- **fail** `language/arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-null.js`

### `arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-single-args.js` (1)
- **fail** `language/arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-single-args.js`

### `arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-spread-operator.js` (1)
- **fail** `language/arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-spread-operator.js`

### `arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-undefined.js` (1)
- **fail** `language/arguments-object/cls-expr-async-private-gen-meth-args-trailing-comma-undefined.js`

### `arguments-object/cls-expr-private-gen-meth-args-trailing-comma-multiple.js` (1)
- **fail** `language/arguments-object/cls-expr-private-gen-meth-args-trailing-comma-multiple.js`

### `arguments-object/cls-expr-private-gen-meth-args-trailing-comma-null.js` (1)
- **fail** `language/arguments-object/cls-expr-private-gen-meth-args-trailing-comma-null.js`

### `arguments-object/cls-expr-private-gen-meth-args-trailing-comma-single-args.js` (1)
- **fail** `language/arguments-object/cls-expr-private-gen-meth-args-trailing-comma-single-args.js`

### `arguments-object/cls-expr-private-gen-meth-args-trailing-comma-spread-operator.js` (1)
- **fail** `language/arguments-object/cls-expr-private-gen-meth-args-trailing-comma-spread-operator.js`

### `arguments-object/cls-expr-private-gen-meth-args-trailing-comma-undefined.js` (1)
- **fail** `language/arguments-object/cls-expr-private-gen-meth-args-trailing-comma-undefined.js`

### `arguments-object/cls-expr-private-meth-args-trailing-comma-multiple.js` (1)
- **fail** `language/arguments-object/cls-expr-private-meth-args-trailing-comma-multiple.js`

### `arguments-object/cls-expr-private-meth-args-trailing-comma-null.js` (1)
- **fail** `language/arguments-object/cls-expr-private-meth-args-trailing-comma-null.js`

### `arguments-object/cls-expr-private-meth-args-trailing-comma-single-args.js` (1)
- **fail** `language/arguments-object/cls-expr-private-meth-args-trailing-comma-single-args.js`

### `arguments-object/cls-expr-private-meth-args-trailing-comma-spread-operator.js` (1)
- **fail** `language/arguments-object/cls-expr-private-meth-args-trailing-comma-spread-operator.js`

### `arguments-object/cls-expr-private-meth-args-trailing-comma-undefined.js` (1)
- **fail** `language/arguments-object/cls-expr-private-meth-args-trailing-comma-undefined.js`

### `directive-prologue/10.1.1-30-s.js` (1)
- **fail** `language/directive-prologue/10.1.1-30-s.js`

### `directive-prologue/10.1.1-31-s.js` (1)
- **fail** `language/directive-prologue/10.1.1-31-s.js`

### `directive-prologue/10.1.1-32-s.js` (1)
- **fail** `language/directive-prologue/10.1.1-32-s.js`

### `directive-prologue/set-accsr-inside-func-expr-runtime.js` (1)
- **fail** `language/directive-prologue/set-accsr-inside-func-expr-runtime.js`

### `directive-prologue/set-accsr-not-first-runtime.js` (1)
- **fail** `language/directive-prologue/set-accsr-not-first-runtime.js`

### `directive-prologue/set-accsr-runtime.js` (1)
- **fail** `language/directive-prologue/set-accsr-runtime.js`

### `expressions/await` (1)
- **fail** `language/expressions/await/await-in-global.js`

### `expressions/delete` (1)
- **fail** `language/expressions/delete/identifier-strict-recursive.js`

### `expressions/does-not-equals` (1)
- **fail** `language/expressions/does-not-equals/S11.9.2_A3.2.js`

### `expressions/exponentiation` (1)
- **fail** `language/expressions/exponentiation/exp-operator-syntax-error-logical-not-unary-expression-base.js`

### `expressions/generators` (1)
- **fail** `language/expressions/generators/dstr/ary-init-iter-no-close.js`

### `expressions/in` (1)
- **error** `language/expressions/in/private-field-invalid-identifier-complex.js`

### `expressions/template-literal` (1)
- **fail** `language/expressions/template-literal/invalid-unicode-escape-sequence-8.js`

### `global-code/invalid-private-names-call-expression-this.js` (1)
- **fail** `language/global-code/invalid-private-names-call-expression-this.js`

### `global-code/switch-dflt-decl-strict.js` (1)
- **fail** `language/global-code/switch-dflt-decl-strict.js`

### `identifiers/other_id_continue-escaped.js` (1)
- **error** `language/identifiers/other_id_continue-escaped.js`

### `identifiers/part-unicode-11.0.0-class-escaped.js` (1)
- **error** `language/identifiers/part-unicode-11.0.0-class-escaped.js`

### `identifiers/part-unicode-12.0.0-escaped.js` (1)
- **error** `language/identifiers/part-unicode-12.0.0-escaped.js`

### `identifiers/part-unicode-12.0.0.js` (1)
- **error** `language/identifiers/part-unicode-12.0.0.js`

### `identifiers/part-unicode-5.2.0-escaped.js` (1)
- **error** `language/identifiers/part-unicode-5.2.0-escaped.js`

### `identifiers/part-unicode-8.0.0.js` (1)
- **error** `language/identifiers/part-unicode-8.0.0.js`

### `identifiers/start-unicode-14.0.0-escaped.js` (1)
- **error** `language/identifiers/start-unicode-14.0.0-escaped.js`

### `identifiers/start-unicode-14.0.0.js` (1)
- **error** `language/identifiers/start-unicode-14.0.0.js`

### `identifiers/start-unicode-16.0.0-class-escaped.js` (1)
- **error** `language/identifiers/start-unicode-16.0.0-class-escaped.js`

### `identifiers/start-unicode-6.0.0-escaped.js` (1)
- **error** `language/identifiers/start-unicode-6.0.0-escaped.js`

### `identifiers/start-unicode-6.0.0.js` (1)
- **error** `language/identifiers/start-unicode-6.0.0.js`

### `identifiers/vals-rus-alpha-lower-via-escape-hex.js` (1)
- **error** `language/identifiers/vals-rus-alpha-lower-via-escape-hex.js`

### `identifiers/vals-rus-alpha-lower.js` (1)
- **error** `language/identifiers/vals-rus-alpha-lower.js`

### `identifiers/vals-rus-alpha-upper.js` (1)
- **error** `language/identifiers/vals-rus-alpha-upper.js`

### `module-code/instn-star-props-nrml.js` (1)
- **error** `language/module-code/instn-star-props-nrml.js`

### `statementList/class-expr-arrow-function-boolean-literal.js` (1)
- **error** `language/statementList/class-expr-arrow-function-boolean-literal.js`

### `white-space/mongolian-vowel-separator-eval.js` (1)
- **fail** `language/white-space/mongolian-vowel-separator-eval.js`

## Fixed sample (language, first 80)

- `annexB/language/eval-code/direct/func-block-decl-eval-func-existing-block-fn-no-init.js`
- `language/arguments-object/cls-decl-private-gen-meth-static-args-trailing-comma-single-args.js`
- `language/arguments-object/unmapped/via-params-dstr.js`
- `language/arguments-object/unmapped/via-params-rest.js`
- `language/asi/S7.9_A7_T4.js`
- `language/asi/S7.9_A7_T8.js`
- `language/asi/S7.9_A7_T9.js`
- `language/block-scope/syntax/redeclaration/inner-block-var-name-redeclaration-attempt-with-var.js`
- `language/comments/S7.4_A4_T2.js`
- `language/comments/multi-line-asi-carriage-return.js`
- `language/comments/multi-line-asi-line-feed.js`
- `language/comments/multi-line-asi-line-separator.js`
- `language/comments/multi-line-asi-paragraph-separator.js`
- `language/computed-property-names/class/accessor/setter.js`
- `language/computed-property-names/class/method/constructor-can-be-setter.js`
- `language/directive-prologue/10.1.1-29-s.js`
- `language/directive-prologue/get-accsr-inside-func-expr-runtime.js`
- `language/directive-prologue/get-accsr-runtime.js`
- `language/eval-code/direct/block-decl-onlystrict.js`
- `language/eval-code/direct/lex-env-distinct-cls.js`
- `language/eval-code/direct/super-call.js`
- `language/eval-code/direct/var-env-var-init-global-exstng.js`
- `language/eval-code/indirect/lex-env-distinct-cls.js`
- `language/eval-code/indirect/var-env-var-init-global-exstng.js`
- `language/expressions/addition/S11.6.1_A1.js`
- `language/expressions/addition/S11.6.1_A2.2_T2.js`
- `language/expressions/addition/S11.6.1_A2.2_T3.js`
- `language/expressions/addition/S11.6.1_A3.2_T1.2.js`
- `language/expressions/addition/bigint-and-number.js`
- `language/expressions/addition/bigint-arithmetic.js`
- `language/expressions/addition/bigint-errors.js`
- `language/expressions/addition/bigint-toprimitive.js`
- `language/expressions/addition/bigint-wrapped-values.js`
- `language/expressions/addition/coerce-bigint-to-string.js`
- `language/expressions/addition/coerce-symbol-to-prim-err.js`
- `language/expressions/addition/coerce-symbol-to-prim-invocation.js`
- `language/expressions/addition/coerce-symbol-to-prim-return-obj.js`
- `language/expressions/addition/coerce-symbol-to-prim-return-prim.js`
- `language/expressions/addition/get-symbol-to-prim-err.js`
- `language/expressions/addition/order-of-evaluation.js`
- `language/expressions/addition/symbol-to-string.js`
- `language/expressions/array/spread-err-mult-err-itr-get-call.js`
- `language/expressions/array/spread-err-sngl-err-itr-get-get.js`
- `language/expressions/array/spread-obj-with-overrides.js`
- `language/expressions/arrow-function/dflt-params-arg-val-not-undefined.js`
- `language/expressions/arrow-function/dstr/ary-init-iter-get-err.js`
- `language/expressions/arrow-function/dstr/ary-ptrn-elem-ary-elem-iter.js`
- `language/expressions/arrow-function/dstr/ary-ptrn-elem-id-init-skipped.js`
- `language/expressions/arrow-function/dstr/dflt-ary-ptrn-elem-id-init-skipped.js`
- `language/expressions/arrow-function/dstr/dflt-obj-ptrn-id-init-skipped.js`
- `language/expressions/arrow-function/dstr/dflt-obj-ptrn-rest-getter.js`
- `language/expressions/arrow-function/dstr/obj-ptrn-id-init-skipped.js`
- `language/expressions/arrow-function/dstr/obj-ptrn-rest-getter.js`
- `language/expressions/arrow-function/lexical-super-property.js`
- `language/expressions/arrow-function/params-trailing-comma-single.js`
- `language/expressions/arrow-function/scope-paramsbody-var-open.js`
- `language/expressions/assignment/dstr/array-elem-init-fn-name-arrow.js`
- `language/expressions/assignment/dstr/array-elem-init-let.js`
- `language/expressions/assignment/dstr/array-elem-init-order.js`
- `language/expressions/assignment/dstr/array-elem-nested-array-undefined-hole.js`
- `language/expressions/assignment/dstr/array-elem-nested-array-undefined-own.js`
- `language/expressions/assignment/dstr/array-elem-nested-array-undefined.js`
- `language/expressions/assignment/dstr/array-elem-nested-obj-yield-expr.js`
- `language/expressions/assignment/dstr/array-elem-nested-obj-yield-ident-valid.js`
- `language/expressions/assignment/dstr/array-elem-trlg-iter-list-rtrn-close.js`
- `language/expressions/assignment/dstr/array-elem-trlg-iter-rest-nrml-close-skip.js`
- `language/expressions/assignment/dstr/array-rest-iter-thrw-close-err.js`
- `language/expressions/assignment/dstr/array-rest-nested-array-yield-ident-valid.js`
- `language/expressions/assignment/dstr/array-rest-nested-obj-null.js`
- `language/expressions/assignment/dstr/array-rest-nested-obj-undefined-own.js`
- `language/expressions/assignment/dstr/array-rest-put-unresolvable-no-strict.js`
- `language/expressions/assignment/dstr/obj-id-init-assignment-missing.js`
- `language/expressions/assignment/dstr/obj-id-init-assignment-null.js`
- `language/expressions/assignment/dstr/obj-id-init-assignment-truthy.js`
- `language/expressions/assignment/dstr/obj-id-init-assignment-undef.js`
- `language/expressions/assignment/dstr/obj-id-init-evaluation.js`
- `language/expressions/assignment/dstr/obj-id-init-yield-expr.js`
- `language/expressions/assignment/dstr/obj-prop-elem-init-assignment-truthy.js`
- `language/expressions/assignment/dstr/obj-prop-elem-init-assignment-undef.js`
- `language/expressions/assignment/dstr/obj-prop-elem-init-fn-name-class.js`
- … +810 more language fixes

