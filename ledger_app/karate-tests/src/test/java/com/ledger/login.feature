Feature: User Login

  # ---------------------------------------------------------------------------
  # Happy path
  # ---------------------------------------------------------------------------

  Scenario: Successful login returns 200 with user data and JWT token
    # First create the user via signup
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "Login",
        "last_name":  "User",
        "dob":        "1990-01-01",
        "phone_number": "8100000001",
        "password":   "mypassword"
      }
      """
    When method POST
    Then status 201

    # Now login with the same credentials
    Given url baseUrl + '/auth/login/'
    And request { phone_number: '8100000001', password: 'mypassword' }
    When method POST
    Then status 200
    And match response contains { token: '#string', user: '#object' }
    And match response.user.phone_number == '8100000001'
    # password must never be returned
    And match response.user !contains { password: '#string' }

  Scenario: Login with a token returns a usable JWT string
    # Create user
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "Token",
        "last_name":  "Check",
        "dob":        "1991-02-02",
        "phone_number": "8100000002",
        "password":   "mypassword"
      }
      """
    When method POST
    Then status 201

    # Login and capture the token
    Given url baseUrl + '/auth/login/'
    And request { phone_number: '8100000002', password: 'mypassword' }
    When method POST
    Then status 200
    * def token = response.token
    # token must be a non-empty JWT string (three dot-separated base64 parts)
    And match token == '#string'
    And assert token.split('.').length == 3

  # ---------------------------------------------------------------------------
  # Authentication failures
  # ---------------------------------------------------------------------------

  Scenario: Login with a phone number that does not exist returns 401
    Given url baseUrl + '/auth/login/'
    And request { phone_number: '0000000000', password: 'irrelevant' }
    When method POST
    Then status 401
    And match response.error == 'Invalid phone number or password.'

  Scenario: Login with a correct phone number but wrong password returns 401
    # Create user
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "Wrong",
        "last_name":  "Pass",
        "dob":        "1992-03-03",
        "phone_number": "8100000003",
        "password":   "correctpass"
      }
      """
    When method POST
    Then status 201

    # Login with the wrong password
    Given url baseUrl + '/auth/login/'
    And request { phone_number: '8100000003', password: 'wrongpassword' }
    When method POST
    Then status 401
    And match response.error == 'Invalid phone number or password.'

  # ---------------------------------------------------------------------------
  # Validation
  # ---------------------------------------------------------------------------

  Scenario: Login request missing the password field returns 400
    Given url baseUrl + '/auth/login/'
    And request { phone_number: '8100000001' }
    When method POST
    Then status 400
    And match response contains { password: '#array' }
