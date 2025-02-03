# Measurement/CPG Brands - Field Input Automation

# Description -
# The Measurement/CPG Brands - Field Input Automation is an automation to assist Measurement in populating Jira tickets
# with names for Reporter, Watchers and Lead Analyst. The automation is deployed to run every week day morning. It
# starts by searching for Jira tickets that meet a predetermined criteria, from each ticket both the advertiser and
# measurement study number are pulled.  The study number is then used in an api call to 'Study Builder' in order to
# find the corresponding parent company id.  This id is then used to search an excel spreadsheet for the applicable
# names with which to populate the jira ticket.  As long as the excel spreadsheet has a corresponding 'Reporter' name
# for the Jira ticket, the ticket fields are populated. If there is no Reporter give or if the spreadsheet search fails
# to find a data name set, an alert email is sent and no changes are made to the ticket.  This allows the spreadsheet
# to be updated and the ticket is left alone to be available for pick up again the next business day by the automation.
# If the name population is successful, the automation then proceeds to progress the status of the ticket to
# 'Input Verification'.
# There is now added capability to read-in data from a mysql database in place of the excel spreadsheet. The 'data
# source' is set in the config.ini file. '1' -> excel file, or '2' -> mysql table.
#
# Application Information -
# Required modules:     main.py,
#                       field_input_manager.py,
#                       api_manager.py,
#                       excel_manager.py,
#                       jira_manager.py,
#                       email_manager.py,
#                       config.ini
# Deployed Location:    //prd-use1a-pr-34-ci-operations-01/home/bradley.ruck/Projects/cpg_brand_input/
# ActiveBatch Trigger:  //prd-09-abjs-01 (V11)/'Jobs, Folders & Plans'/Operations/Report/CPG_Brand_Input
#                                                                                                   /FIM_Once_a_WeekDay
# Source Code:          //gitlab.oracledatacloud.com/odc-operations/CPG_Brand_Input/
# LogFile Location:     //zfs1/Operations_mounted/CPG_brand_input/automation_logs/
#
# Contact Information -
# Primary Users:        Measurement/CPG
# Lead Customer(s):     Brian Quinn(brian.p.quinn@oracle.com)
# Lead Developer:       Bradley Ruck (bradley.ruck@oracle.com)
# Date Launched:        September, 2018
# Date Updated:         October, 2019

# main module
# Responsible for reading in the basic configurations settings, creating the log file, and creating and launching
# the Field Input Manager (FIM), finally it launches the purge_files method to remove log files that are older
# than a prescribed retention period.
# A console logger option is offered via keyboard input for development purposes when the main.py script is invoked.
# For production, import main as a module and launch the main function as main.main(), which uses 'n' as the default
# input to the the console logger run option.
#
from datetime import datetime, timedelta
import os
import configparser
import logging

from field_input_manager import FieldInputManager


# Define a console logger for development purposes
#
def console_logger():
    # define Handler that writes DEBUG or higher messages to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a simple format for console use
    formatter = logging.Formatter('%(levelname)-7s: %(name)-30s: %(threadName)-12s: %(message)s')
    console.setFormatter(formatter)
    # add the Handler to the root logger
    logging.getLogger('').addHandler(console)


def main(con_opt='n'):
    today_date = (datetime.now() - timedelta(hours=6)).strftime('%Y%m%d-%H%M%S')

    # create a configparser object and open in read mode
    config = configparser.ConfigParser()
    config.read('config.ini')

    # create a dictionary of configuration parameters
    config_params = {
        "data_source":          config.get('Project Details', 'data_source'),
        "jira_url":             config.get('Jira', 'url'),
        "jira_token":           tuple(config.get('Jira', 'authorization').split(',')),
        "jql_project":          config.get('Jira', 'project'),
        "jql_reporter":         config.get('Jira', 'reporter'),
        "jql_product":          config.get('Jira', 'product'),
        "jql_type":             config.get('Jira', 'issuetype'),
        "jql_vertical":         config.get('Jira', 'vertical'),
        "jql_vertical2":        config.get('Jira', 'vertical2'),
        "jql_status":           config.get('Jira', 'status'),
        "jql_yt_media_partner": config.get('Jira', 'yt_media_partner'),
        "jql_filter1":          config.get('Jira', 'generic_filter1'),
        "jql_filter2":          config.get('Jira', 'generic_filter2'),
        "jql_brand_list":       list(config.get('Jira', 'brand_list').split(',')),
        "study_url":            config.get('Api', 'study_url', raw=True),
        "account_url":          config.get('Api', 'account_url', raw=True),
        "excel_file":           config.get('ExcelFile', 'path'),
        "db_config":            config.get('MySQL', 'db_config'),
        "email_subject":        config.get('Email', 'subject'),
        "email_to":             config.get('Email', 'to'),
        "email_from":           config.get('Email', 'from'),
        "email_cc":             config.get('Email', 'cc')
    }

    # logfile path to point to the Operations_limited drive on zfs
    purge_days = config.get('LogFile', 'retention_days')
    log_file_path = config.get('LogFile', 'path')
    logfile_name = '{}{}_{}.log'.format(log_file_path, config.get('Project Details', 'app_name'), today_date)

    # check to see if log file already exits for the day to avoid duplicate execution
    if not os.path.isfile(logfile_name):
        logging.basicConfig(filename=logfile_name,
                            level=logging.INFO,
                            format='%(asctime)s: %(levelname)-7s: %(name)-30s: %(threadName)-12s: %(message)s',
                            datefmt='%m/%d/%Y %H:%M:%S')

        logger = logging.getLogger(__name__)

        # checks for console logger option, default value set to 'n' to not run in production
        if con_opt and con_opt in ['y', 'Y']:
            console_logger()

        logger.info("Process Start - Daily CPG Brand Input Automation - {}\n".format(today_date))

        # create FIM object and launch the process manager
        field_input = FieldInputManager(config_params)
        field_input.process_manager()

        # search logfile directory for old log files to purge
        field_input.purge_files(purge_days, log_file_path)


if __name__ == '__main__':
    # prompt user for use of console logging -> for use in development not production
    ans = input("\nWould you like to enable a console logger for this run?\n Please enter y or n:\t")
    print()
    main(ans)
