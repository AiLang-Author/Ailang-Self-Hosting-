# Knockout list — M128e7bh (language residuals)

Tip `70ad3b2b` · language residual **2,671** (fail+error+timeout) · G2 gap **1,490**

## Priority bands

| Band | Criteria | Use |
|------|----------|-----|
| **P0 near-complete** | residual 1–25, pass% ≥ 70% | grind 100% chips |
| **P1 medium residual** | residual 26–80 | engine feature slices |
| **P2 bulk residual** | residual > 80 | class/private/for-of/eval |

## P0 — near-complete (knock out first)

| Category | Residual | Pass/Total | Pass% |
|----------|---------:|-----------:|------:|
| `expressions/delete` | 1 | 68/69 | 98.6% |
| `expressions/template-literal` | 1 | 56/57 | 98.2% |
| `expressions/exponentiation` | 1 | 43/44 | 97.7% |
| `expressions/does-not-equals` | 1 | 37/38 | 97.4% |
| `expressions/coalesce` | 1 | 23/24 | 95.8% |
| `statements/continue` | 1 | 23/24 | 95.8% |
| `statements/break` | 1 | 19/20 | 95.0% |
| `types/object` | 1 | 18/19 | 94.7% |
| `expressions/logical-and` | 1 | 17/18 | 94.4% |
| `expressions/logical-or` | 1 | 17/18 | 94.4% |
| `block-scope/leave` | 1 | 14/15 | 93.3% |
| `statements/async-function` | 2 | 72/74 | 97.3% |
| `expressions/in` | 2 | 34/36 | 94.4% |
| `statements/do-while` | 2 | 34/36 | 94.4% |
| `expressions/conditional` | 2 | 20/22 | 90.9% |
| `types/number` | 2 | 19/21 | 90.5% |
| `destructuring/binding` | 2 | 17/19 | 89.5% |
| `statements/return` | 2 | 14/16 | 87.5% |
| `block-scope/shadowing` | 2 | 13/15 | 86.7% |
| `expressions/new.target` | 2 | 12/14 | 85.7% |
| `computed-property-names/object` | 2 | 10/12 | 83.3% |
| `types/undefined` | 2 | 6/8 | 75.0% |
| `expressions/async-function` | 3 | 90/93 | 96.8% |
| `literals/string` | 3 | 70/73 | 95.9% |
| `arguments-object/mapped` | 3 | 40/43 | 93.0% |
| `statements/block` | 3 | 18/21 | 85.7% |
| `statements/async-generator` | 4 | 297/301 | 98.7% |
| `statements/with` | 4 | 177/181 | 97.8% |
| `module-code/namespace` | 4 | 34/38 | 89.5% |
| `expressions/await` | 4 | 18/22 | 81.8% |
| `expressions/dynamic-import` | 5 | 936/941 | 99.5% |
| `types/reference` | 5 | 24/29 | 82.8% |
| `expressions/compound-assignment` | 6 | 448/454 | 98.7% |
| `statements/while` | 6 | 32/38 | 84.2% |
| `expressions/import.meta` | 6 | 16/22 | 72.7% |
| `statements/labeled` | 7 | 17/24 | 70.8% |
| `statements/const` | 8 | 128/136 | 94.1% |
| `expressions/async-generator` | 9 | 614/623 | 98.6% |
| `expressions/logical-assignment` | 9 | 69/78 | 88.5% |
| `expressions/assignment` | 10 | 475/485 | 97.9% |
| `expressions/call` | 10 | 82/92 | 89.1% |
| `statements/if` | 10 | 59/69 | 85.5% |
| `eval-code/indirect` | 10 | 51/61 | 83.6% |
| `statements/generators` | 12 | 254/266 | 95.5% |
| `statements/let` | 13 | 132/145 | 91.0% |
| `statements/await-using` | 13 | 81/94 | 86.2% |
| `statements/variable` | 15 | 163/178 | 91.6% |
| `statements/switch` | 17 | 94/111 | 84.7% |
| `statements/for` | 18 | 367/385 | 95.3% |
| `expressions/function` | 18 | 246/264 | 93.2% |
| `expressions/arrow-function` | 19 | 324/343 | 94.5% |
| `expressions/generators` | 19 | 271/290 | 93.4% |
| `expressions/super` | 20 | 74/94 | 78.7% |
| `statements/function` | 24 | 427/451 | 94.7% |
| `eval-code/direct` | 24 | 262/286 | 91.6% |
| `statements/for-in` | 24 | 91/115 | 79.1% |

