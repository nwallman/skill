# PIT / pitest setup reference

When `detect_build.py` reports `has_pit: false`, add the plugin. Commit message: `chore: add pitest plugin for crap-buster`. Combine with the JaCoCo commit only if both are missing — otherwise keep them separate.

## Maven

Append inside `<build><plugins>` in `pom.xml`:

```xml
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.17.0</version>
    <dependencies>
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-junit5-plugin</artifactId>
            <version>1.2.1</version>
        </dependency>
    </dependencies>
    <configuration>
        <outputFormats>
            <outputFormat>HTML</outputFormat>
            <outputFormat>XML</outputFormat>
        </outputFormats>
        <timestampedReports>true</timestampedReports>
        <timeoutConstant>8000</timeoutConstant>
        <threads>4</threads>
    </configuration>
</plugin>
```

The `pitest-junit5-plugin` dependency is required for JUnit 5. If the project is on JUnit 4 only, omit it.

Run mutation testing with:
```bash
mvn org.pitest:pitest-maven:mutationCoverage
```

Reports land in `target/pit-reports/<timestamp>/`.

## Gradle (Kotlin DSL)

```kotlin
plugins {
    id("info.solidsoft.pitest") version "1.15.0"
}

pitest {
    junit5PluginVersion.set("1.2.1")
    outputFormats.set(listOf("HTML", "XML"))
    timestampedReports.set(true)
    threads.set(4)
    timeoutConstInMillis.set(8000)
}
```

## Gradle (Groovy DSL)

```groovy
plugins {
    id 'info.solidsoft.pitest' version '1.15.0'
}

pitest {
    junit5PluginVersion = '1.2.1'
    outputFormats = ['HTML', 'XML']
    timestampedReports = true
    threads = 4
    timeoutConstInMillis = 8000
}
```

Run with `./gradlew pitest`. Reports land in `build/reports/pitest/`.

## Threads and timeouts

PIT is CPU-bound. Setting `threads` to the number of physical cores is usually a good default. `timeoutConstant` is milliseconds added to each test's expected runtime budget — PIT kills tests that take longer, on the assumption a mutation caused an infinite loop. 8000ms is generous; if most tests are fast, 3000 is fine.

## Scope for crap-buster runs

### Full scope (default when `mutation.scope: full` in `.crap-buster.yml`)

Run with no `targetClasses` flag. PIT mutates everything under `src/main/java` that has at least one test. This is slow (minutes to hours) and honest.

### Changed-since scope (`mutation.scope: "changed-since:main"`)

Collect classes touched since the git ref:

```bash
CHANGED=$(git diff --name-only main -- 'src/main/java/**/*.java' \
  | sed 's|src/main/java/||; s|\.java$||; s|/|.|g' \
  | tr '\n' ',' | sed 's/,$//')
mvn org.pitest:pitest-maven:mutationCoverage -DtargetClasses="$CHANGED"
```

For Gradle:
```bash
./gradlew pitest -DtargetClasses="$CHANGED"
```

## Exclusions

Mutation testing is wasteful on some classes. Exclude at the plugin level:

Maven:
```xml
<configuration>
    <excludedClasses>
        <param>*.config.*</param>
        <param>*.dto.*</param>
        <param>*Application</param>
        <param>*Configuration</param>
        <param>*Properties</param>
    </excludedClasses>
    <excludedMethods>
        <param>toString</param>
        <param>hashCode</param>
        <param>equals</param>
    </excludedMethods>
</configuration>
```

Gradle Kotlin:
```kotlin
pitest {
    excludedClasses.set(listOf(
        "*.config.*", "*.dto.*",
        "*Application", "*Configuration", "*Properties"
    ))
    excludedMethods.set(listOf("toString", "hashCode", "equals"))
}
```

These exclusions apply only to the *mutation* step. Coverage still measures them (accurately, when Lombok's `@Generated` annotation is respected).

## Known pitfalls

- **OOM on large projects.** Set `-DjvmArgs=-Xmx4g` (Maven) or `pitest { jvmArgs.set(listOf("-Xmx4g")) }` (Gradle) if PIT crashes. Bigger projects may need 8g+.
- **Parallel tests + shared state.** If tests share mutable state (static caches, test DB state leaking between tests), PIT will produce flaky results. This is a sign your tests have a latent bug, not a sign that PIT is wrong. Fix the state isolation before interpreting PIT output.
- **Slow PITs from integration tests.** PIT runs every test against every mutation. `@SpringBootTest` tests with full context load become extremely slow under mutation. Exclude integration test classes from the mutation run: `excludedTestClasses` or `testClasses` scopes in plugin config.
- **Timestamps pile up.** `timestampedReports: true` keeps every run's results under `target/pit-reports/<timestamp>/`. Good for diffing across runs. Periodically `git clean` them or add to `.gitignore` if not already.
