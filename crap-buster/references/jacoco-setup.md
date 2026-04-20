# JaCoCo setup reference

When `detect_build.py` reports `has_jacoco: false`, add the plugin. Keep it to one commit (`chore: add jacoco plugin for crap-buster`) and don't touch other parts of the build file in the same commit.

## Maven

Append inside `<build><plugins>` in `pom.xml`:

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution>
            <id>prepare-agent</id>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

After this, `mvn test` automatically produces `target/site/jacoco/jacoco.xml` and `jacoco.html`. No separate target required.

## Gradle (Kotlin DSL)

In `build.gradle.kts`:

```kotlin
plugins {
    jacoco
}

tasks.test {
    finalizedBy(tasks.jacocoTestReport)
}

tasks.jacocoTestReport {
    dependsOn(tasks.test)
    reports {
        xml.required.set(true)
        html.required.set(true)
    }
}
```

Report will land at `build/reports/jacoco/test/jacocoTestReport.xml`.

## Gradle (Groovy DSL)

In `build.gradle`:

```groovy
plugins {
    id 'jacoco'
}

test {
    finalizedBy jacocoTestReport
}

jacocoTestReport {
    dependsOn test
    reports {
        xml.required = true
        html.required = true
    }
}
```

## Lombok integration

If `detect_build.py` reports `has_lombok: true` and `lombok_generated_annotation_enabled: no` or `no-config-file`, write or update `lombok.config` at the project root:

```
lombok.addLombokGeneratedAnnotation = true
```

That single line makes Lombok emit `@lombok.Generated` on all synthesized methods. JaCoCo automatically excludes any method tagged `@Generated`, so getters/setters/equals/hashCode/toString/builders don't appear in coverage reports — and crap-buster won't waste Phase 2 time trying to test them. Commit `lombok.config` together with the JaCoCo plugin addition in the same `chore:` commit.

If `lombok.config` already exists with that line set to `true`, no action needed.

## Exclusions in the JaCoCo config itself

JaCoCo's plugin config supports `<excludes>` / `excludes =`. Don't add package-level exclusions at the plugin level — use `.crap-buster.yml` `exclude` instead, so all exclusion policy lives in one place. The only exception is tool-agnostic boilerplate you'd want out of *any* coverage report:

Maven:
```xml
<configuration>
    <excludes>
        <exclude>**/generated/**</exclude>
        <exclude>**/*Application.class</exclude>
    </excludes>
</configuration>
```

Gradle Kotlin:
```kotlin
tasks.jacocoTestReport {
    classDirectories.setFrom(
        files(classDirectories.files.map {
            fileTree(it) {
                exclude("**/generated/**", "**/*Application.class")
            }
        })
    )
}
```

These two are safe defaults. Anything more project-specific belongs in `.crap-buster.yml`.

## Verifying it works

After adding the plugin, run:

```bash
mvn test                          # Maven
./gradlew test jacocoTestReport   # Gradle
```

Then confirm `jacoco.xml` exists. Run `scripts/crap.py --input <path> --out /tmp/test.md` as a smoke test before starting Phase 1 in earnest.
