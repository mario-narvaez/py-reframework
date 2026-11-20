*** Settings ***
Library    Browser    run_on_failure=Take Screenshot

*** Variables ***
${LOGIN_LINK}      css=nav >> role=link[name="Login"]
${BANKING_LINK}    data-testid=sidebar >> css=a[href$="/banking"]

*** Keywords ***
Open Demo Portal
    [Arguments]    ${portal_url}    ${demo_delay_seconds}
    ${headless}=    Convert To Boolean    ${HEADLESS}
    IF    ${headless}
        New Browser    chromium    headless=${True}
    ELSE
        New Browser    chromium    headless=${False}    slowMo=${demo_delay_seconds} seconds
    END
    Set Suite Variable    ${BROWSER_OPEN}    ${True}
    New Context    acceptDownloads=${True}
    New Page
    ${status}=    Go To    ${portal_url}
    RETURN    ${status}

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

Apply Demo Date Range
    [Arguments]    ${start_date}    ${end_date}
    Fill Text    data-testid=start-date    ${start_date}
    Fill Text    data-testid=end-date    ${end_date}
    ${states}=    Get Element States    data-testid=apply-date-range
    IF    not $start_date or not $end_date
        IF    'disabled' not in $states
            Fail    Apply Range is unexpectedly enabled for an incomplete date range.
        END
        Clear Demo Dates
        RETURN    ${False}
    END
    IF    'disabled' in $states
        Fail    Apply Range is unexpectedly disabled for a complete date range.
    END
    Click    data-testid=apply-date-range
    Wait For Elements State    data-testid=date-range-display    visible
    ${selected}=    Get Text    data-testid=date-range-display
    Should Match Regexp    ${selected}    ^Selected: ${start_date} to ${end_date} \\(-?\\d+ days\\)$
    RETURN    ${True}

Download Demo Statement
    [Arguments]    ${download_path}    ${timeout_seconds}
    ${download}=    Promise To Wait For Download    ${download_path}    download_timeout=${timeout_seconds} seconds
    Click    data-testid=download-statement
    ${result}=    Wait For    ${download}
    Should Be Equal    ${result}[state]    finished
    Clear Demo Dates
    RETURN    ${result}[saveAs]

Clear Demo Dates
    Clear Text    data-testid=start-date
    Clear Text    data-testid=end-date

Finish Browser Session
    IF    ${BROWSER_OPEN}
        Run Keyword If Test Failed    Capture Failure Evidence
        Close Browser    ALL
        Set Suite Variable    ${BROWSER_OPEN}    ${False}
    END

Capture Failure Evidence
    Run Keyword And Warn On Failure    Take Screenshot