## P1 — medium residual

| Category | Residual | Pass/Total | Pass% |
|----------|---------:|-----------:|------:|
| `statements/try` | 28 | 173/201 | 86.1% |
| `module-code/top-level-await` | 29 | 222/251 | 88.4% |
| `literals/regexp` | 31 | 207/238 | 87.0% |
| `expressions/yield` | 32 | 31/63 | 49.2% |
| `expressions/object` | 37 | 1124/1161 | 96.8% |
| `statements/using` | 40 | 38/78 | 48.7% |
| `import/import-defer` | 45 | 56/101 | 55.4% |
| `statements/for-of` | 70 | 681/751 | 90.7% |

## P2 — bulk residual

| Category | Residual | Pass/Total | Pass% |
|----------|---------:|-----------:|------:|
| `expressions/class` | 575 | 3484/4059 | 85.8% |
| `statements/class` | 1107 | 3260/4367 | 74.7% |

## P0 failing paths (sample ≤15 per category)

### `arguments-object/mapped` (3 residual)
- **fail** `language/arguments-object/mapped/enumerable-configurable-accessor-descriptor.js` exit=b'1'
- **fail** `language/arguments-object/mapped/mapped-arguments-nonwritable-nonconfigurable-2.js` exit=b'1'
- **fail** `language/arguments-object/mapped/mapped-arguments-nonwritable-nonconfigurable-4.js` exit=b'1'

### `block-scope/leave` (1 residual)
- **fail** `language/block-scope/leave/outermost-binding-updated-in-catch-block-nested-block-let-declaration-unseen-outside-of-block.js` exit=b'1'

### `block-scope/shadowing` (2 residual)
- **fail** `language/block-scope/shadowing/catch-parameter-shadowing-let-declaration.js` exit=b'1'
- **fail** `language/block-scope/shadowing/parameter-name-shadowing-parameter-name-let-const-and-var.js` exit=b'1'

### `computed-property-names/object` (2 residual)
- **fail** `language/computed-property-names/object/method/number.js` exit=b'1'
- **fail** `language/computed-property-names/object/method/symbol.js` exit=b'1'

### `destructuring/binding` (2 residual)
- **fail** `language/destructuring/binding/keyed-destructuring-property-reference-target-evaluation-order-with-bindings.js` exit=b'1'
- **fail** `language/destructuring/binding/typedarray-backed-by-resizable-buffer.js` exit=b'1'

### `eval-code/direct` (24 residual)
- **fail** `language/eval-code/direct/arrow-fn-body-cntns-arguments-func-decl-arrow-func-declare-arguments-assign-incl-def-param-arrow-arguments.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-body-cntns-arguments-func-decl-arrow-func-declare-arguments-assign.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-body-cntns-arguments-lex-bind-arrow-func-declare-arguments-assign-incl-def-param-arrow-arguments.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-body-cntns-arguments-lex-bind-arrow-func-declare-arguments-assign.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-body-cntns-arguments-var-bind-arrow-func-declare-arguments-assign-incl-def-param-arrow-arguments.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-body-cntns-arguments-var-bind-arrow-func-declare-arguments-assign.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-no-pre-existing-arguments-bindings-are-present-arrow-func-declare-arguments-assign-incl-def-param-arrow-arguments.js` exit=b'1'
- **fail** `language/eval-code/direct/arrow-fn-no-pre-existing-arguments-bindings-are-present-arrow-func-declare-arguments-assign.js` exit=b'1'
- **fail** `language/eval-code/direct/export.js` exit=b'1'
- **fail** `language/eval-code/direct/global-env-rec-catch.js` exit=b'1'
- **fail** `language/eval-code/direct/global-env-rec-eval.js` exit=b'1'
- **fail** `language/eval-code/direct/global-env-rec-fun.js` exit=b'1'
- **fail** `language/eval-code/direct/global-env-rec-with.js` exit=b'1'
- **fail** `language/eval-code/direct/global-env-rec.js` exit=b'1'
- **fail** `language/eval-code/direct/import.js` exit=b'1'
- … +9 more

