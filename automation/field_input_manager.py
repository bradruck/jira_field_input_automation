# field_input_manager module
# Module holds the class => FieldInputManager - manages the Jira Ticket Field Input Process
# Class responsible for overall program management
#
from datetime import datetime, timedelta
import time
import os
import logging
from glob import glob
from jira_manager import JiraManager
from excel_manager import ExcelManager
from email_manager import EmailManager
from api_manager import APICallManager
from mysql_manager import MySQLManager

today_date = (datetime.now() - timedelta(hours=7)).strftime('%Y-%m-%d')


class FieldInputManager(object):
    def __init__(self, config_params):
        self.data_source = config_params['data_source']
        self.jira_url = config_params['jira_url']
        self.jira_token = config_params['jira_token']
        self.jira_pars = JiraManager(self.jira_url, self.jira_token)
        self.jql_project = config_params['jql_project']
        self.jql_reporter = config_params['jql_reporter']
        self.jql_product = config_params['jql_product']
        self.jql_type = config_params['jql_type']
        self.jql_vertical = config_params['jql_vertical']
        self.jql_vertical2 = config_params['jql_vertical2']
        self.jql_status = config_params['jql_status']
        self.jql_yt_media_partner = config_params['jql_yt_media_partner']
        self.jql_generic_filter1 = config_params['jql_filter1']
        self.jql_generic_filter2 = config_params['jql_filter2']
        self.jql_brand_list = config_params['jql_brand_list']
        self.study_url = config_params['study_url']
        self.account_url = config_params['account_url']
        self.excel_path = config_params['excel_file']
        self.email_subject = config_params['email_subject']
        self.email_to = config_params['email_to']
        self.email_from = config_params['email_from']
        self.email_cc = config_params['email_cc']
        self.excel_file_name = glob(('{}/*.xlsx'.format(self.excel_path)))[-1]
        self.db_config = config_params['db_config']
        self.db = None
        self.db_name = 'cpg_assignments'
        self.table_name = 'assignments'
        self.youtube_media_partner = ['YouTube']
        self.media_partners = ['Snapchat, Inc.', 'Spotify']
        self.in_flight_roi_watcher_list = ['isobel.brooks', 'cara.manion']      # additional watchers
        self.youtube_watcher_list = ['andy.fortna']     # additional watchers
        self.ticket_varieties = ['Standard', 'YouTube', 'In-Flight ROI', 'Retail']
        self.tickets = dict()
        self.provider_set = set()
        self.null_provider_set = set()
        self.logger = logging.getLogger(__name__)

    # Manages the overall automation
    #
    def process_manager(self):
        try:
            # Pulls desired tickets via jql
            self.jira_ticket_search()
        except Exception as e:
            self.logger.error("Jira ticket search failed => {}".format(e))
        else:
            # open up connection with data base, if used
            if self.data_source == '2':
                self.db = MySQLManager(self.db_config, self.db_name)
                self.db.establish_connection()

            # iterate through ticket dict for different ticket varieties
            for k, v in self.tickets.items():

                # process 'YouTube' tickets, no transition
                if k == 'YouTube' and v is not None:
                    self.process_youtube(k, v)

                # process 'Standard' tickets, full treatment, 2 different account types
                if k == 'Standard' and v is not None:
                    self.process_standard(k, v)

                # process 'In-Flight ROI' tickets, no transition
                if k == 'In-Flight ROI' and v is not None:
                    self.process_inflight_roi(k, v)

                # process 'Retail' tickets, transition only
                if k == 'Retail' and v is not None:
                    self.process_retail(k, v)

            self.logger.info("\n")

            # close connection to data base, if used
            if self.data_source == '2':
                self.db.close_connection()

    # Manages the jira ticket search
    #
    def jira_ticket_search(self):
        # pull desired tickets via jql, for two different verticals 'Retail/CPG Retail' or 'CPG Brands'
        for variety in self.ticket_varieties:
            if variety != 'Retail':
                self.tickets[variety] = self.jira_pars.find_tickets(variety, self.jql_project, self.jql_reporter,
                                                                    self.jql_type, self.jql_vertical, self.jql_status,
                                                                    self.jql_product, self.jql_yt_media_partner)
            else:
                self.tickets[variety] = self.jira_pars.find_tickets(variety, self.jql_project, self.jql_reporter,
                                                                    self.jql_type, self.jql_vertical2, self.jql_status,
                                                                    self.jql_product, self.jql_yt_media_partner)
        # print list of found tickets to log
        for k, v in self.tickets.items():
            if v is not None:
                self.logger.info("Ticket variety: {} has {} tickets".format(k, len(v)))
                for ticket in v:
                    if v is not None:
                        self.logger.info("{} {}".format(ticket.key, ticket.fields.reporter.displayName))
            else:
                self.logger.info("Ticket variety: {} has no tickets".format(k))
            self.logger.info("\n")

    # Process tickets with 'YouTube' as media partner
    #
    def process_youtube(self, k, v):
        self.logger.info("'{}' ticket type".format(k))
        self.logger.info("{} ticket(s) were found that match the criteria.\n".format(len(v)))
        time.sleep(2)
        for ticket in v:
            advertiser, data_dict, provider_set, null_provider_set = self.jira_ticket_pull(k, v)

            # for 'YouTube' add specified watchers to ticket
            for k1, v1 in data_dict.items():
                if k1 == 'watchers':
                    v1.extend(self.youtube_watcher_list)

            if data_dict is not None:
                # populates the jira ticket with field information, does not progress ticket
                self.populate_not_progress(ticket, data_dict, advertiser)

            else:
                self.logger.error("Data fetch failed for ticket: {}".format(ticket.key))
                self.emailer(ticket, advertiser)
            self.logger.info("\n")

    # Process 'CPG Brands' tickets, both 'Enterprise' and 'Core Brands' accounts
    #
    def process_standard(self, k, v):
        self.logger.info("'{}' ticket type".format(k))
        self.logger.info("{} ticket(s) were found that match the criteria.\n".format(len(v)))
        time.sleep(2)
        for ticket in v:
            advertiser, data_dict, provider_set, null_provider_set = self.jira_ticket_pull(k, v)

            if data_dict is not None:
                # check account type, first 'Enterprise' accounts
                if data_dict['account_type'] == 'Enterprise':
                    self.logger.info("Account Type: {}".format(data_dict.get('account_type')))
                    # populates the jira ticket with field information
                    self.populate_and_progress(ticket, data_dict, advertiser)

                # next 'Core Brands' accounts
                elif data_dict['account_type'] == 'Core Brands':
                    self.logger.info("Account Type: {}".format(data_dict.get('account_type')))
                    # populates the jira ticket with field information
                    self.populate_and_progress(ticket, data_dict, advertiser)

            else:
                self.logger.error("Data fetch failed for ticket: {}".format(ticket.key))
                self.emailer(ticket, advertiser)
            self.logger.info("\n")

    # Process 'In-Flight ROI' tickets
    #
    def process_inflight_roi(self, k, v):
        self.logger.info("'{}' ticket type".format(k))
        self.logger.info("{} ticket(s) were found that match the criteria.\n".format(len(v)))
        time.sleep(2)
        for ticket in v:
            advertiser, data_dict, provider_set, null_provider_set = self.jira_ticket_pull(k, v)

            if data_dict is not None:
                # add additional watchers for this ticket type
                for k1, v1 in data_dict.items():
                    if k1 == 'watchers':
                        v1.extend(self.in_flight_roi_watcher_list)
                # populates the jira ticket with field information
                self.populate_not_progress(ticket, data_dict, advertiser)
            else:
                self.logger.error("Data fetch failed for ticket: {}".format(ticket.key))
                self.emailer(ticket, advertiser)
            self.logger.info("\n")

    # Process 'Retail' tickets
    #
    def process_retail(self, k, v):
        self.logger.info("'{}' ticket type".format(k))
        self.logger.info("{} ticket(s) were found that match the criteria.\n".format(len(v)))
        time.sleep(2)
        # iterate through list of tickets
        for ticket in v:
            # collect ticket level info
            advertiser, study_number = self.jira_pars.ticket_information_pull(ticket)
            # progress the status of ticket
            try:
                self.jira_pars.progress_ticket(ticket.key)
            except Exception as e:
                self.logger.error("Jira ticket status progress error for ticket {}, "
                                  "ticket field population should be visually checked => {}"
                                  .format(ticket.key, e))
                # code to send warning email
                self.emailer2(ticket, advertiser)
            else:
                self.logger.info("The ticket {} has been progressed to 'Input Verification' "
                                 "status".format(ticket.key))

    # Jira ticket population with ticket progression
    #
    def populate_and_progress(self, ticket, data_dict, advertiser):
        try:
            self.jira_ticket_populate(ticket, data_dict, advertiser, data_dict['account_type'])
            self.logger.info("List of names and ticket fields: {}".format(data_dict))
        except Exception as e:
            self.logger.error("Jira ticket field populate error for ticket {}, "
                              "ticket field population should be visually checked => {}"
                              .format(ticket.key, e))
        else:
            # if field population success, progress the status of ticket
            try:
                self.jira_pars.progress_ticket(ticket.key)
            except Exception as e:
                self.logger.error("Jira ticket status progress error for ticket {}, "
                                  "ticket field population should be visually checked => {}"
                                  .format(ticket.key, e))
                # send warning email
                self.emailer2(ticket, advertiser)
            else:
                self.logger.info("The ticket {} has been progressed to 'Input Verification'"
                                 " status".format(ticket.key))

    # Jira ticket population without ticket progression
    #
    def populate_not_progress(self, ticket, data_dict, advertiser):
        try:
            self.jira_ticket_populate(ticket, data_dict, advertiser, None)
            self.logger.info("List of names and ticket fields: {}".format(data_dict))
        except Exception as e:
            self.logger.error("Jira ticket field populate error for ticket {}, "
                              "ticket field population should be visually checked => {}"
                              .format(ticket.key, e))
        else:
            self.logger.info("The ticket {} has not been progressed.".format(ticket.key))

    # Retrieve information from Jira ticket
    #
    def jira_ticket_pull(self, k, v):
        for ticket in v:
            advertiser, study_number = self.jira_pars.ticket_information_pull(ticket)
            pid = self.jira_pars.pid_info_pull(ticket)
            media_partner = self.jira_pars.media_partner_pull(ticket, advertiser)
            self.logger.info("'{}': parent id".format(pid))
            data_dict, provider_set, null_provider_set = self.source_data(pid, ticket, advertiser,
                                                                          study_number, k, media_partner)
            return advertiser, data_dict, provider_set, null_provider_set

    # Sources the ticket input data from either spreadsheet or database
    #
    def source_data(self, pid, ticket, advertiser, study_number, ticket_type, media_partner):
        provider_set = set()
        null_provider_set = set()
        data_dict = dict()

        if pid is not None:
            self.logger.info('From Jira Ticket, {}{}{}'.format(ticket.key.ljust(12),
                                                               advertiser.ljust(30, '.'),
                                                               str(pid).rjust(10, '.')))
            provider_set.add(advertiser)

            # check for data source 1 is excel file, 2 is mysql
            if self.data_source == '1':
                data_dict = self.excel_data_fetch(int(pid), ticket, ticket_type, media_partner)
            else:
                data_dict = self.mysql_data_fetch(advertiser, ticket, ticket_type, media_partner)

        elif pid is None:
            parent_id = self.api_manager(study_number)
            self.logger.info('From Study Builder, {}{}{}'.format(ticket.key.ljust(12),
                                                                 advertiser.ljust(30, '.'),
                                                                 str(parent_id).rjust(10, '.')))
            provider_set.add(advertiser)

            # check for data source 1 is excel file, 2 is mysql
            if self.data_source == '1':
                data_dict = self.excel_data_fetch(parent_id, ticket, ticket_type, media_partner)
            else:
                data_dict = self.mysql_data_fetch(advertiser, ticket, ticket_type, media_partner)
        else:
            self.logger.info('{}{}{}'.format(ticket.key.ljust(12), advertiser.ljust(30, '.'),
                                             "None".rjust(10, '.')))
            null_provider_set.add(advertiser)
        return data_dict, provider_set, null_provider_set

    # Manages the api class instance creation and function calls
    #
    def api_manager(self, id_num):
        # create api search object instance
        api_manager = APICallManager()

        # api call to find study data
        study_call_results = api_manager.api_call(self.study_url, id_num)

        # confirm api call returned results, search to find required data
        if study_call_results is not None:
            parent_company_id = api_manager.parent_id_fetch(study_call_results)
            return parent_company_id
        else:
            return None

    # Manages the excel data pull
    #
    def excel_data_fetch(self, advertiser, ticket, ticket_type, media_partner):
        excel_data = ExcelManager()
        try:
            # check for ticket type from key value, if standard - search excel via pid, else search via advertiser name
            if ticket_type == 'Standard' or ticket_type == 'In-Flight ROI' or ticket_type == 'YouTube':
                row_identifier = excel_data.pid_row_search(int(advertiser), self.excel_path, media_partner)
            else:
                row_identifier = excel_data.advertiser_row_search(advertiser, self.excel_path, media_partner)
        except Exception as e:
            self.logger.error("Excel file row location error for ticket {}, there may be a problem with the file => {}"
                              .format(ticket.key, e))
            return None
        else:
            if row_identifier is not None:
                excel_data_dict = excel_data.excel_read(row_identifier)
                return excel_data_dict
            else:
                return None

    # Manages the mysql data pull
    #
    def mysql_data_fetch(self, advertiser, ticket, ticket_type, media_partner):
        watcher_list = ['solutions_leader', 'solutions_manager', 'client_solutions_consultant', 'solutions_ops_owner1',
                        'solutions_ops_owner2']
        watchers = list()
        try:
            # check for ticket type via sql search on '' column
            if ticket_type == 'Standard' or ticket_type == 'In-Flight ROI' or ticket_type == 'YouTube':
                mysql_dict = self.db.get_data(self.table_name, int(advertiser), media_partner)
            else:
                mysql_dict = self.db.get_data(self.table_name, advertiser, media_partner)
        except Exception as e:
            self.logger.error("MySQL row location error for ticket {}, there may be a problem with the data set => {}"
                              .format(ticket.key, e))
            return None
        else:
            # create a list out of watchers, remove Nones, and add to dictionary
            if mysql_dict is not None:
                for k, v in mysql_dict.items():
                    if k in watcher_list and v:
                        watchers.append(v)
                mysql_dict['watchers'] = watchers
                return mysql_dict
            else:
                return None

    # Manages the jira ticket field population
    #
    def jira_ticket_populate(self, ticket, account_dict, advertiser, account_type):
        if account_type is not None and account_type == 'Core Brands':
            self.jira_pars.add_watcher(ticket, account_dict.get('solutions_mgr'))
            self.jira_pars.update_reporter(ticket, account_dict.get('solutions_mgr'))
        else:
            if account_dict.get('solutions_mgr') is not None:
                self.jira_pars.update_field(ticket, 'lead analyst', account_dict.get('client_analytics'))
                for watcher in account_dict.get('watchers'):
                    self.jira_pars.add_watcher(ticket, watcher)
                self.jira_pars.update_reporter(ticket, account_dict.get('solutions_manager'))
                pass
            else:
                self.logger.error("There was no reporter listed")
                self.emailer(ticket, advertiser)

    # Creates the Email Manager instance, launches the emailer module
    #
    def emailer(self, ticket, advertiser):
        cm_email = EmailManager(ticket, advertiser, self.email_subject, self.email_to, self.email_from, self.email_cc,
                                self.excel_file_name, self.data_source)
        cm_email.cm_emailer()

    # Creates the Email Manager instance, launches the emailer module
    #
    def emailer2(self, ticket, advertiser):
        cm_email2 = EmailManager(ticket, advertiser, self.email_subject, self.email_to, self.email_from,
                                 self.email_cc, self.excel_file_name, self.data_source)
        cm_email2.cm_emailer2()

    # Checks the log directory for all files and removes those after a specified number of days
    #
    def purge_files(self, purge_days, purge_dir):
        try:
            self.logger.info("")
            self.logger.info("Remove {} days old files from the {} directory".format(purge_days, purge_dir))
            now = time.time()
            for file_purge in os.listdir(purge_dir):
                f_obs_path = os.path.join(purge_dir, file_purge)
                if os.stat(f_obs_path).st_mtime < now - int(purge_days) * 86400 and f_obs_path.split(".")[-1] == "log":
                    time_stamp = time.strptime(time.strftime('%Y-%m-%d %H:%M:%S',
                                                             time.localtime(os.stat(f_obs_path).st_mtime)),
                                               '%Y-%m-%d %H:%M:%S')
                    self.logger.info("Removing File [{}] with timestamp [{}]".format(f_obs_path, time_stamp))

                    os.remove(f_obs_path)

        except Exception as e:
            self.logger.error("{}".format(e))
