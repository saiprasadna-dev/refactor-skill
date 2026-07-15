# Upgrade Guides

Version-specific guidance for common Java modernization paths. Always
cross-check against the actual versions found during assessment — never
assume versions.

## Supported upgrade paths

- Java 8/11/17 → Java 21 is acceptable
- Spring Boot 2.x → 3.x is acceptable
- javax → jakarta migration must be handled carefully
- Hibernate, JUnit, Mockito, Jackson, Maven plugins, and build tooling must
  be aligned to versions compatible with the chosen Java/Spring targets

## Java version upgrades (8/11/17 → 21)

Checklist:

- Update `maven.compiler.source`/`target` (prefer `maven.compiler.release`)
  or Gradle `java.toolchain.languageVersion`.
- Update the Maven wrapper / Gradle wrapper if the current version does not
  support the target JDK (Gradle 8.5+ for Java 21).
- Upgrade `maven-compiler-plugin`, `maven-surefire-plugin`, and
  `maven-failsafe-plugin` to versions that support the target JDK.
- Watch for removed/encapsulated JDK internals: `sun.misc.*`,
  `javax.xml.bind` (JAXB), `javax.annotation` (moved out of the JDK after
  Java 8/11) — add explicit dependencies where still needed.
- Check bytecode tools (Lombok, MapStruct, AspectJ, Javassist, ByteBuddy,
  CGLIB) for target-JDK-compatible versions; these break first.
- `SecurityManager`, Nashorn, and Applet APIs are removed or deprecated for
  removal — flag usages as manual review items if behavior depends on them.
- Reflection over JDK internals may need `--add-opens` flags; prefer fixing
  the dependency version over adding JVM flags.

## Spring Boot 2.x → 3.x

Spring Boot 3 requires Java 17+ and Spring Framework 6. Scan carefully for:

- **javax imports** — see the javax → jakarta section below.
- **Old validation packages** — `javax.validation` →
  `jakarta.validation`; ensure `spring-boot-starter-validation` is present
  (validation is no longer pulled in transitively by web starter).
- **Outdated servlet APIs** — `javax.servlet` → `jakarta.servlet`
  (Servlet 6.0); check filters, listeners, and any embedded-container
  customizers.
- **Deprecated security configuration** — `WebSecurityConfigurerAdapter`
  is removed; migrate to component-based `SecurityFilterChain` beans.
  `antMatchers`/`mvcMatchers` → `requestMatchers`. Preserve the exact same
  authorization rules — this is a high-risk area for silent behavior change.
- **Hibernate 5 → 6 issues** — see below.
- **Test annotation changes** — `@MockBean`/`@SpyBean` locations, JUnit 4
  runners, `spring.factories`-based test configuration.

Additional Boot 3 items:

- Property renames: run with `spring-boot-properties-migrator` on the
  classpath during migration to detect renamed/removed properties, then
  remove it before finishing.
- `spring.factories` auto-configuration registration is replaced by
  `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`.
- Actuator endpoint and metrics changes (Micrometer 1.10+, Observation API).
- Trailing-slash matching is disabled by default in Spring MVC — flag any
  endpoints that relied on it as manual review items (API contract risk).
- HTTP clients: `RestTemplate` still works; `HttpClient`-related
  configuration classes moved packages.

## javax → jakarta migration

Handle carefully and mechanically:

1. Inventory all `javax.*` imports first. Only EE packages migrate —
   `javax.sql`, `javax.crypto`, `javax.naming`, `javax.annotation.processing`
   and other JDK packages **stay as javax**.
2. Migrating packages include: `javax.persistence`, `javax.validation`,
   `javax.servlet`, `javax.annotation` (Common Annotations), `javax.transaction`,
   `javax.ws.rs`, `javax.jms`, `javax.mail`, `javax.xml.bind`.
3. Replace dependencies, not just imports: e.g.
   `javax.servlet:javax.servlet-api` → `jakarta.servlet:jakarta.servlet-api`,
   `javax.validation:validation-api` → `jakarta.validation:jakarta.validation-api`.
4. Check third-party libraries for jakarta-compatible versions before
   migrating code that touches them.
5. Watch for `javax` strings outside imports: XML descriptors (`web.xml`,
   `persistence.xml`), `@Generated` annotations from code generators, and
   reflective `Class.forName` lookups.

## Hibernate 5 → 6

- ID generation semantics changed for `AUTO`/sequence generators — verify
  the generated SQL matches the existing schema; flag mismatches as manual
  review (database behavior risk).
- Deprecated dialect classes are consolidated; remove version-specific
  dialects where auto-detection works.
- `javax.persistence` → `jakarta.persistence`.
- Type system rework: custom `UserType`s and `@Type` annotations need
  rewriting to the new SPI.
- Query behavior: stricter JPQL validation, changed handling of implicit
  joins and numeric literal typing — run all repository/query tests.
- Criteria API returns typed expressions more strictly; some casts break at
  compile time.

## Test framework alignment

- JUnit 4 → JUnit 5: `@Test(expected=…)` → `assertThrows`, `@Before/@After` →
  `@BeforeEach/@AfterEach`, `@RunWith(SpringRunner.class)` →
  `@ExtendWith(SpringExtension.class)` (or rely on `@SpringBootTest`
  meta-annotations), `@Rule`-based patterns → extensions.
  Keep `junit-vintage-engine` temporarily if a big-bang test migration is
  too risky; remove it once migration completes.
- Mockito: align to a version compatible with the target JDK; replace
  deprecated `MockitoAnnotations.initMocks` with `openMocks` or
  `@ExtendWith(MockitoExtension.class)`.
- Surefire/Failsafe: ensure versions that discover JUnit 5 tests — silent
  test-discovery loss is a common trap; compare test counts before and after.

## Dependency alignment strategy

- Prefer managing versions through the Spring Boot BOM / parent; remove
  explicit version overrides that the BOM now manages.
- Upgrade Jackson, SLF4J/Logback, and database drivers to BOM-managed
  versions rather than pinning.
- After each dependency change, check for duplicate classes on the classpath
  (old javax artifacts lingering next to jakarta ones is the classic case).