### `eval-code/indirect` (10 residual)
- **fail** `language/eval-code/indirect/export.js` exit=b'1'
- **fail** `language/eval-code/indirect/import.js` exit=b'1'
- **fail** `language/eval-code/indirect/lex-env-distinct-const.js` exit=b'1'
- **fail** `language/eval-code/indirect/lex-env-distinct-let.js` exit=b'1'
- **fail** `language/eval-code/indirect/lex-env-heritage.js` exit=b'1'
- **fail** `language/eval-code/indirect/realm.js` exit=b'1'
- **fail** `language/eval-code/indirect/var-env-func-init-global-new.js` exit=b'1'
- **fail** `language/eval-code/indirect/var-env-func-init-multi.js` exit=b'1'
- **fail** `language/eval-code/indirect/var-env-var-init-global-new.js` exit=b'1'
- **fail** `language/eval-code/indirect/var-env-var-strict.js` exit=b'1'

### `expressions/arrow-function` (19 residual)
- **fail** `language/expressions/arrow-function/ArrowFunction_restricted-properties.js` exit=b'1'
- **fail** `language/expressions/arrow-function/cannot-override-this-with-thisArg.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/lexical-new.target-closure-returned.js` exit=b'1'
- **fail** `language/expressions/arrow-function/lexical-new.target.js` exit=b'1'
- **error** `language/expressions/arrow-function/lexical-super-call-from-within-constructor.js` harness_eof
- **error** `language/expressions/arrow-function/lexical-super-property-from-within-constructor.js` harness_eof
- **error** `language/expressions/arrow-function/lexical-supercall-from-immediately-invoked-arrow.js` harness_eof
- **fail** `language/expressions/arrow-function/lexical-this.js` exit=b'1'
- **fail** `language/expressions/arrow-function/scope-param-rest-elem-var-close.js` exit=b'1'
- **fail** `language/expressions/arrow-function/scope-param-rest-elem-var-open.js` exit=b'1'
- … +4 more

### `expressions/assignment` (10 residual)
- **fail** `language/expressions/assignment/11.13.1-4-6-s.js` exit=b'1'
- **fail** `language/expressions/assignment/destructuring/target-assign-throws-iterator-return-get-throws.js` exit=b'1'
- **fail** `language/expressions/assignment/destructuring/target-assign-throws-iterator-return-is-not-callable.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-elem-put-prop-ref-user-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-rest-put-prop-ref-user-err-iter-close-skip.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-rest-put-prop-ref-user-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/obj-prop-put-prop-ref-user-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/obj-rest-getter-abrupt-get-error.js` exit=b'1'
- **fail** `language/expressions/assignment/fn-name-lhs-member.js` exit=b'1'
- **fail** `language/expressions/assignment/target-super-computed-reference-null.js` exit=b'1'

### `expressions/async-function` (3 residual)
- **fail** `language/expressions/async-function/await-as-identifier-reference-escaped.js` exit=b'0'
- **fail** `language/expressions/async-function/early-errors-expression-body-contains-super-property.js` exit=b'0'
- **fail** `language/expressions/async-function/named-await-as-label-identifier-escaped.js` exit=b'0'

### `expressions/async-generator` (9 residual)
- **fail** `language/expressions/async-generator/await-as-label-identifier-escaped.js` exit=b'0'
- **fail** `language/expressions/async-generator/default-proto.js` exit=b'1'
- **fail** `language/expressions/async-generator/dstr/dflt-ary-init-iter-close.js` exit=b'1'
- **fail** `language/expressions/async-generator/eval-body-proto-realm.js` exit=b'1'
- **fail** `language/expressions/async-generator/eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/async-generator/expression-yield-star-before-newline.js` exit=b'1'
- **fail** `language/expressions/async-generator/named-eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/async-generator/named-yield-promise-reject-next-yield-star-async-iterator.js` exit=b'1'
- **fail** `language/expressions/async-generator/yield-promise-reject-next-yield-star-async-iterator.js` exit=b'1'

### `expressions/await` (4 residual)
- **fail** `language/expressions/await/await-BindingIdentifier-in-global.js` exit=b'1'
- **fail** `language/expressions/await/await-in-function.js` exit=b'1'
- **fail** `language/expressions/await/await-in-generator.js` exit=b'1'
- **fail** `language/expressions/await/await-in-global.js` exit=b'1'

### `expressions/call` (10 residual)
- **fail** `language/expressions/call/eval-realm-indirect.js` exit=b'1'
- **fail** `language/expressions/call/eval-spread-empty-leading.js` exit=b'1'
- **fail** `language/expressions/call/eval-spread-empty-trailing.js` exit=b'1'
- **fail** `language/expressions/call/eval-spread.js` exit=b'1'
- **fail** `language/expressions/call/tco-call-args.js` exit=b'1'
- **fail** `language/expressions/call/tco-member-args.js` exit=b'1'
- **fail** `language/expressions/call/tco-non-eval-function-dynamic.js` exit=b'1'
- **fail** `language/expressions/call/tco-non-eval-function.js` exit=b'1'
- **fail** `language/expressions/call/tco-non-eval-global.js` exit=b'1'
- **fail** `language/expressions/call/tco-non-eval-with.js` exit=b'1'

