*** Settings ***
Library    Browser    run_on_failure=Take Screenshot

*** Variables ***
${LOGIN_LINK}      css=nav >> role=link[name="Login"]
${BANKING_LINK}    data-testid=sidebar >> css=a[href$="/banking"]

*** Keywords ***
Open Demo Portal
    [Arguments]    ${portal_url}
    New Browser    chromium    headless=${HEADLESS}
    Set Suite Variable    ${BROWSER_OPEN}    ${True}
    New Context    acceptDownloads=${True}
    New Page    ${portal_url}

Log In To Demo Portal
    Click    ${LOGIN_LINK}
    Click    data-testid=sidebar-toggle
    Fill Secret    data-testid=username-input    %PORTAL_USERNAME
    Fill Secret    data-testid=password-input    %PORTAL_PASSWORD
    Click    data-testid=login-button
    Wait For Elements State    css=[data-testid="close-success-dialog"], [data-testid="username-error"]    visible
    ${error_count}=    Get Element Count    data-testid=username-error
    IF    ${error_count} > 0
        Fail    Demo portal rejected the supplied credentials.
    END
    Click    data-testid=close-success-dialog

Open Banking Page
    Click    data-testid=sidebar-toggle
    Click    ${BANKING_LINK}
    Click    data-testid=sidebar-toggle
    Wait For Elements State    data-testid=start-date    visible

Download Demo Statement
    [Arguments]    ${start_date}    ${end_date}    ${download_path}    ${timeout_seconds}
    Fill Text    data-testid=start-date    ${start_date}
    Fill Text    data-testid=end-date    ${end_date}
    ${download}=    Promise To Wait For Download    ${download_path}    download_timeout=${timeout_seconds} seconds
    Click    data-testid=download-statement
    ${result}=    Wait For    ${download}
    Should Be Equal    ${result}[state]    finished
    Verify Demo Statement    ${result}[saveAs]    ${start_date}    ${end_date}
    RETURN    ${result}[saveAs]

Finish Browser Session
    IF    ${BROWSER_OPEN}
        Run Keyword If Test Failed    Capture Failure Evidence
        Close Browser    ALL
    END

Capture Failure Evidence
    Run Keyword And Warn On Failure    Take Screenshot
