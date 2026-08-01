# Knockout list — M128e7bb (language residuals)

Tip `6dbf7744` · language residual **2,956** (fail+error+timeout) · G2 gap **1,775**

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
| `expressions/async-arrow-function` | 1 | 59/60 | 98.3% |
| `statements/continue` | 1 | 23/24 | 95.8% |
| `statements/break` | 1 | 19/20 | 95.0% |
| `types/object` | 1 | 18/19 | 94.7% |
| `expressions/logical-and` | 1 | 17/18 | 94.4% |
| `expressions/logical-or` | 1 | 17/18 | 94.4% |
| `block-scope/leave` | 1 | 14/15 | 93.3% |
| `expressions/comma` | 1 | 5/6 | 83.3% |
| `statements/async-function` | 2 | 72/74 | 97.3% |
| `statements/do-while` | 2 | 34/36 | 94.4% |
| `expressions/coalesce` | 2 | 22/24 | 91.7% |
| `expressions/conditional` | 2 | 20/22 | 90.9% |
| `types/number` | 2 | 19/21 | 90.5% |
| `destructuring/binding` | 2 | 17/19 | 89.5% |
| `statements/return` | 2 | 14/16 | 87.5% |
| `block-scope/shadowing` | 2 | 13/15 | 86.7% |
| `computed-property-names/object` | 2 | 10/12 | 83.3% |
| `types/undefined` | 2 | 6/8 | 75.0% |
| `literals/string` | 3 | 70/73 | 95.9% |
| `expressions/in` | 3 | 33/36 | 91.7% |
| `statements/block` | 3 | 18/21 | 85.7% |
| `expressions/dynamic-import` | 4 | 937/941 | 99.6% |
| `statements/async-generator` | 4 | 297/301 | 98.7% |
| `arguments-object/mapped` | 4 | 39/43 | 90.7% |
| `expressions/await` | 4 | 18/22 | 81.8% |
| `expressions/new.target` | 4 | 10/14 | 71.4% |
| `expressions/optional-chaining` | 5 | 33/38 | 86.8% |
| `types/reference` | 5 | 24/29 | 82.8% |
| `statements/while` | 6 | 32/38 | 84.2% |
| `expressions/import.meta` | 6 | 16/22 | 72.7% |
| `expressions/async-generator` | 7 | 616/623 | 98.9% |
| `statements/with` | 7 | 174/181 | 96.1% |
| `statements/labeled` | 7 | 17/24 | 70.8% |
| `expressions/array` | 8 | 44/52 | 84.6% |
| `expressions/logical-assignment` | 9 | 69/78 | 88.5% |
| `statements/if` | 10 | 59/69 | 85.5% |
| `eval-code/indirect` | 10 | 51/61 | 83.6% |
| `module-code/namespace` | 10 | 28/38 | 73.7% |
| `statements/const` | 11 | 125/136 | 91.9% |
| `statements/generators` | 12 | 254/266 | 95.5% |
| `statements/await-using` | 13 | 81/94 | 86.2% |
| `expressions/assignment` | 14 | 471/485 | 97.1% |
| `expressions/template-literal` | 14 | 43/57 | 75.4% |
| `statements/let` | 16 | 129/145 | 89.0% |
| `statements/switch` | 17 | 94/111 | 84.7% |
| `expressions/generators` | 18 | 272/290 | 93.8% |
| `statements/variable` | 18 | 160/178 | 89.9% |
| `expressions/call` | 19 | 73/92 | 79.3% |
| `expressions/function` | 23 | 241/264 | 91.3% |
| `expressions/compound-assignment` | 24 | 430/454 | 94.7% |
| `eval-code/direct` | 24 | 262/286 | 91.6% |
| `statements/for-in` | 24 | 91/115 | 79.1% |
| `expressions/arrow-function` | 25 | 318/343 | 92.7% |

## P1 — medium residual

| Category | Residual | Pass/Total | Pass% |
|----------|---------:|-----------:|------:|
| `statements/function` | 29 | 422/451 | 93.6% |
| `statements/for` | 29 | 356/385 | 92.5% |
| `module-code/top-level-await` | 29 | 222/251 | 88.4% |
| `statements/try` | 30 | 171/201 | 85.1% |
| `expressions/super` | 30 | 64/94 | 68.1% |
| `literals/regexp` | 31 | 207/238 | 87.0% |
| `expressions/yield` | 36 | 27/63 | 42.9% |
| `statements/using` | 40 | 38/78 | 48.7% |
| `expressions/object` | 45 | 1116/1161 | 96.1% |
| `import/import-defer` | 45 | 56/101 | 55.4% |

