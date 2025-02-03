import mysql.connector
from mysql.connector import errorcode
import logging
import sys


class MySQLManager(object):
    def __init__(self, config, db_name):
        self.cnx = None
        self.cursor = None
        self.account_data = dict()
        self.config = config
        self.DB_NAME = db_name
        self.logger = logging.getLogger(__name__)

    # Creates a new connection with MySQL server
    #
    def establish_connection(self):
        # verify connection credentials
        try:
            self.cnx = mysql.connector.connect(**self.config, auth_plugin='mysql_native_password')
        except mysql.connector.Error as e:
            if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                self.logger.error("Something is wrong with your user name or password")
            elif e.errno == errorcode.ER_BAD_DB_ERROR:
                self.logger.error("Database does not exist")
            else:
                self.logger.error(e)
            sys.exit(1)
        else:
            self.cursor = self.cnx.cursor(buffered=True)
            # attempts to connect to named database, if not exit, else confirm connection
            try:
                self.cnx.database = self.DB_NAME
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_BAD_DB_ERROR:
                    self.logger.error("Database '{}' does not exist, exiting now.\n".format(self.DB_NAME))
                    sys.exit(1)
            else:
                self.logger.info("The data base '{}' exists, you are now connected.\n".format(self.DB_NAME))

    # Get values from database, assemble into dictionary and return
    #
    def get_data(self, table_name, media_partner, advertiser):
        # utilize a mysql cursor-dictionary class to return each db row as a dictionary, with column headings as keys
        self.cursor = self.cnx.cursor(dictionary=True)
        self.logger.info("Now using table {}".format(table_name))
        # 2 different sql queries one for no brand -> 'IS NULL' and one for a brand value -> '= brand'
        if media_partner is None:
            query = "SELECT * FROM {} as t WHERE t.media_partner IS NULL AND t.account = '{}'".format(table_name,
                                                                                                         advertiser)
        else:
            query = "SELECT * FROM {} as t WHERE t.media_partner = '{}' AND t.account = '{}'".format(table_name,
                                                                                                        media_partner,
                                                                                                        advertiser)
        self.cursor.execute(query)
        # this will return the only matched row in a dict structure
        for row in self.cursor:
            return row

    # Normalize data before database insertion, attend to and/or escape apostrophes and capture 'None's
    #
    @staticmethod
    def sql_esc(s):
        if s is None:
            return None
        elif isinstance(s, str):
            return '{}'.format(s.replace("'", "\\'"))
        else:
            return s

    # Closes cursor and connection
    #
    def close_connection(self):
        self.cursor.close()
        self.cnx.close()
        self.logger.info("Now closing mysql connection.")
