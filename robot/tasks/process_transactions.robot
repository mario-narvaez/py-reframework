*** Settings ***
Documentation    Download a demo statement for each valid row in the input CSV.
Library          py_reframework.transactions
Library          py_reframework.portal_support
Resource         ../resources/demo_portal.resource
Task Teardown    Finish Browser Session

*** Variables ***
${CONFIG_FILE}     ${CURDIR}${/}..${/}..${/}config${/}settings.csv
${HEADLESS}        ${True}
${BROWSER_OPEN}    ${False}

*** Tasks ***
Process Statement Transactions
    ${batch}=    Initialize Batch    ${CONFIG_FILE}
    Log    Results CSV: ${batch}[results_path]    console=${True}
    ${session_ready}=    Set Variable    ${False}
    ${business_failures}=    Set Variable    ${0}
    FOR    ${transaction}    IN    @{batch}[transactions]
        IF    $transaction["error"]
            Record Transaction Result    ${batch}    ${transaction}    business_failure    error=${transaction}[error]
            ${business_failures}=    Evaluate    ${business_failures} + 1
            CONTINUE
        END
        TRY
            IF    not ${session_ready}
                Validate Portal Credentials
                Open Demo Portal    ${batch}[portal_url]
                Log In To Demo Portal
                Open Banking Page
                ${session_ready}=    Set Variable    ${True}
            END
            ${download_path}=    Reserve Batch Statement Path    ${batch}
            ${path}=    Download Demo Statement
            ...    ${transaction}[start_date]
            ...    ${transaction}[end_date]
            ...    ${download_path}
            ...    ${batch}[download_timeout_seconds]
        EXCEPT
            IF    ${BROWSER_OPEN}
                Capture Failure Evidence
            END
            Record Transaction Result    ${batch}    ${transaction}    system_failure
            ...    error=Portal processing failed; see Robot log.
            Fail    Portal processing failed; see Robot log and results CSV.
        END
        Record Transaction Result    ${batch}    ${transaction}    success    download_path=${path}
    END
    IF    ${business_failures} > 0
        Fail    ${business_failures} transaction(s) failed validation; see results CSV.
    END
