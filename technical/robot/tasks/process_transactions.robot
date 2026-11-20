*** Settings ***
Documentation    Download a demo statement for each valid row in the input CSV.
Library          Collections
Library          py_reframework.transactions
Library          py_reframework.portal_support
Resource         ../resources/demo_portal.resource
Task Teardown    Finish Batch

*** Variables ***
${CONFIG_FILE}        ${CURDIR}${/}..${/}..${/}config${/}settings.csv
${HEADLESS}           ${False}
${BROWSER_OPEN}       ${False}
${RUN_STATE}          ${None}
${OUTAGE_THRESHOLD}   ${3}

*** Tasks ***
Process Statement Transactions
    ${state}=    Create Dictionary
    ...    session_ready=${False}
    ...    successes=${0}
    ...    business_failures=${0}
    ...    system_failures=${0}
    ...    consecutive_failures=${0}
    Set Test Variable    ${RUN_STATE}    ${state}
    ${batch}=    Initialize Batch    ${CONFIG_FILE}
    Log    Results CSV: ${batch}[results_path]    console=${True}
    FOR    ${transaction}    IN    @{batch}[transactions]
        Process Transaction With Recovery    ${batch}    ${transaction}    ${state}
        Stop If Too Many System Failures    ${state}
    END
    Fail If Batch Has Failures    ${state}

*** Keywords ***
Process Transaction With Recovery
    [Arguments]    ${batch}    ${transaction}    ${state}
    IF    $transaction["error"]
        Record Transaction Result    ${batch}    ${transaction}    business_failure
        ...    error=${transaction}[error]    attempts=${0}
        ${count}=    Evaluate    $state["business_failures"] + 1
        Set To Dictionary    ${state}    business_failures=${count}
        RETURN
    END
    ${maximum_attempts}=    Evaluate    $batch["max_retries"] + 1
    FOR    ${index}    IN RANGE    ${maximum_attempts}
        ${attempt}=    Evaluate    $index + 1
        TRY
            ${result}=    Process Statement Attempt    ${batch}    ${transaction}    ${state}
            IF    $result["status"] == "retryable"
                IF    ${attempt} < ${maximum_attempts}
                    Log    Portal returned HTTP ${result}[http_status]; retrying after ${batch}[retry_delay_seconds] seconds.    console=${True}
                    Sleep    ${batch}[retry_delay_seconds] seconds
                    CONTINUE
                END
                Set To Dictionary    ${result}    status=system_failure
            END
        EXCEPT
            IF    ${BROWSER_OPEN}
                Capture Failure Evidence
            END
            ${result}=    Create Dictionary
            ...    status=system_failure
            ...    download_path=${EMPTY}
            ...    error=Non-retryable system failure; see Robot log.
            Record Transaction Outcome    ${batch}    ${transaction}    ${state}    ${result}    ${attempt}
            Fail    Non-retryable system failure; see Robot log and results CSV.
        END
        Record Transaction Outcome    ${batch}    ${transaction}    ${state}    ${result}    ${attempt}
        RETURN
    END

Process Statement Attempt
    [Arguments]    ${batch}    ${transaction}    ${state}
    ${temporary_status}=    Ensure Portal Session    ${batch}    ${state}
    IF    $temporary_status is not None
        ${result}=    Create Dictionary
        ...    status=retryable
        ...    http_status=${temporary_status}
        ...    download_path=${EMPTY}
        ...    error=Portal returned temporary HTTP ${temporary_status}; retries exhausted.
        RETURN    ${result}
    END
    ${download_path}=    Reserve Batch Statement Path    ${batch}
    ${path}=    Download Demo Statement
    ...    ${transaction}[start_date]
    ...    ${transaction}[end_date]
    ...    ${download_path}
    ...    ${batch}[download_timeout_seconds]
    ${valid}=    Check Demo Statement    ${path}    ${transaction}[start_date]    ${transaction}[end_date]
    IF    not ${valid}
        Capture Failure Evidence
        Close Portal Session
        Set To Dictionary    ${state}    session_ready=${False}
        ${result}=    Create Dictionary
        ...    status=system_failure
        ...    download_path=${EMPTY}
        ...    error=Downloaded statement does not contain the requested date range.
        RETURN    ${result}
    END
    ${result}=    Create Dictionary    status=success    download_path=${path}    error=${EMPTY}
    RETURN    ${result}

Ensure Portal Session
    [Arguments]    ${batch}    ${state}
    IF    $state["session_ready"]
        RETURN    ${None}
    END
    Validate Portal Credentials
    ${http_status}=    Open Demo Portal    ${batch}[portal_url]    ${batch}[demo_delay_seconds]
    IF    $http_status in (502, 503, 504)
        Capture Failure Evidence
        Close Portal Session
        RETURN    ${http_status}
    END
    IF    ${http_status} < 200 or ${http_status} >= 400
        Fail    Portal returned non-retryable HTTP status ${http_status}.
    END
    Log In To Demo Portal
    Open Banking Page
    Set To Dictionary    ${state}    session_ready=${True}
    RETURN    ${None}

Record Transaction Outcome
    [Arguments]    ${batch}    ${transaction}    ${state}    ${result}    ${attempt}
    Record Transaction Result    ${batch}    ${transaction}    ${result}[status]
    ...    download_path=${result}[download_path]    error=${result}[error]    attempts=${attempt}
    IF    $result["status"] == "success"
        ${count}=    Evaluate    $state["successes"] + 1
        Set To Dictionary    ${state}    successes=${count}    consecutive_failures=${0}
    ELSE
        ${count}=    Evaluate    $state["system_failures"] + 1
        ${consecutive}=    Evaluate    $state["consecutive_failures"] + 1
        Set To Dictionary    ${state}    system_failures=${count}    consecutive_failures=${consecutive}
    END

Stop If Too Many System Failures
    [Arguments]    ${state}
    IF    ${state}[consecutive_failures] >= ${OUTAGE_THRESHOLD}
        Fail    Stopped after ${state}[consecutive_failures] consecutive system failures; see results CSV.
    END

Fail If Batch Has Failures
    [Arguments]    ${state}
    IF    ${state}[business_failures] > 0 or ${state}[system_failures] > 0
        Fail    One or more transactions failed; see results CSV.
    END

Close Portal Session
    Close Browser    ALL
    Set Suite Variable    ${BROWSER_OPEN}    ${False}

Finish Batch
    IF    $RUN_STATE is not None
        Log    Summary: ${RUN_STATE}[successes] succeeded, ${RUN_STATE}[business_failures] business failures, ${RUN_STATE}[system_failures] system failures.    console=${True}
    ELSE
        Log    Summary unavailable: batch state was not initialized.    WARN    console=${True}
    END
    Finish Browser Session
