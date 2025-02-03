# jira_manager module
# Module holds the class => JiraManager - manages JIRA ticket interface
# Class responsible for all JIRA related interactions including ticket searching, data pull, file attaching, comment
# posting and field updating.
#
from jira import JIRA
from datetime import date
from urllib.parse import urlparse
import logging


class JiraManager(object):
    def __init__(self, url, jira_token):
        self.tickets = []
        self.jira = JIRA(url, basic_auth=jira_token)
        self.date_range = ""
        self.file_name = ""
        self.hub_study_number = ""
        self.start_date = ""
        self.lead_analyst = None
        self.advertiser = None
        self.media_partner = None
        self.advertiser_id = None
        self.media_partners = ['YouTube', 'Snapchat, Inc.', 'Spotify']
        self.today_date = date.today().strftime('%Y-%m-%d')  # format required for Jira date field
        self.logger = logging.getLogger(__name__)

        # available transitions for this type of ticket
        #self.ticket_transitionid = '41'   # id for 'Impressions Complete'
        #self.ticket_transitionid = '81'   # id for 'Request Impressions'
        #self.ticket_transitionid = '251'  # id for 'Back to Open'
        #self.ticket_transitionid = '331'  # id for 'Issue Encountered'
        self.ticket_transitionid = '21'   # id for 'Input Verification'

        # adjustable date fields in ticket
        self.date_field = 'due_date'            # due
        self.date_field = 'customfield_10231'   # SLA start date
        self.date_field = 'customfield_10431'   # start date
        self.date_field = 'customfield_10418'   # end date
        self.date_field = 'customfield_11426'   # post-period end date

    # Searches Jira for all tickets that match the ticket query criteria
    #
    def find_tickets(self, ticket_type, project, reporter, issue_type, vertical, status, product, media_partner):
        # Search Jira to find corresponding tickets, jql searches for 1 of 3 different ticket types
        if ticket_type == 'Standard':
            jql_query = 'project = {} AND reporter IN {} AND issuetype IN {} AND vertical IN {} AND status = {} ' \
                        'AND product NOT IN {} AND "Media Partner - HUB" NOT IN {} AND NOT summary ~ "test*"'\
                        .format(project, reporter, issue_type, vertical, status, product, media_partner)
        elif ticket_type == 'YouTube':
            jql_query = 'project = {} AND reporter IN {} AND issuetype IN {} AND vertical IN {} AND status = {} ' \
                        'AND product NOT IN {} AND "Media Partner - HUB" IN {} AND NOT summary ~ "test*"'\
                        .format(project, reporter, issue_type, vertical, status, product, media_partner)
        elif ticket_type == 'In-Flight ROI':
            jql_query = 'project = {} AND reporter IN {} AND issuetype IN {} AND vertical IN {} AND status = {} ' \
                        'AND product IN {} AND "Media Partner - HUB" NOT IN {} AND NOT summary ~ "test*"'\
                        .format(project, reporter, issue_type, vertical, status, product, media_partner)
        else:  # Retail & CPG Retail tickets
            jql_query = 'project = {} AND issuetype IN {} AND vertical IN {} AND status = {} ' \
                        'AND "Media Partner - HUB" NOT IN {} AND NOT summary ~ "test*"'\
                        .format(project, issue_type, vertical, status, media_partner)

        self.tickets = self.jira.search_issues(jql_query, maxResults=500)

        if len(self.tickets) > 0:
            return self.tickets
        else:
            return None

    # Retrieves the hub study number from ticket to populate api study call convert to integer type, also returns
    # the post-period end date and start date for hive query
    #
    def ticket_information_pull(self, ticket):
        ticket = self.jira.issue(ticket.key)
        self.advertiser = ticket.fields.customfield_10414
        # Converts field value returned link url to tuple via urlparse, selects the item that represents the path [-4],
        # parse this item before selecting the last item [-1] from this string after splitting on '/'
        self.hub_study_number = int(urlparse(ticket.fields.customfield_17018)[-4].split('/')[-1].strip())

        return self.advertiser, self.hub_study_number

    # Retrieves the media partner - HUB from the jira ticket field
    #
    def media_partner_pull(self, ticket, advertiser):
        ticket = self.jira.issue(ticket.key)
        self.media_partner = ticket.fields.customfield_17028
        if self.media_partner not in self.media_partners or advertiser != 'Pepsico':
            self.media_partner = None
        return self.media_partner

    # Retrieves the pid from the jira ticket field
    #
    def pid_info_pull(self, ticket):
        ticket = self.jira.issue(ticket.key)
        self.advertiser_id = ticket.fields.customfield_11492
        return self.advertiser_id

    # Add/Update Lead Analyst
    #
    def update_field(self, ticket, cf_name, user_name):
        if cf_name == 'lead analyst' and ticket.fields.customfield_12325 is not None:
            self.logger.info("Lead Analyst has already been assigned: {}".format(ticket.fields.customfield_12325))
        else:
            ticket.update(fields={'customfield_12325': {'name': user_name}})
            self.logger.info("Lead Analyst has been updated to : {}".format(user_name))

    # Add Watcher
    #
    def add_watcher(self, ticket, user_name):
        self.jira.add_watcher(ticket, user_name)

    @staticmethod
    # Add/Update Reporter
    #
    def update_reporter(ticket, user_name):
        ticket.update(reporter={'name': user_name})

    # Update the field 'Due Date' in the ticket to today's date
    #
    def update_date_field(self, ticket):
        ticket.fields.due_date = self.today_date
        ticket.update(fields={'duedate': ticket.fields.due_date})

    # Reassign Ticket
    #
    '''def assign_ticket(self, ticket, user_name):
        self.jira.assign_issue(ticket, user_name)'''

    # Add a comment to ticket informing lead analyst of data availability and post qubole results
    #
    '''def add_transaction_data_comment(self, ticket_key, lead_analyst, results):
        cam_ticket = self.jira.issue(ticket_key)
        reporter = cam_ticket.fields.reporter.key
        message = """[~{attention}], {transaction_data_alert} for Ticket =>    *{ticket_id}*

                     ||Return Parameter||Result||
                     |Total Days in Period|{days}|
                     |Distinct Days Transaction Count|{trans}|
                     |Earliest Transaction Date|{min}|
                     |Final Transaction Date|{max}|
                     """.format(reporter, attention=lead_analyst,
                                transaction_data_alert=self.transaction_data_alert,
                                ticket_id=ticket_key,
                                days=results[0],
                                trans=results[1],
                                min=results[2],
                                max=results[3]
                                )
        self.jira.add_comment(issue=cam_ticket, body=message)'''

    # Transition the ticket to one of five statuses, see above to set selection
    #
    def progress_ticket(self, ticket_key):
        ticket = self.jira.issue(ticket_key)
        self.jira.transition_issue(ticket, self.ticket_transitionid)

    # Ends the current JIRA session
    #
    def kill_session(self):
        self.jira.kill_session()