## P2 — bulk residual

| Category | Residual | Pass/Total | Pass% |
|----------|---------:|-----------:|------:|
| `statements/for-of` | 90 | 661/751 | 88.0% |
| `expressions/class` | 638 | 3421/4059 | 84.3% |
| `statements/class` | 1167 | 3200/4367 | 73.3% |

## P0 failing paths (sample ≤15 per category)

### `arguments-object/mapped` (4 residual)
- **fail** `language/arguments-object/mapped/enumerable-configurable-accessor-descriptor.js` exit=b'1'
- **fail** `language/arguments-object/mapped/mapped-arguments-nonwritable-nonconfigurable-2.js` exit=b'1'
- **fail** `language/arguments-object/mapped/mapped-arguments-nonwritable-nonconfigurable-4.js` exit=b'1'
- **fail** `language/arguments-object/mapped/nonconfigurable-descriptors-define-failure.js` exit=b'1'

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

### `expressions/array` (8 residual)
- **fail** `language/expressions/array/spread-err-mult-err-itr-get-call.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-mult-err-itr-get-get.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-mult-err-itr-step.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-mult-err-itr-value.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-sngl-err-itr-get-call.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-sngl-err-itr-get-get.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-sngl-err-itr-step.js` exit=b'1'
- **fail** `language/expressions/array/spread-err-sngl-err-itr-value.js` exit=b'1'

### `expressions/arrow-function` (25 residual)
- **fail** `language/expressions/arrow-function/ArrowFunction_restricted-properties.js` exit=b'1'
- **fail** `language/expressions/arrow-function/cannot-override-this-with-thisArg.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-obj-ptrn-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/dflt-obj-ptrn-prop-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/obj-ptrn-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/dstr/obj-ptrn-prop-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/arrow-function/lexical-new.target-closure-returned.js` exit=b'1'
- **fail** `language/expressions/arrow-function/lexical-new.target.js` exit=b'1'
- … +10 more

### `expressions/assignment` (14 residual)
- **fail** `language/expressions/assignment/11.13.1-4-6-s.js` exit=b'1'
- **fail** `language/expressions/assignment/destructuring/target-assign-throws-iterator-return-is-not-callable.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-elem-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-elem-put-prop-ref-user-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-elem-trlg-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-elision-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-empty-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-rest-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-rest-put-prop-ref-user-err-iter-close-skip.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/array-rest-put-prop-ref-user-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/obj-prop-put-prop-ref-user-err.js` exit=b'1'
- **fail** `language/expressions/assignment/dstr/obj-rest-getter-abrupt-get-error.js` exit=b'1'
- **fail** `language/expressions/assignment/fn-name-lhs-member.js` exit=b'1'
- **fail** `language/expressions/assignment/target-super-computed-reference-null.js` exit=b'1'

### `expressions/async-arrow-function` (1 residual)
- **timeout** `language/expressions/async-arrow-function/prototype.js` timeout

### `expressions/async-generator` (7 residual)
- **fail** `language/expressions/async-generator/default-proto.js` exit=b'1'
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

### `expressions/call` (19 residual)
- **fail** `language/expressions/call/eval-realm-indirect.js` exit=b'1'
- **fail** `language/expressions/call/eval-spread-empty-leading.js` exit=b'1'
- **fail** `language/expressions/call/eval-spread-empty-trailing.js` exit=b'1'
- **fail** `language/expressions/call/eval-spread.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-mult-err-itr-get-call.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-mult-err-itr-get-get.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-mult-err-itr-step.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-mult-err-itr-value.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-sngl-err-itr-get-call.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-sngl-err-itr-get-get.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-sngl-err-itr-step.js` exit=b'1'
- **fail** `language/expressions/call/spread-err-sngl-err-itr-value.js` exit=b'1'
- **fail** `language/expressions/call/tco-call-args.js` exit=b'1'
- **fail** `language/expressions/call/tco-member-args.js` exit=b'1'
- **fail** `language/expressions/call/tco-non-eval-function-dynamic.js` exit=b'1'
- … +4 more

