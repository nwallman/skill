# Spring Boot test types — when to use which

Most tests generated in crap-buster Phase 2 should be **plain JUnit 5 + Mockito**, not Spring slices. Reach for Spring test annotations only when you actually need the container. The rules below help you pick.

## Plain JUnit 5 + Mockito

Use for: services, domain classes, mappers, validators, helpers, anything that doesn't need the Spring context. This should be the default.

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock UserRepository repo;
    @Mock Clock clock;
    @InjectMocks UserService service;

    @Test
    void shouldReturnUser_whenIdExists() {
        User expected = new User(1L, "alice");
        when(repo.findById(1L)).thenReturn(Optional.of(expected));

        User actual = service.getUser(1L);

        assertThat(actual).isEqualTo(expected);
    }
}
```

No Spring context means: fast (milliseconds), no classpath surprises, no proxy magic.

## `@WebMvcTest` — for controllers

Use for: `@RestController` / `@Controller` methods. Loads the MVC slice only — controller, converters, filters, `ControllerAdvice` — no services, no repositories.

```java
@WebMvcTest(UserController.class)
class UserControllerTest {
    @Autowired MockMvc mvc;
    @MockBean UserService service;

    @Test
    void shouldReturn404_whenUserMissing() throws Exception {
        when(service.getUser(42L)).thenThrow(new NotFoundException());

        mvc.perform(get("/api/users/42"))
            .andExpect(status().isNotFound());
    }
}
```

Assert on HTTP status, headers, and response body JSON — not on the controller's internal `ResponseEntity`. Use `jsonPath("$.id").value(42)` for field assertions.

For reactive stacks (WebFlux), use `@WebFluxTest` + `WebTestClient`.

## `@DataJpaTest` — for repositories

Use for: `JpaRepository` subinterfaces with custom queries, `@Query` methods, or native SQL. Loads the JPA slice only — entities, repositories, `EntityManager` — no MVC, no services.

```java
@DataJpaTest
class UserRepositoryTest {
    @Autowired UserRepository repo;
    @Autowired TestEntityManager em;

    @Test
    void shouldFindByEmail_whenEmailExists() {
        User alice = em.persistAndFlush(new User(null, "alice", "alice@x.com"));

        Optional<User> found = repo.findByEmail("alice@x.com");

        assertThat(found).contains(alice);
    }
}
```

By default uses H2. For repositories with PostgreSQL-specific SQL, wrap with Testcontainers:

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = Replace.NONE)
@Testcontainers
class UserRepositoryTest {
    @Container
    static PostgreSQLContainer<?> db = new PostgreSQLContainer<>("postgres:16");
    // ...
}
```

Don't write `@DataJpaTest` just to exercise trivial `findById` — those are covered by JPA itself. Only test custom queries.

## `@SpringBootTest` — sparingly

Use for: integration smoke tests that need the full context. Slow (5-10s per test), flaky by default, and a poor tool for driving CRAP down. In Phase 2, write at most one or two `@SpringBootTest` classes per API feature, covering happy-path end-to-end.

```java
@SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
class UserApiIntegrationTest {
    @Autowired MockMvc mvc;
    @Autowired UserRepository repo;

    @Test
    void shouldCreateAndRetrieveUser() throws Exception {
        MvcResult created = mvc.perform(post("/api/users")
                .contentType(APPLICATION_JSON)
                .content("{\"email\":\"alice@x.com\"}"))
            .andExpect(status().isCreated())
            .andReturn();

        Long id = JsonPath.read(created.getResponse().getContentAsString(), "$.id");

        mvc.perform(get("/api/users/" + id))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.email").value("alice@x.com"));
    }
}
```

For API-level assertions, prefer `MockMvc` over `TestRestTemplate` — faster and doesn't need `RANDOM_PORT`.

## Decision tree

```
What are you testing?
│
├── A controller method? → @WebMvcTest + MockMvc
├── A repository method (custom query)? → @DataJpaTest + TestEntityManager
├── A scheduled job / listener / integration seam? → @SpringBootTest (sparingly)
├── Anything else (service, domain, mapper, etc.) → plain JUnit 5 + Mockito
```

## Don'ts

- **Don't use `@SpringBootTest` as a default.** Every test that can be plain JUnit should be.
- **Don't mock the thing under test.** If you're mocking the class whose method you're testing, you're not testing that class.
- **Don't `@Autowired` the concrete class when `@MockBean` would decouple.** `@MockBean` provides the Spring-visible stub the controller uses; `@Autowired` would pull in the real service and any of its dependencies.
- **Don't assert on ResponseEntity internals.** Assert HTTP status/body. The controller's choice of `ResponseEntity.ok(x)` vs. `new ResponseEntity<>(x, HttpStatus.OK)` is an implementation detail; tests that pin it are brittle.
- **Don't test Spring itself.** `@PathVariable` parses path variables, `@Valid` triggers validation — these are framework guarantees, not your logic. Test your logic.