### `expressions/coalesce` (1 residual)
- **fail** `language/expressions/coalesce/tco-pos-null.js` exit=b'1'

### `expressions/compound-assignment` (6 residual)
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-accessor-property-exp.js` harness_eof
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-bitand.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-div.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-lshift.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-rshift.js` exit=b'1'
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-method-mod.js` harness_eof

### `expressions/conditional` (2 residual)
- **fail** `language/expressions/conditional/tco-cond.js` exit=b'1'
- **fail** `language/expressions/conditional/tco-pos.js` exit=b'1'

### `expressions/delete` (1 residual)
- **fail** `language/expressions/delete/identifier-strict-recursive.js` exit=b'0'

### `expressions/does-not-equals` (1 residual)
- **fail** `language/expressions/does-not-equals/S11.9.2_A3.2.js` exit=b'1'

### `expressions/dynamic-import` (5 residual)
- **timeout** `language/expressions/dynamic-import/await-import-evaluation.js` timeout
- **fail** `language/expressions/dynamic-import/escape-sequence-import.js` exit=b'0'
- **fail** `language/expressions/dynamic-import/import-attributes/2nd-param-in.js` exit=b'1'
- **fail** `language/expressions/dynamic-import/syntax/invalid/nested-async-arrow-function-return-await-import-source-assignment-expr-not-optional.js` exit=b'0'
- **fail** `language/expressions/dynamic-import/syntax/invalid/nested-async-gen-await-import-source-assignment-expr-not-optional.js` exit=b'0'

### `expressions/exponentiation` (1 residual)
- **fail** `language/expressions/exponentiation/exp-operator-syntax-error-logical-not-unary-expression-base.js` exit=b'0'

### `expressions/function` (18 residual)
- **fail** `language/expressions/function/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/early-body-super-prop.js` exit=b'0'
- **fail** `language/expressions/function/eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/function/named-strict-error-reassign-fn-name-in-body-in-arrow.js` exit=b'1'
- **fail** `language/expressions/function/named-strict-error-reassign-fn-name-in-body-in-eval.js` exit=b'1'
- **fail** `language/expressions/function/scope-name-var-close.js` exit=b'1'
- **fail** `language/expressions/function/scope-name-var-open-non-strict.js` exit=b'1'
- **fail** `language/expressions/function/scope-name-var-open-strict.js` exit=b'1'
- **fail** `language/expressions/function/scope-param-elem-var-close.js` exit=b'1'
- **fail** `language/expressions/function/scope-param-elem-var-open.js` exit=b'1'
- **fail** `language/expressions/function/scope-param-rest-elem-var-close.js` exit=b'1'
- **fail** `language/expressions/function/scope-param-rest-elem-var-open.js` exit=b'1'
- … +3 more

### `expressions/generators` (19 residual)
- **fail** `language/expressions/generators/default-proto.js` exit=b'1'
- **fail** `language/expressions/generators/dstr/ary-init-iter-no-close.js` exit=b'1'
- **fail** `language/expressions/generators/eval-body-proto-realm.js` exit=b'1'
- **fail** `language/expressions/generators/eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/generators/named-no-strict-reassign-fn-name-in-body-in-arrow.js` exit=b'1'
- **fail** `language/expressions/generators/named-no-strict-reassign-fn-name-in-body-in-eval.js` exit=b'1'
- **fail** `language/expressions/generators/named-no-strict-reassign-fn-name-in-body.js` exit=b'1'
- **fail** `language/expressions/generators/named-strict-error-reassign-fn-name-in-body-in-arrow.js` exit=b'1'
- **fail** `language/expressions/generators/named-strict-error-reassign-fn-name-in-body-in-eval.js` exit=b'1'
- **fail** `language/expressions/generators/scope-name-var-close.js` exit=b'1'
- **fail** `language/expressions/generators/scope-name-var-open-non-strict.js` exit=b'1'
- **fail** `language/expressions/generators/scope-name-var-open-strict.js` exit=b'1'
- **fail** `language/expressions/generators/scope-param-elem-var-close.js` exit=b'1'
- **fail** `language/expressions/generators/scope-param-elem-var-open.js` exit=b'1'
- **fail** `language/expressions/generators/scope-param-rest-elem-var-close.js` exit=b'1'
- … +4 more

### `expressions/import.meta` (6 residual)
- **fail** `language/expressions/import.meta/distinct-for-each-module.js` exit=b'1'
- **fail** `language/expressions/import.meta/not-accessible-from-direct-eval.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-async-function-params-or-body.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-async-generator-params-or-body.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-function-params-or-body.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-generator-params-or-body.js` exit=b'1'

### `expressions/in` (2 residual)
- **error** `language/expressions/in/private-field-invalid-identifier-complex.js` harness_eof
- **error** `language/expressions/in/private-field-rhs-unresolvable.js` harness_eof

### `expressions/logical-and` (1 residual)
- **fail** `language/expressions/logical-and/tco-right.js` exit=b'1'

### `expressions/logical-assignment` (9 residual)
- **fail** `language/expressions/logical-assignment/lgcl-and-assignment-operator-namedevaluation-arrow-function.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-and-assignment-operator-namedevaluation-class-expression.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-and-assignment-operator-namedevaluation-function.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-nullish-assignment-operator-namedevaluation-arrow-function.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-nullish-assignment-operator-namedevaluation-class-expression.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-nullish-assignment-operator-namedevaluation-function.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-or-assignment-operator-namedevaluation-arrow-function.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-or-assignment-operator-namedevaluation-class-expression.js` exit=b'1'
- **fail** `language/expressions/logical-assignment/lgcl-or-assignment-operator-namedevaluation-function.js` exit=b'1'

### `expressions/logical-or` (1 residual)
- **fail** `language/expressions/logical-or/tco-right.js` exit=b'1'

### `expressions/new.target` (2 residual)
- **error** `language/expressions/new.target/value-via-super-call.js` harness_eof
- **error** `language/expressions/new.target/value-via-super-property.js` harness_eof

### `expressions/super` (20 residual)
- **fail** `language/expressions/super/call-construct-invocation.js` exit=b'1'
- **fail** `language/expressions/super/call-proto-not-ctor.js` exit=b'1'
- **error** `language/expressions/super/call-spread-mult-expr.js` harness_eof
- **error** `language/expressions/super/call-spread-mult-obj-undefined.js` harness_eof
- **fail** `language/expressions/super/call-spread-obj-getter-init.js` exit=b'1'
- **fail** `language/expressions/super/prop-dot-obj-val-from-arrow.js` exit=b'1'
- **error** `language/expressions/super/prop-expr-cls-null-proto.js` harness_eof
- **fail** `language/expressions/super/prop-expr-cls-ref-strict.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-cls-ref-this.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-getsuperbase-before-topropertykey-putvalue-compound-assign.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-getsuperbase-before-topropertykey-putvalue-increment.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-getsuperbase-before-topropertykey-putvalue.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-obj-ref-non-strict.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-obj-ref-strict.js` exit=b'1'
- **fail** `language/expressions/super/prop-expr-obj-ref-this.js` exit=b'1'
- … +5 more

### `expressions/template-literal` (1 residual)
- **fail** `language/expressions/template-literal/invalid-unicode-escape-sequence-8.js` exit=b'0'

### `literals/string` (3 residual)
- **error** `language/literals/string/S7.8.4_A4.2_T1.js` harness_eof
- **fail** `language/literals/string/S7.8.4_A6.1_T2.js` exit=b'1'
- **error** `language/literals/string/S7.8.4_A7.3_T1.js` harness_eof

### `module-code/namespace` (4 residual)
- **fail** `language/module-code/namespace/internals/delete-exported-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/set.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/super-access-to-tdz-binding.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/super-set-to-tdz-binding-with-accessor.js` exit=b'1'

### `statements/async-function` (2 residual)
- **timeout** `language/statements/async-function/cptn-decl.js` timeout
- **fail** `language/statements/async-function/syntax-declaration-no-line-terminator.js` exit=b'1'

### `statements/async-generator` (4 residual)
- **fail** `language/statements/async-generator/eval-var-scope-syntax-err.js` exit=b'1'
- **timeout** `language/statements/async-generator/yield-identifier-spread-strict.js` timeout
- **fail** `language/statements/async-generator/yield-promise-reject-next-yield-star-async-iterator.js` exit=b'1'
- **fail** `language/statements/async-generator/yield-star-async-from-sync-iterator-inaccessible.js` exit=b'1'

### `statements/await-using` (13 residual)
- **fail** `language/statements/await-using/initializer-Symbol.asyncDispose-called-at-end-of-each-iteration-of-forofstatement.js` exit=b'1'
- **fail** `language/statements/await-using/initializer-Symbol.asyncDispose-called-at-end-of-forstatement.js` exit=b'1'
- **fail** `language/statements/await-using/initializer-Symbol.asyncDispose-called-if-subsequent-initializer-throws-in-forstatement-head.js` exit=b'1'
- **fail** `language/statements/await-using/initializer-Symbol.dispose-called-at-end-of-each-iteration-of-forofstatement.js` exit=b'1'
- **fail** `language/statements/await-using/initializer-Symbol.dispose-called-at-end-of-forstatement.js` exit=b'1'
- **fail** `language/statements/await-using/initializer-Symbol.dispose-called-if-subsequent-initializer-throws-in-forstatement-head.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using-allowed-at-top-level-of-module.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using-declaring-let-split-across-two-lines.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using-invalid-assignment-next-expression-for.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using-invalid-assignment-statement-body-for-of.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using-outer-inner-using-bindings.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using-valid-for-await-using-of-of.js` exit=b'1'
- **fail** `language/statements/await-using/syntax/await-using.js` exit=b'1'

### `statements/block` (3 residual)
- **timeout** `language/statements/block/labeled-continue.js` timeout
- **fail** `language/statements/block/tco-stmt-list.js` exit=b'1'
- **fail** `language/statements/block/tco-stmt.js` exit=b'1'

### `statements/break` (1 residual)
- **fail** `language/statements/break/line-terminators.js` exit=b'1'

### `statements/const` (8 residual)
- **fail** `language/statements/const/cptn-value.js` exit=b'1'
- **fail** `language/statements/const/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/const/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/const/function-local-closure-get-before-initialization.js` exit=b'1'
- **fail** `language/statements/const/syntax/const-invalid-assignment-statement-body-for-in.js` exit=b'1'
- **fail** `language/statements/const/syntax/const-invalid-assignment-statement-body-for-of.js` exit=b'1'
- **fail** `language/statements/const/syntax/const-outer-inner-let-bindings.js` exit=b'1'
- **fail** `language/statements/const/syntax/const.js` exit=b'1'

### `statements/continue` (1 residual)
- **fail** `language/statements/continue/line-terminators.js` exit=b'1'

### `statements/do-while` (2 residual)
- **fail** `language/statements/do-while/S12.6.1_A10.js` exit=b'1'
- **fail** `language/statements/do-while/tco-body.js` exit=b'1'

### `statements/for` (18 residual)
- **fail** `language/statements/for/cptn-decl-expr-iter.js` exit=b'1'
- **fail** `language/statements/for/cptn-expr-expr-iter.js` exit=b'1'
- **fail** `language/statements/for/dstr/const-ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/for/dstr/const-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/for/dstr/let-ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/for/dstr/let-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/for/head-let-destructuring.js` exit=b'1'
- **fail** `language/statements/for/head-lhs-let.js` exit=b'1'
- **fail** `language/statements/for/scope-body-lex-boundary.js` exit=b'1'
- **fail** `language/statements/for/scope-body-lex-open.js` exit=b'1'
- **fail** `language/statements/for/scope-body-var-none.js` exit=b'1'
- **fail** `language/statements/for/scope-head-lex-close.js` exit=b'1'
- **fail** `language/statements/for/scope-head-lex-open.js` exit=b'1'
- **fail** `language/statements/for/scope-head-var-none.js` exit=b'1'
- **fail** `language/statements/for/tco-const-body.js` exit=b'1'
- … +3 more

### `statements/for-in` (24 residual)
- **fail** `language/statements/for-in/S12.6.4_A6.1.js` exit=b'1'
- **fail** `language/statements/for-in/S12.6.4_A6.js` exit=b'1'
- **fail** `language/statements/for-in/S12.6.4_A7_T2.js` exit=b'1'
- **fail** `language/statements/for-in/cptn-decl-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/for-in/cptn-decl-itr.js` exit=b'1'
- **fail** `language/statements/for-in/cptn-expr-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/for-in/cptn-expr-itr.js` exit=b'1'
- **fail** `language/statements/for-in/head-const-bound-names-fordecl-tdz.js` exit=b'1'
- **fail** `language/statements/for-in/head-let-bound-names-fordecl-tdz.js` exit=b'1'
- **fail** `language/statements/for-in/head-let-destructuring.js` exit=b'1'
- **fail** `language/statements/for-in/head-lhs-cover.js` exit=b'1'
- **fail** `language/statements/for-in/head-lhs-let.js` exit=b'1'
- **fail** `language/statements/for-in/head-var-bound-names-dup.js` exit=b'1'
- **fail** `language/statements/for-in/head-var-bound-names-in-stmt.js` exit=b'1'
- **fail** `language/statements/for-in/identifier-let-allowed-as-lefthandside-expression-not-strict.js` exit=b'1'
- … +9 more

### `statements/function` (24 residual)
- **fail** `language/statements/function/13.0-12-s.js` exit=b'1'
- **fail** `language/statements/function/13.0-17-s.js` exit=b'1'
- **fail** `language/statements/function/S13.2.1_A6_T3.js` exit=b'1'
- **fail** `language/statements/function/S13.2.2_A12.js` exit=b'1'
- **fail** `language/statements/function/S13.2.2_A19_T7.js` exit=b'1'
- **fail** `language/statements/function/S13.2.2_A8_T1.js` exit=b'1'
- **fail** `language/statements/function/S13.2.2_A8_T3.js` exit=b'1'
- **fail** `language/statements/function/S13.2_A4_T1.js` exit=b'1'
- **fail** `language/statements/function/S13.2_A4_T2.js` exit=b'1'
- **fail** `language/statements/function/S13_A15_T4.js` exit=b'1'
- **fail** `language/statements/function/S13_A19_T2.js` exit=b'1'
- **fail** `language/statements/function/cptn-decl.js` exit=b'1'
- **fail** `language/statements/function/dflt-params-duplicates.js` exit=b'0'
- **fail** `language/statements/function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/function/early-body-super-call.js` exit=b'0'
- … +9 more

### `statements/generators` (12 residual)
- **fail** `language/statements/generators/cptn-decl.js` exit=b'1'
- **fail** `language/statements/generators/default-proto.js` exit=b'1'
- **fail** `language/statements/generators/dflt-params-duplicates.js` exit=b'0'
- **fail** `language/statements/generators/scope-param-elem-var-close.js` exit=b'1'
- **fail** `language/statements/generators/scope-param-rest-elem-var-close.js` exit=b'1'
- **fail** `language/statements/generators/scope-param-rest-elem-var-open.js` exit=b'1'
- **fail** `language/statements/generators/unscopables-with-in-nested-fn.js` exit=b'1'
- **fail** `language/statements/generators/unscopables-with.js` exit=b'1'
- **fail** `language/statements/generators/yield-as-binding-identifier-escaped.js` exit=b'0'
- **fail** `language/statements/generators/yield-as-generator-declaration-binding-identifier.js` exit=b'1'
- **timeout** `language/statements/generators/yield-identifier-spread-strict.js` timeout
- **timeout** `language/statements/generators/yield-identifier-strict.js` timeout

### `statements/if` (10 residual)
- **fail** `language/statements/if/cptn-else-false-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/if/cptn-else-false-nrml.js` exit=b'1'
- **fail** `language/statements/if/cptn-else-true-nrml.js` exit=b'1'
- **fail** `language/statements/if/cptn-no-else-true-nrml.js` exit=b'1'
- **fail** `language/statements/if/if-decl-else-stmt-strict.js` exit=b'0'
- **fail** `language/statements/if/if-fun-no-else-strict.js` exit=b'0'
- **fail** `language/statements/if/if-stmt-else-fun-strict.js` exit=b'0'
- **fail** `language/statements/if/labelled-fn-stmt-lone.js` exit=b'0'
- **fail** `language/statements/if/tco-else-body.js` exit=b'1'
- **fail** `language/statements/if/tco-if-body.js` exit=b'1'

### `statements/labeled` (7 residual)
- **fail** `language/statements/labeled/continue.js` exit=b'0'
- **fail** `language/statements/labeled/cptn-break.js` exit=b'1'
- **fail** `language/statements/labeled/decl-async-generator.js` exit=b'0'
- **fail** `language/statements/labeled/decl-gen.js` exit=b'0'
- **fail** `language/statements/labeled/tco.js` exit=b'1'
- **fail** `language/statements/labeled/value-await-non-module.js` exit=b'1'
- **fail** `language/statements/labeled/value-yield-non-strict.js` exit=b'1'

### `statements/let` (13 residual)
- **fail** `language/statements/let/cptn-value.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-init-iter-close.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/let/function-local-closure-get-before-initialization.js` exit=b'1'
- **fail** `language/statements/let/function-local-closure-set-before-initialization.js` exit=b'1'
- **fail** `language/statements/let/global-closure-set-before-initialization.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-closure-inside-condition.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-closure-inside-initialization.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-closure-inside-next-expression.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-iteration-variable-is-freshly-allocated-for-each-iteration-multi-let-binding.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-outer-inner-let-bindings.js` exit=b'1'
- **fail** `language/statements/let/syntax/let.js` exit=b'1'

### `statements/return` (2 residual)
- **fail** `language/statements/return/line-terminators.js` exit=b'1'
- **fail** `language/statements/return/tco.js` exit=b'1'

### `statements/switch` (17 residual)
- **fail** `language/statements/switch/cptn-a-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/switch/cptn-b-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/switch/cptn-dflt-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/switch/cptn-dflt-b-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/switch/cptn-no-dflt-match-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/switch/scope-lex-async-function.js` exit=b'0'
- **fail** `language/statements/switch/scope-lex-async-generator.js` exit=b'0'
- **fail** `language/statements/switch/scope-lex-class.js` exit=b'0'
- **fail** `language/statements/switch/scope-lex-close-case.js` exit=b'1'
- **fail** `language/statements/switch/scope-lex-close-dflt.js` exit=b'1'
- **fail** `language/statements/switch/scope-lex-const.js` exit=b'0'
- **fail** `language/statements/switch/scope-lex-generator.js` exit=b'0'
- **fail** `language/statements/switch/scope-lex-open-dflt.js` exit=b'1'
- **fail** `language/statements/switch/scope-var-none-case.js` exit=b'1'
- **fail** `language/statements/switch/tco-case-body-dflt.js` exit=b'1'
- … +2 more

### `statements/variable` (15 residual)
- **fail** `language/statements/variable/12.2.1-18-s.js` exit=b'1'
- **fail** `language/statements/variable/12.2.1-22-s.js` exit=b'1'
- **fail** `language/statements/variable/12.2.1-3-s.js` exit=b'1'
- **fail** `language/statements/variable/12.2.1-6-s.js` exit=b'1'
- **fail** `language/statements/variable/12.2.1-7-s.js` exit=b'1'
- **fail** `language/statements/variable/S12.2_A11.js` exit=b'1'
- **fail** `language/statements/variable/S12.2_A2.js` exit=b'1'
- **fail** `language/statements/variable/S12.2_A3.js` exit=b'1'
- **fail** `language/statements/variable/S12.2_A9.js` exit=b'1'
- **fail** `language/statements/variable/binding-resolution.js` exit=b'1'
- **fail** `language/statements/variable/cptn-value.js` exit=b'1'
- **fail** `language/statements/variable/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/variable/dstr/ary-ptrn-elem-id-static-init-await-valid.js` exit=b'1'
- **fail** `language/statements/variable/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/variable/dstr/obj-ptrn-elem-id-static-init-await-valid.js` exit=b'1'

### `statements/while` (6 residual)
- **fail** `language/statements/while/S12.6.2_A10.js` exit=b'1'
- **fail** `language/statements/while/S12.6.2_A5.js` exit=b'1'
- **fail** `language/statements/while/S12.6.2_A8.js` exit=b'1'
- **fail** `language/statements/while/cptn-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/while/cptn-iter.js` exit=b'1'
- **fail** `language/statements/while/tco-body.js` exit=b'1'

### `statements/with` (4 residual)
- **fail** `language/statements/with/get-binding-value-call-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/get-binding-value-idref-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/set-mutable-binding-idref-compound-assign-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/set-mutable-binding-idref-with-proxy-env.js` exit=b'1'

### `types/number` (2 residual)
- **fail** `language/types/number/8.5.1.js` exit=b'1'
- **fail** `language/types/number/S8.5_A13_T2.js` exit=b'1'

### `types/object` (1 residual)
- **fail** `language/types/object/S8.6.2_A8.js` exit=b'1'

### `types/reference` (5 residual)
- **fail** `language/types/reference/S8.7_A5_T2.js` exit=b'1'
- **fail** `language/types/reference/get-value-prop-base-primitive-realm.js` exit=b'1'
- **fail** `language/types/reference/get-value-prop-base-primitive.js` exit=b'1'
- **fail** `language/types/reference/put-value-prop-base-primitive-realm.js` exit=b'1'
- **fail** `language/types/reference/put-value-prop-base-primitive.js` exit=b'1'

### `types/undefined` (2 residual)
- **fail** `language/types/undefined/S8.1_A3_T1.js` exit=b'1'
- **fail** `language/types/undefined/S8.1_A3_T2.js` exit=b'1'

