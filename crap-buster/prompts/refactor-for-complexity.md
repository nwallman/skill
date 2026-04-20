# Refactor a method for lower complexity

You are being invoked inside crap-buster Phase 4 ("Decompose"). Your task: refactor **one** method whose CRAP score is still above the target because its cyclomatic complexity is high, and do it in a way that provably preserves behaviour.

You are given:

- `fq_method`: fully-qualified method signature
- `file`: absolute path to the Java source file
- `complexity_before`: current cyclomatic complexity
- `coverage`: line coverage (should be ≥ 0.9 by the time Phase 4 runs on this method)
- `class_mutation_score_before`: class-level mutation score from the latest PIT run
- `config.mutation.regression_tolerance`: maximum allowed mutation-score drop

## The non-negotiable gates

After your refactor, two things must still be true:

1. **The full test suite is green.** Run `mvn test` (or `./gradlew test`). If red, revert (`git reset --hard HEAD`) and stop.
2. **Mutation score on this class must not drop by more than `regression_tolerance` points.** Run PIT scoped to this class. Compare to `class_mutation_score_before`. If the drop exceeds tolerance, revert and stop.

If either gate fails, the refactor did not preserve behaviour (or the tests don't actually verify what you thought they did). *Don't try to fix it by weakening tests.* Revert, log the method as "refactor-skipped" in the phase report, and let a human look at it later.

## The refactors you can apply

Prefer earlier items on this list — they're the safest.

### 1. Extract Method

Find a block of code with a clear single responsibility (often marked by a comment, or a blank-line-separated paragraph) and extract it into a new private method. Choose a name that explains *what it does*, not *how it does it*.

**Before:**
```java
public BigDecimal calculateTotal(Order order) {
    BigDecimal subtotal = BigDecimal.ZERO;
    for (Item i : order.getItems()) {
        subtotal = subtotal.add(i.getPrice().multiply(BigDecimal.valueOf(i.getQuantity())));
    }
    BigDecimal tax = subtotal.multiply(TAX_RATE);
    BigDecimal discount = BigDecimal.ZERO;
    if (order.getCustomer().getTier() == Tier.PREMIUM) {
        discount = subtotal.multiply(PREMIUM_DISCOUNT);
    } else if (order.getCustomer().getTier() == Tier.GOLD) {
        discount = subtotal.multiply(GOLD_DISCOUNT);
    }
    return subtotal.add(tax).subtract(discount);
}
```

**After:**
```java
public BigDecimal calculateTotal(Order order) {
    BigDecimal subtotal = subtotalOf(order.getItems());
    BigDecimal tax = subtotal.multiply(TAX_RATE);
    BigDecimal discount = discountFor(order.getCustomer(), subtotal);
    return subtotal.add(tax).subtract(discount);
}
```

Each extracted method gets tested indirectly via the same callers, but its own complexity drops to 1 or 2.

### 2. Guard Clauses (Replace Nested Conditionals)

Nested `if`s with short "unhappy path" bodies should be flattened into early returns.

**Before:**
```java
public User authenticate(String token) {
    if (token != null) {
        if (!token.isBlank()) {
            if (tokenStore.isValid(token)) {
                return userRepo.findByToken(token);
            }
        }
    }
    throw new UnauthorizedException();
}
```

**After:**
```java
public User authenticate(String token) {
    if (token == null || token.isBlank()) throw new UnauthorizedException();
    if (!tokenStore.isValid(token)) throw new UnauthorizedException();
    return userRepo.findByToken(token);
}
```

### 3. Replace Conditional with Polymorphism

When a method's complexity comes from a `switch`/`if-else` chain on a type tag, replace it with a strategy map. This is heavier — do it only when the same type tag is switched on in multiple places.

Not every `switch` is a candidate. A single 3-case switch inside a method used once doesn't need abstracting.

### 4. Extract Class

When a method operates on a cohesive subset of its class's fields (and you'd want to test that subset independently), extract a new class. This is the heaviest refactor on the list — use only when the resulting classes will each be individually useful.

### 5. Replace Magic Numbers / Strings with Named Constants

Doesn't lower complexity but makes subsequent refactors safer and reads better. Often a good first step alongside extract-method.

## Refactors you should *not* apply

- **Don't change method signatures unless you also update all callers.** Breaking the public API of a class is out of scope for this phase.
- **Don't change behaviour for edge cases** (null inputs, empty collections, bounds) even if the current behaviour looks wrong. If the current behaviour is a bug, that's a separate PR.
- **Don't inline Spring annotations** or change `@Transactional` boundaries. Transaction semantics are load-bearing; refactoring across them is risky.
- **Don't refactor `@Entity` classes for complexity.** JPA's proxy/lifecycle expectations make aggressive refactoring here dangerous.

## Process

1. **Check the contract.** Before editing, skim the existing tests for this method. The tests define the observable contract. Your refactor must preserve every assertion.
2. **Snapshot the mutation score.** You need `class_mutation_score_before` — get it from the JSON output of the last PIT run, or re-run PIT scoped to this class.
3. **Apply one refactor at a time.** Don't stack Extract Method + Extract Class + Guard Clause in a single commit. One refactor, one commit.
4. **Run tests.** `mvn -Dtest=<TestClass> test` first for a fast check, then `mvn test` for the full suite.
5. **Run PIT scoped to this class.** Compare the new mutation score against the snapshot. Apply the tolerance gate.
6. **Recompute CRAP.** Run `mvn jacoco:report` and then `crap.py`. If the method's CRAP didn't drop, you refactored shape but not complexity — undo and try a different refactor.
7. **Commit** if all gates pass.

## Commit message

```
refactor: decompose <SimpleClassName>.<methodName> (CRAP <before> → <after>)

- Extract method `<newMethodName>` covering <short description>
- Complexity <before> → <after>
- Mutation score on class: <before>% → <after>%
```

## When to give up on a method

If two consecutive refactor attempts on the same method:

- fail a gate, or
- don't reduce CRAP, or
- require test changes to stay green

…stop. Revert. Add the method to `.crap-buster.yml` under `exclude.methods` with a one-line comment explaining why. Some methods are irreducibly complex — parsers, state machines, exhaustive enum dispatchers — and mechanical decomposition makes them worse. Recognise and move on.
