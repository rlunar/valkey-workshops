package com.example.validation;

import net.jqwik.api.*;
import net.jqwik.api.constraints.*;

import java.util.List;

// Feature: jdbc-query-cache-workshop, Property 1: SELECT-only validation
/**
 * Property-based test for SQL validation.
 *
 * Validates: Requirements 7.1, 7.2
 *
 * Property 1: SELECT-only validation
 * For any SQL string, after stripping leading whitespace and SQL comments
 * (both block and line), the SQL validator SHALL accept the query if and only if
 * the first keyword is SELECT (case-insensitive). All other statement initiators
 * SHALL be rejected.
 */
class SqlValidatorPropertyTest {

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
    Arbitrary<String> whitespaceAndCommentPrefixes() {
        Arbitrary<String> whitespace = Arbitraries.of("", " ", "  ", "\t", "\n", "\r\n", "  \t\n");
        Arbitrary<String> blockComment = blockCommentArbitrary();
        Arbitrary<String> lineComment = lineCommentArbitrary();

        return Combinators.combine(whitespace, Arbitraries.of(true, false), blockComment, lineComment)
            .as((ws, useBlock, block, line) -> {
                StringBuilder sb = new StringBuilder();
                sb.append(ws);
                if (useBlock) {
                    sb.append(block).append(" ");
                } else {
                    sb.append(line).append("\n");
                }
                return sb.toString();
            });
    }

    @Provide
    Arbitrary<String> selectWithWhitespaceAndComments() {
        return Combinators.combine(whitespaceAndCommentPrefixes(), validSelectQueries())
            .as((prefix, query) -> prefix + query);
    }

    @Provide
    Arbitrary<String> invalidWithWhitespaceAndComments() {
        return Combinators.combine(whitespaceAndCommentPrefixes(), invalidQueries())
            .as((prefix, query) -> prefix + query);
    }

    @Provide
    Arbitrary<String> invalidKeywordWithCaseVariations() {
        Arbitrary<String> keyword = Arbitraries.of(BLOCKED_KEYWORDS);
        return keyword.flatMap(kw -> randomCase(kw))
            .flatMap(kw -> queryRemainder().map(rest -> kw + " " + rest));
    }

    // --- Property Tests ---

    /**
     * Validates: Requirements 7.1, 7.2
     *
     * Valid SELECT queries (with any case variation) must always pass validation.
     */
    @Property(tries = 100)
    void selectQueriesAlwaysPass(@ForAll("validSelectQueries") String query) {
        // Should not throw
        SqlValidator.validate(query);
    }

    /**
     * Validates: Requirements 7.1, 7.2
     *
     * SELECT queries prefixed with whitespace and/or SQL comments must still pass.
     */
    @Property(tries = 100)
    void selectWithWhitespaceAndCommentsAlwaysPasses(
            @ForAll("selectWithWhitespaceAndComments") String query) {
        // Should not throw
        SqlValidator.validate(query);
    }

    /**
     * Validates: Requirements 7.1, 7.2
     *
     * Queries starting with blocked keywords must always be rejected.
     */
    @Property(tries = 100)
    void blockedKeywordQueriesAlwaysRejected(@ForAll("invalidQueries") String query) {
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            // Expected - validation correctly rejected the query
        }
    }

    /**
     * Validates: Requirements 7.1, 7.2
     *
     * Queries starting with blocked keywords (with whitespace/comment prefixes) must be rejected.
     */
    @Property(tries = 100)
    void blockedKeywordWithPrefixesAlwaysRejected(
            @ForAll("invalidWithWhitespaceAndComments") String query) {
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            // Expected - validation correctly rejected the query
        }
    }

    /**
     * Validates: Requirements 7.1, 7.2
     *
     * Blocked keywords in any case variation must be rejected.
     */
    @Property(tries = 100)
    void blockedKeywordCaseInsensitiveRejection(
            @ForAll("invalidKeywordWithCaseVariations") String query) {
        try {
            SqlValidator.validate(query);
            throw new AssertionError("Expected InvalidQueryException for: " + query);
        } catch (InvalidQueryException e) {
            // Expected - validation correctly rejected the query
        }
    }

    // --- Helper Generators ---

    private Arbitrary<String> selectKeywordVariant() {
        return Arbitraries.of("SELECT", "select", "Select", "sElEcT", "SELECT");
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
            .ofMaxLength(10)
            .map(s -> s + Arbitraries.integers().between(0, 99).sample());
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

    private Arbitrary<String> blockCommentArbitrary() {
        return Arbitraries.of(
            "/* comment */",
            "/* multi\nline\ncomment */",
            "/* short */",
            "/* a random block comment here */"
        );
    }

    private Arbitrary<String> lineCommentArbitrary() {
        return Arbitraries.of(
            "-- line comment",
            "-- another comment",
            "-- test",
            "-- SELECT should not matter here"
        );
    }

    private Arbitrary<String> randomCase(String word) {
        return Arbitraries.of(
            word.toLowerCase(),
            word.toUpperCase(),
            mixCase(word)
        );
    }

    private String mixCase(String word) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < word.length(); i++) {
            char c = word.charAt(i);
            sb.append(i % 2 == 0 ? Character.toLowerCase(c) : Character.toUpperCase(c));
        }
        return sb.toString();
    }
}
