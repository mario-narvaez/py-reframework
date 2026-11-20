*** Settings ***
Documentation    Download one simulated statement for a supplied date range.
Library          py_reframework.portal_support
Resource         ../resources/demo_portal.resource
Task Teardown    Finish Browser Session

*** Variables ***
${CONFIG_FILE}     ${CURDIR}${/}..${/}..${/}config${/}settings.csv
${START_DATE}      ${EMPTY}
${END_DATE}        ${EMPTY}
${HEADLESS}        ${True}
${BROWSER_OPEN}    ${False}

*** Tasks ***
Download One Demo Statement
    ${request}=    Prepare Statement Request    ${CONFIG_FILE}    ${START_DATE}    ${END_DATE}
    Open Demo Portal    ${request}[portal_url]
    Log In To Demo Portal
    Open Banking Page
    ${path}=    Download Demo Statement
    ...    ${request}[start_date]
    ...    ${request}[end_date]
    ...    ${request}[download_path]
    ...    ${request}[download_timeout_seconds]
    Log    Statement saved: ${path}
