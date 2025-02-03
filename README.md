**Description -**

The Measurement/CPG Brands - Field Input Automation is an automation to assist Measurement in populating Jira tickets
with names for Reporter, Watchers and Lead Analyst. The automation is deployed to run every week day morning. It
starts by searching for Jira tickets that meet a predetermined criteria, from each ticket both the advertiser and
measurement study number are pulled.  The study number is then used in an api call to 'Study Builder' in order to
find the corresponding parent company id.  This id is then used to search an excel spreadsheet for the applicable
names with which to populate the jira ticket.  As long as the excel spreadsheet has a corresponding 'Reporter' name
for the Jira ticket, the ticket fields are populated. If there is no Reporter give or if the spreadsheet search fails
to find a data name set, an alert email is sent and no changes are made to the ticket.  This allows the spreadsheet
to be updated and the ticket is left alone to be available for pick up again the next business day by the automation.
If the name population is successful, the automation then proceeds to progress the status of the ticket to 'Input 
Verification'.
There is now added capability to read-in data from a mysql database in place of the excel spreadsheet. 
The 'data source' is set in the config.ini file. '1' -> excel file, or '2' -> mysql table.

**Application Information -**

Required modules: <ul>
                  <li>main.py,
                  <li>field_input_manager.py.py,
                  <li>api_manager.py.py,
                  <li>jira_manager.py,
                  <li>excel_manager.py,
                  <li>email_manager.py,
                  <li>config.ini
                  </ul>

Location:         <ul>
                  <li>Deployment -> //prd-use1a-pr-34-ci-operations-01/opt/app/automations/brad/Projects/cpg_brand_input/
                  <li>
                  <li>Scheduled to run once a weekday, triggered by ActiveBatch-V11 under File/Plan -> CPG_Brand_Input
                  </ul>

Source Code:      <ul>
                  <li>//gitlab.oracledatacloud.com/odc-operations/CPG_Brand_Input/
                  </ul>

LogFile Location: <ul>
                  <li>//zfs1/Operations_mounted/CPG_brand_input/automation_logs/
                  </ul>

**Contact Information -**

Primary Users:    <ul>
                  <li>Measurement/CPG
                  </ul>

Lead Customer:    <ul>
                  <li>
                  </ul>

Lead Developer:   <ul>
                  <li>Bradley Ruck (bradley.ruck@oracle.com)
                  </ul>

Date Launched:    <ul>
                  <li>September, 2018
                  </ul>
Date Updated:     <ul>
                  <li>May, 2019
                  </ul>
