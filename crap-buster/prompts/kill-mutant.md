# Kill a surviving mutant

You are being invoked inside crap-buster Phase 3 ("Mutate"). Your task: given a mutant that the current test suite failed to kill, write a test that *would* fail if the mutation were applied. This closes a real verification gap — not just a coverage gap.

You are given:

- `klass`: fully-qualified class, e.g. `com.example.api.UserService`
- `method`: method name + descriptor
- `line`: line number in the source file
- `mutator`: the short mutator name, e.g. `NegateConditionals`, `ConditionalsBoundary`, `MathMutator`, `VoidMethodCall`, `IncrementsMutator`, `ReturnVals`, `EmptyReturns`, `NullReturns`, `PrimitiveReturns`, `InlineConstant`
- `description`: PIT's description, e.g. "negated conditional"
- `source_file`: absolute path

## How to think about mutants

A mutant is a deliberate bug. PIT patched the bytecode at `line` using `mutator`, reran your tests, and they still passed — meaning your tests don't distinguish "code works" from "code has this specific bug". Your job is to produce an input for which the mutated version returns a different observable output from the original.

### Common mutator → test strategy

- **NegateConditionals** (`if (x > 5)` becomes `if (!(x > 5))`): you need two inputs that straddle the boundary. One on each side, asserting different outputs.
- **ConditionalsBoundary** (`>` becomes `>=`, `<` becomes `<=`): test exactly *at* the boundary. If the production code says `x > 5`, the input `x == 5` must produce the "false branch" result. This is the mutation most commonly missed — easy to write a test for `x == 10` that passes both ways.
- **MathMutator** (`a + b` becomes `a - b`, etc.): test with values that make the operators distinguishable. `2 + 2 == 4` and `2 - 2 == 0` differ. `2 * 2 == 4` and `2 + 2 == 4` don't.
- **IncrementsMutator** (`i++` becomes `i--`): loop iteration counts, accumulator values — assert on them directly.
- **VoidMethodCall / NonVoidMethodCall** (removes a method call): if the removed call has an observable side effect (log, event publish, metric increment), assert on that side effect. If it's a pure function whose result is discarded, the call is dead code — remove it from production or exclude the class from mutation testing.
- **EmptyReturns / NullReturns / PrimitiveReturns**: your test must assert the actual returned value, not just that a value was returned.
- **InlineConstant** (`return 42` becomes `return 43` or `return 0`): assert on the actual numeric value.

### What makes a kill test different from a coverage test

A coverage test proves the line *ran*. A kill test proves the line *matters*. Kill tests are almost always *value-asserting* and *boundary-hitting*.

Example gap a lot of test suites have:

```java
if (age >= 18) return "adult";
return "minor";
```

A coverage test that passes `age = 25` covers both lines and both branches. But mutating `>=` to `>` survives unless you test `age = 18` specifically.

## Process

1. **Read the line.** Open the source file at `line` and look at what the mutator would have changed. If PIT's description isn't enough, cross-reference the mutator name with the list above.
2. **Find the existing test class** for this class. Look for a test that already exercises `method` and figure out why it doesn't catch the mutation.
3. **Write a minimal kill test.** Ideally: one new `@Test` method, one input, one output assertion. Name it after the specific case: `shouldReturnMinor_whenAgeIs17`, `shouldIncludeLoggingSideEffect_whenCallSucceeds`, etc.
4. **Verify the test passes against the unmutated code** (`mvn -Dtest=<TestClass> test`).
5. **Verify the mutant is now killed.** Run PIT scoped to just this class: `mvn org.pitest:pitest-maven:mutationCoverage -DtargetClasses=<klass>`. The mutation score on the class should go up and the specific mutant should no longer be in the survivors list.
6. **If the mutant is still alive** after your new test, your test passes *both* mutated and unmutated versions. Re-read the mutator's semantics and try again with a more targeted input. Common reasons:
   - You asserted on the wrong output (tested a side channel, not the mutated path's return).
   - Your input doesn't actually hit the mutated line.
   - The production code has dead branches that dominate the mutation (the mutant is equivalent to the original — rare but real; exclude that specific mutator for that line).

## Commit message

```
test(mutation): kill <N> surviving mutants in <SimpleClassName>

- L<line> <mutator>: <short description of the kill-test approach>
- L<line> <mutator>: ...
```

## When to skip

- **Equivalent mutants.** Some mutations produce semantically-identical code (e.g. negating a conditional on a side-effect-free helper that also doesn't affect return value). These can't be killed. Add them to `.crap-buster.yml` under `mutation.excluded_mutations` with the class, line, and mutator.
- **Logging-only mutations.** `VoidMethodCall` on `log.debug(...)` or similar is usually not worth killing unless your service contract promises a specific log emission. Exclude at the class level or globally.
- **Unreachable mutations.** If the mutated branch is unreachable by construction (e.g. early return makes a later `null` check impossible to hit), ignore — the mutation is harmless.