### `expressions/coalesce` (2 residual)
- **fail** `language/expressions/coalesce/tco-pos-null.js` exit=b'1'
- **fail** `language/expressions/coalesce/tco-pos-undefined.js` exit=b'1'

### `expressions/comma` (1 residual)
- **fail** `language/expressions/comma/tco-final.js` exit=b'1'

### `expressions/compound-assignment` (24 residual)
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.10_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.11_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.1_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.2_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.3_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.4_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.5_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.6_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.7_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.8_T3.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/S11.13.2_A7.9_T3.js` exit=b'1'
- **error** `language/expressions/compound-assignment/left-hand-side-private-reference-accessor-property-bitand.js` harness_eof
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-add.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-bitand.js` exit=b'1'
- **fail** `language/expressions/compound-assignment/left-hand-side-private-reference-data-property-bitor.js` exit=b'1'
- … +9 more

### `expressions/conditional` (2 residual)
- **fail** `language/expressions/conditional/tco-cond.js` exit=b'1'
- **fail** `language/expressions/conditional/tco-pos.js` exit=b'1'

### `expressions/delete` (1 residual)
- **error** `language/expressions/delete/super-property.js` harness_eof

### `expressions/dynamic-import` (4 residual)
- **fail** `language/expressions/dynamic-import/assign-expr-get-value-abrupt-throws.js` exit=b'1'
- **timeout** `language/expressions/dynamic-import/await-import-evaluation.js` timeout
- **fail** `language/expressions/dynamic-import/import-attributes/2nd-param-in.js` exit=b'1'
- **fail** `language/expressions/dynamic-import/syntax/valid/callexpression-templateliteral.js` exit=b'1'

### `expressions/function` (23 residual)
- **fail** `language/expressions/function/dstr/ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-obj-ptrn-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/dflt-obj-ptrn-prop-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/obj-ptrn-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/function/dstr/obj-ptrn-prop-id-get-value-err.js` exit=b'1'
- **fail** `language/expressions/function/eval-var-scope-syntax-err.js` exit=b'1'
- **fail** `language/expressions/function/named-strict-error-reassign-fn-name-in-body-in-arrow.js` exit=b'1'
- **fail** `language/expressions/function/named-strict-error-reassign-fn-name-in-body-in-eval.js` exit=b'1'
- **fail** `language/expressions/function/scope-name-var-close.js` exit=b'1'
- **fail** `language/expressions/function/scope-name-var-open-non-strict.js` exit=b'1'
- … +8 more

### `expressions/generators` (18 residual)
- **fail** `language/expressions/generators/default-proto.js` exit=b'1'
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
- **fail** `language/expressions/generators/scope-param-rest-elem-var-open.js` exit=b'1'
- … +3 more

### `expressions/import.meta` (6 residual)
- **fail** `language/expressions/import.meta/distinct-for-each-module.js` exit=b'1'
- **fail** `language/expressions/import.meta/not-accessible-from-direct-eval.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-async-function-params-or-body.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-async-generator-params-or-body.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-function-params-or-body.js` exit=b'1'
- **fail** `language/expressions/import.meta/syntax/goal-generator-params-or-body.js` exit=b'1'

### `expressions/in` (3 residual)
- **error** `language/expressions/in/private-field-presence-method.js` harness_eof
- **error** `language/expressions/in/private-field-rhs-await-absent.js` harness_eof
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

### `expressions/new.target` (4 residual)
- **fail** `language/expressions/new.target/value-via-reflect-apply.js` exit=b'1'
- **fail** `language/expressions/new.target/value-via-reflect-construct.js` exit=b'1'
- **error** `language/expressions/new.target/value-via-super-call.js` harness_eof
- **error** `language/expressions/new.target/value-via-super-property.js` harness_eof

### `expressions/optional-chaining` (5 residual)
- **fail** `language/expressions/optional-chaining/call-expression.js` exit=b'1'
- **fail** `language/expressions/optional-chaining/new-target-optional-call.js` exit=b'1'
- **fail** `language/expressions/optional-chaining/optional-chain-prod-arguments.js` exit=b'1'
- **fail** `language/expressions/optional-chaining/optional-chain-prod-expression.js` exit=b'1'
- **fail** `language/expressions/optional-chaining/super-property-optional-call.js` exit=b'1'

