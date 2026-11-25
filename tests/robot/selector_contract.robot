*** Settings ***
Documentation     Check navigation selectors against a local page with similar links.
Resource          ../../code/robot/resources/demo_portal.resource
Suite Setup       New Browser    chromium
Suite Teardown    Close Browser    ALL
Test Teardown     Close Page    ALL

*** Test Cases ***
Navigation Selectors Identify The Intended Links
    New Page    data:text/html,<nav><a href="/login">Login</a></nav><aside data-testid="sidebar"><a href="/other-login">Login</a><a href="/demowebapp/banking">Banking</a></aside><main><a href="/other/banking">Other banking link</a></main>
    ${login_href}=    Get Attribute    ${LOGIN_LINK}    href
    ${banking_href}=    Get Attribute    ${BANKING_LINK}    href
    Should Be Equal    ${login_href}    /login
    Should Be Equal    ${banking_href}    /demowebapp/banking

Ambiguous Login Links Fail Instead Of Clicking An Arbitrary Match
    New Page    data:text/html,<nav><a href="/login">Login</a><a href="/other">Login</a></nav>
    Run Keyword And Expect Error    *strict mode violation*    Click    ${LOGIN_LINK}
