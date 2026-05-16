package com.ledger;

import com.intuit.karate.junit5.Karate;

/**
 * Entry point for all Karate feature files.
 *
 * Run all tests:
 *   mvn test
 *
 * Run against a specific server:
 *   mvn test -DbaseUrl=http://staging.example.com
 *
 * Run a single feature:
 *   mvn test -Dkarate.options="classpath:com/ledger/signup.feature"
 */
class KarateRunnerTest {

    @Karate.Test
    Karate testSignup() {
        return Karate.run("signup").relativeTo(getClass());
    }

    @Karate.Test
    Karate testLogin() {
        return Karate.run("login").relativeTo(getClass());
    }
}