### `expressions/template-literal` (14 residual)
- **fail** `language/expressions/template-literal/evaluation-order.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-character-escape-sequence.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-hex-escape-sequence.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-line-continuation.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-line-terminator-sequence.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-no-substitution.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-null-character-escape-sequence.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-template-character.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-template-characters.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-template-head.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-template-middle.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-template-tail.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-utf16-escape-sequence.js` exit=b'1'
- **fail** `language/expressions/template-literal/tv-zwnbsp.js` exit=b'1'

### `literals/string` (3 residual)
- **error** `language/literals/string/S7.8.4_A4.2_T1.js` harness_eof
- **fail** `language/literals/string/S7.8.4_A6.1_T2.js` exit=b'1'
- **error** `language/literals/string/S7.8.4_A7.3_T1.js` harness_eof

### `module-code/namespace` (10 residual)
- **fail** `language/module-code/namespace/internals/delete-exported-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/enumerate-binding-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/get-own-property-str-found-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/get-str-found-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/object-hasOwnProperty-binding-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/object-keys-binding-uninit.js` exit=b'1'
- **fail** `language/module-code/namespace/internals/object-propertyIsEnumerable-binding-uninit.js` exit=b'1'
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

### `statements/const` (11 residual)
- **fail** `language/statements/const/cptn-value.js` exit=b'1'
- **fail** `language/statements/const/dstr/ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/statements/const/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/const/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/const/dstr/obj-ptrn-id-get-value-err.js` exit=b'1'
- **fail** `language/statements/const/dstr/obj-ptrn-prop-id-get-value-err.js` exit=b'1'
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

### `statements/let` (16 residual)
- **fail** `language/statements/let/cptn-value.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-init-iter-close.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/let/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/let/dstr/obj-ptrn-id-get-value-err.js` exit=b'1'
- **fail** `language/statements/let/dstr/obj-ptrn-prop-id-get-value-err.js` exit=b'1'
- **fail** `language/statements/let/function-local-closure-get-before-initialization.js` exit=b'1'
- **fail** `language/statements/let/function-local-closure-set-before-initialization.js` exit=b'1'
- **fail** `language/statements/let/global-closure-set-before-initialization.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-closure-inside-condition.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-closure-inside-initialization.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-closure-inside-next-expression.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-iteration-variable-is-freshly-allocated-for-each-iteration-multi-let-binding.js` exit=b'1'
- **fail** `language/statements/let/syntax/let-outer-inner-let-bindings.js` exit=b'1'
- … +1 more

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

### `statements/variable` (18 residual)
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
- **fail** `language/statements/variable/dstr/ary-init-iter-get-err.js` exit=b'1'
- **fail** `language/statements/variable/dstr/ary-ptrn-elem-id-iter-val-err.js` exit=b'1'
- **fail** `language/statements/variable/dstr/ary-ptrn-elem-id-static-init-await-valid.js` exit=b'1'
- **fail** `language/statements/variable/dstr/ary-ptrn-rest-id-iter-val-err.js` exit=b'1'
- … +3 more

### `statements/while` (6 residual)
- **fail** `language/statements/while/S12.6.2_A10.js` exit=b'1'
- **fail** `language/statements/while/S12.6.2_A5.js` exit=b'1'
- **fail** `language/statements/while/S12.6.2_A8.js` exit=b'1'
- **fail** `language/statements/while/cptn-abrupt-empty.js` exit=b'1'
- **fail** `language/statements/while/cptn-iter.js` exit=b'1'
- **fail** `language/statements/while/tco-body.js` exit=b'1'

### `statements/with` (7 residual)
- **fail** `language/statements/with/get-binding-value-call-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/get-binding-value-idref-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/has-property-err.js` exit=b'1'
- **fail** `language/statements/with/set-mutable-binding-idref-compound-assign-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/set-mutable-binding-idref-with-proxy-env.js` exit=b'1'
- **fail** `language/statements/with/unscopables-get-err.js` exit=b'1'
- **fail** `language/statements/with/unscopables-prop-get-err.js` exit=b'1'

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

