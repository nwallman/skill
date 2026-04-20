# Generate a test for a specific method

You are being invoked inside crap-buster Phase 2 ("Cover"). Your task: write the missing tests for **one** method in the current project, such that after this step runs, the method's line coverage rises meaningfully (ideally to ≥ 0.85) without introducing tests that just exercise Mockito rather than the production code.

You are given:

- `fq_method`: fully-qualified method signature, e.g. `com.example.api.UserService.createUser(UserDto)`
- `file`: the absolute path to the Java source file
- `current_coverage`: fraction 0..1 from the latest JaCoCo run
- `complexity`: cyclomatic complexity
- `existing_test_class` (if any): path to the matching test class
- `surviving_mutants` (if any from a prior PIT run): list of mutations still alive; useful hints for what edge cases the existing tests miss

## Process

1. **Read the method.** Open the source file, find the method, and read it along with the class fields and constructor — you need to understand what collaborators it uses.
2. **Identify the test type.** Use `references/spring-test-types.md` for the decision. Roughly:
   - Controller method (annotated `@GetMapping`/`@PostMapping`/etc.): `@WebMvcTest` + `MockMvc` or `WebTestClient`.
   - Repository method (extends `JpaRepository` or custom): `@DataJpaTest` with `TestEntityManager` against H2 or Testcontainers.
   - Service or domain class: plain JUnit 5 + Mockito. No `@SpringBootTest` unless you genuinely need the container.
   - Configuration, mapper, DTO, exception: plain JUnit 5, no Spring.
3. **Enumerate the branches.** Cyclomatic complexity `N` means there are `N` independent paths through the method. Write one test per path, at minimum. Use mutation survivors (if provided) to find the branches the existing tests under-verify.
4. **Write the tests.**
   - Prefer AAA (Arrange / Act / Assert) structure with blank lines between the three sections.
   - Assertions should be behavioural, not incidental. Prefer `assertThat(result).isEqualTo(expected)` over `verify(mock).doThing()` when you can. Assert the *output*, not the *interaction*, unless the interaction *is* the output.
   - Use descriptive test names in the form `shouldX_whenY` or `givenX_whenY_thenZ`. Don't name tests after method names.
   - For parameterised cases, use `@ParameterizedTest` + `@CsvSource` / `@MethodSource`.
   - Mock only what you own that crosses an I/O boundary (repositories, external clients, clocks). Don't mock value objects.
5. **Run the test class.** Execute `mvn -Dtest=<TestClassName> test` (or the Gradle equivalent). If red, fix. If the method is genuinely untestable without invasive changes, stop and report — don't silently widen scope.
6. **Run the full suite.** Only commit if the full suite is green.

## Commit message

```
test: cover <SimpleClassName>

- <method signature>: coverage <before> → <after>, CRAP <before> → <after>
- <method signature>: coverage <before> → <after>, CRAP <before> → <after>
```

## Things to avoid

- **Vacuous tests.** A test that calls a method and only asserts it "doesn't throw" is worse than no test — it inflates coverage without verifying anything. If the method genuinely has no observable effect, skip it and note that in the phase report.
- **Over-mocking.** If your test is 30 lines of `when(...).thenReturn(...)` and 2 lines of assertion, your test is testing your mocks.
- **Replicating Spring plumbing.** For controller tests, don't hand-build the `ResponseEntity` expected value to match how the controller constructs it — that just restates the production code. Assert the observable HTTP outputs: status, body JSON fields, headers.
- **Chasing 100%.** The target is `coverage.line_target`, not 1.0. Don't write tests for unreachable branches (`default:` clauses covering exhaustive enums, impossible `else` blocks on already-checked conditions). Annotate them `@SuppressWarnings` or leave them alone.
- **Assertions on private state.** Use `org.assertj.core.api.Assertions` against the public output or side effect. Reflection-based private-field assertions are a bad smell.

## When to stop and hand back

- If the method is `@Deprecated` or has a clear "don't test me" signal (e.g. `// TODO: remove in v3`), add it to `.crap-buster.yml` `exclude` with a one-line justification and move on.
- If the method requires a running external system that isn't mocked or containerized (e.g. direct `new RestTemplate().exchange(...)` to a third-party API), quarantine: add a TODO comment, log the class in the report, and move on.
- If covering the method would require refactoring the production code to make it testable (method is `final static` with hidden global state, etc.), note this for Phase 4 ("Decompose") and move on.
