# weekly_emailer module
# Module holds the class => WeeklyEmailManager - manages the email creation and the smtp interface
# Class responsible for all email related management
#
from smtplib import SMTP
# from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import logging


class EmailManager(object):
    def __init__(self, ticket, advertiser, subject, to_address, from_address, cc, html_link, data_source):
        self.logger = logging.getLogger(__name__)
        self.data_source = data_source
        self.msg = ""
        self.ticket = ticket
        self.advertiser = advertiser
        self.subj = subject
        self.to_address = to_address
        self.from_address = from_address
        self.cc = cc
        self.file_name = os.path.basename(html_link)
        self.text_excel1 = "Measurement/CPG Brands,\n\n" + \
                           "There appears to be a problem locating the input data for the Jira ticket, you may wish " \
                           "to check the spreadsheet: '{}', located in the 'CPG_brand_input' directory on the " \
                           "Operations_mounted zfs1 drive." \
                           "\n\nClick on the appropriate link below to navigate to the network server : " \
                           .format(self.file_name)

        self.text_mysql1 = "Measurement/CPG Brands,\n\n" + \
                           "There appears to be a problem locating the input data for the Jira ticket, you may wish " \
                           "to check the mysql data table: 'assignments', located in the 'cpg_assignments' schema on " \
                           "the ??? server."

        self.text_progress_failure = "Measurement/CPG Brands,\n\n" + \
                                     "There was a problem advancing the ticket status, " + \
                                     "ticket field population should be visually checked."

        self.html = """\
                <html>
                    <head></head>
                    <body>
                        <p>On MacOs:   <a href="smb://zfs1/Operations_mounted/">//zfs1/Operations_mounted/</a><br>

                           On Windows: <a href="\\zfs1\Operations_mounted\">\\\zfs1\Operations_mounted\</a>
                        </p>
                    </body>
                </html>
                """

        self.text2 = "Please find details below:\n\n" + \
                     "Jira Ticket: " + self.ticket.key + "\n" + \
                     "Advertiser: " + self.advertiser + "\n\n" + \
                     "Thanks,\n" + \
                     "Core Services"

    # Create the email in a text format then send via smtp, finally save the email as a StringIO file and return
    #
    def cm_emailer(self):
        try:
            # Text and HTML Email
            self.msg = MIMEMultipart()
            self.msg['Subject'] = self.subj
            self.msg['From'] = self.from_address
            self.msg['To'] = self.to_address
            self.msg['Cc'] = self.cc

            # Message Text
            if self.data_source == '1':
                part1 = MIMEText(self.text_excel1, 'plain')
                part2 = MIMEText(self.html, 'html')
                part3 = MIMEText(self.text2, 'plain')

                self.msg.attach(part1)
                self.msg.attach(part2)
                self.msg.attach(part3)
            else:
                part1 = MIMEText(self.text_mysql1, 'plain')
                part3 = MIMEText(self.text2, 'plain')

                self.msg.attach(part1)
                self.msg.attach(part3)

            # Send Email
            with SMTP('mailhost.valkyrie.net') as smtp:
                smtp.send_message(self.msg)

        except Exception as e:
            self.logger.error = ("Email failed for ticket {} => {}".format(self.ticket.key, e))

        else:
            self.logger.warning("An alert email for ticket {} has been sent.".format(self.ticket.key))

    # Create the email in a text format then send via smtp, finally save the email as a StringIO file and return
    #
    def cm_emailer2(self):
        try:
            # Simple Text Email
            self.msg = MIMEMultipart()
            self.msg['Subject'] = self.subj
            self.msg['From'] = self.from_address
            self.msg['To'] = self.to_address
            self.msg['Cc'] = self.cc

            part1 = MIMEText(self.text_progress_failure, 'plain')
            part3 = MIMEText(self.text2, 'plain')

            self.msg.attach(part1)
            self.msg.attach(part3)

            # Send Email
            with SMTP('mailhost.valkyrie.net') as smtp:
                smtp.send_message(self.msg)

        except Exception as e:
            self.logger.error = ("Email failed for ticket {} => {}".format(self.ticket.key, e))

        else:
            self.logger.warning("An alert email for ticket {} has been sent.".format(self.ticket.key))
