package com.example.validation;

import net.jqwik.api.*;

import java.util.List;

// Feature: jdbc-query-cache-workshop, Property 2: Cache hint transparency
/**
 * Property-based test for cache hint transparency.
 *
 * Validates: Requirements 7.4
 *
 * Property 2: Cache hint transparency
 * For any SQL query string and any valid CACHE_PARAM hint (with arbitrary TTL values
 * like 30s, 5m, 1h), prepending the hint to the query SHALL NOT change the validation
 * outcome — a query that passes validation without the hint SHALL also pass with the hint,
 * and a query that fails validation without the hint SHALL also fail with the hint.
 */
class SqlValidatorCacheHintPropertyTest {

    private static final List<String> BLOCKED_KEYWORDS = List.of(
        "DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT",
        "UPDATE", "CREATE", "GRANT", "REVOKE", "EXEC"
    );

    // --- Generators ---

    @Provide
    Arbitrary<String> validSelectQueries() {
        Arbitrary<String> columns = columnList();
        Arbitrary<String> tables = tableName();
        Arbitrary<String> whereClauses = whereClause();
        Arbitrary<String> orderBy = orderByClause();
        Arbitrary<String> limit = limitClause();
        Arbitrary<String> selectKeyword = selectKeywordVariant();

        return Combinators.combine(selectKeyword, columns, tables, whereClauses, orderBy, limit)
            .as((sel, cols, tbl, where, order, lim) ->
                sel + " " + cols + " FROM " + tbl + where + order + lim);
    }

    @Provide
    Arbitrary<String> invalidQueries() {
        Arbitrary<String> keyword = Arbitraries.of(BLOCKED_KEYWORDS);
        Arbitrary<String> rest = queryRemainder();
        return Combinators.combine(keyword, rest)
            .as((kw, remainder) -> kw + " " + remainder);
    }

    @Provide
    Arbitrary<String> cacheHints() {
        Arbitrary<String> ttlValue = ttlDuration();
        Arbitrary<String> spacing = hintSpacing();
        return Combinators.combine(ttlValue, spacing)
            .as((ttl, space) -> "/* CACHE_PARAM(ttl=" + ttl + ") */" + space);
    }

    @Provide
    Arbitrary<String> validQueryWithHint() {
        return Combinators.combine(cacheHints(), validSelectQueries())
            .as((hint, query) -> hint + query);
    }

    @Provide
    Arbitrary<String> invalidQueryWithHint() {
        return Combinators.combine(cacheHints(), invalidQueries())
            .as((hint, query) -> hint + query);
    }

    // --- Property Tests ---

    /**
     * Validates: Requirements 7.4
     *
     * A valid SELECT query that passes validation without a cache hint
     * SHALL also pass validation when a CACHE_PARAM hint is prepended.
     */
    @Property(tries = 100)
    void validQueryPassesWithAndWithoutHint(
            @ForAll("validSelectQueries") String query,
            @ForAll("cacheHints") String hint) {
        // Without hint - should pass
        SqlValidator.validate(query);
        // With hint - should also pass
        SqlValidator.validate(hint + query);
    }

    /**
     * Validates: Requirements 7.4
     *
     * An invalid query that fails validation without a cache hint
     * SHALL also fail validation when a CACHE_PARAM hint is prepended.
     */
    @Property(tries = 100)
    void invalidQueryFailsWithAndWithoutHint(
            @ForAll("invalidQueries") String query,
            @ForAll("cacheHints") String hint) {
        // Without hint - should fail
        boolean failsWithout = false;
        try {
            SqlValidator.validate(query);
        } catch (InvalidQueryException e) {
            failsWithout = true;
        }

        // With hint - should also fail
        boolean failsWith = false;
        try {
            SqlValidator.validate(hint + query);
        } catch (InvalidQueryException e) {
            failsWith = true;
        }

        if (failsWithout != failsWith) {
            throw new AssertionError(
                "Cache hint changed validation outcome. Without hint: " +
                (failsWithout ? "rejected" : "accepted") +
                ", With hint: " + (failsWith ? "rejected" : "accepted") +
                ". Query: " + query + ", Hint: " + hint);
        }
    }

    /**
     * Validates: Requirements 7.4
     *
     * Prepending a CACHE_PARAM hint with various TTL formats to a valid SELECT
     * query must always pass validation.
     */
    @Property(tries = 100)
    void hintWithVariousTtlFormatsDoesNotAffectValidSelect(
            @ForAll("validQueryWithHint") String queryWithHint) {
        // Should not throw
        SqlValidator.validate(queryWithHint);
    }

    /**
     * Validates: Requirements 7.4
     *
     * Prepending a CACHE_PARAM hint to an invalid query must always fail validation.
     */
    @Property(tries = 100)
    void hintWithInvalidQueryAlwaysRejected(
            @ForAll("invalidQueryWithHint") String queryWithHint) {
        try {
            SqlValidator.validate(queryWithHint);
            throw new AssertionError("Expected InvalidQueryException for: " + queryWithHint);
        } catch (InvalidQueryException e) {
            // Expected - validation correctly rejected the query
        }
    }

    // --- Helper Generators ---

    private Arbitrary<String> selectKeywordVariant() {
        return Arbitraries.of("SELECT", "select", "Select", "sElEcT");
    }

    private Arbitrary<String> columnList() {
        Arbitrary<String> singleCol = identifier();
        return singleCol.list().ofMinSize(1).ofMaxSize(4)
            .map(cols -> String.join(", ", cols));
    }

    private Arbitrary<String> tableName() {
        return identifier();
    }

    private Arbitrary<String> identifier() {
        return Arbitraries.strings()
            .withCharRange('a', 'z')
            .ofMinLength(2)
            .ofMaxLength(10);
    }

    private Arbitrary<String> whereClause() {
        return Arbitraries.of(
            "",
            " WHERE id > 0",
            " WHERE name IS NOT NULL",
            " WHERE status = 'active'",
            " WHERE created_at > '2020-01-01'"
        );
    }

    private Arbitrary<String> orderByClause() {
        return Arbitraries.of(
            "",
            " ORDER BY id",
            " ORDER BY name ASC",
            " ORDER BY created_at DESC"
        );
    }

    private Arbitrary<String> limitClause() {
        return Arbitraries.of("", " LIMIT 10", " LIMIT 100", " LIMIT 25");
    }

    private Arbitrary<String> queryRemainder() {
        return Arbitraries.of(
            "TABLE users",
            "FROM accounts WHERE id = 1",
            "INTO logs VALUES (1, 'test')",
            "users SET name = 'x' WHERE id = 1",
            "INDEX idx ON users(name)",
            "ALL PRIVILEGES ON db.* TO user",
            "PROCEDURE sp_test"
        );
    }

    private Arbitrary<String> ttlDuration() {
        return Arbitraries.of(
            "30s", "60s", "120s", "300s",
            "1m", "5m", "10m", "30m",
            "1h", "2h", "12h", "24h",
            "1000", "500ms", "45s"
        );
    }

    private Arbitrary<String> hintSpacing() {
        return Arbitraries.of(" ", "  ", "\n", "\t", " \n");
    }
}
