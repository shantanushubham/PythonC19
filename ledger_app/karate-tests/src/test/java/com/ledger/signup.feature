Feature: User Signup

  # ---------------------------------------------------------------------------
  # Happy path
  # ---------------------------------------------------------------------------

  Scenario: Successful signup returns 201 with user data and JWT token
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "Karate",
        "last_name":  "Signup",
        "dob":        "1995-06-15",
        "phone_number": "8000000001",
        "password":   "securepass"
      }
      """
    When method POST
    Then status 201
    And match response.user.phone_number == '8000000001'
    And match response.user.first_name   == 'Karate'
    And match response.user.last_name    == 'Signup'
    And match response.user.user_type    == 'BASIC_USER'
    And match response contains { token: '#string' }
    # password must never be returned
    And match response.user !contains { password: '#string' }

  # ---------------------------------------------------------------------------
  # Validation failures
  # ---------------------------------------------------------------------------

  Scenario: Signup with a duplicate phone number returns 400
    # Create the first user
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "First",
        "last_name":  "User",
        "dob":        "1992-01-01",
        "phone_number": "8000000002",
        "password":   "securepass"
      }
      """
    When method POST
    Then status 201

    # Attempt signup with the same phone number
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "Second",
        "last_name":  "User",
        "dob":        "1993-02-02",
        "phone_number": "8000000002",
        "password":   "securepass"
      }
      """
    When method POST
    Then status 400

  Scenario: Signup with a password shorter than 8 characters returns 400
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "Short",
        "last_name":  "Pass",
        "dob":        "1995-03-03",
        "phone_number": "8000000003",
        "password":   "abc"
      }
      """
    When method POST
    Then status 400
    And match response contains { password: '#array' }

  Scenario: Signup with a missing required field returns 400
    Given url baseUrl + '/auth/signup/'
    And request
      """
      {
        "first_name": "No",
        "last_name":  "Password",
        "dob":        "1995-04-04",
        "phone_number": "8000000004"
      }
      """
    When method POST
    Then status 400
    And match response contains { password: '#array' }
