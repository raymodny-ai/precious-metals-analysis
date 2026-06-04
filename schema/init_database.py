import mysql.connector
from mysql.connector import errorcode

DB_CONFIG = {
    'user': 'root',
    'password': 'your_password',
    'host': '127.0.0.1',
    'raise_on_warnings': True
}

DB_NAME = 'precious_insight'

TABLES = {}
TABLES['metal_prices'] = (
    "CREATE TABLE `metal_prices` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `metal_type` enum('gold','silver','platinum','palladium') NOT NULL,"
    "  `price_usd` decimal(10,2) NOT NULL,"
    "  `timestamp` datetime NOT NULL,"
    "  `source` varchar(100) DEFAULT NULL,"
    "  PRIMARY KEY (`id`),"
    "  KEY `idx_metal_time` (`metal_type`,`timestamp`)"
    ") ENGINE=InnoDB")

TABLES['news'] = (
    "CREATE TABLE `news` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `title` varchar(500) NOT NULL,"
    "  `content` text,"
    "  `source` varchar(100) DEFAULT NULL,"
    "  `url` varchar(500) DEFAULT NULL,"
    "  `publish_time` datetime DEFAULT NULL,"
    "  `sentiment_score` float DEFAULT NULL,"
    "  `metal_related` json DEFAULT NULL,"
    "  PRIMARY KEY (`id`),"
    "  KEY `idx_time` (`publish_time`),"
    "  KEY `idx_sentiment` (`sentiment_score`)"
    ") ENGINE=InnoDB")

TABLES['social_media'] = (
    "CREATE TABLE `social_media` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `platform` varchar(50) NOT NULL,"
    "  `content` text,"
    "  `author` varchar(100) DEFAULT NULL,"
    "  `post_time` datetime DEFAULT NULL,"
    "  `engagement_count` int(11) DEFAULT NULL,"
    "  `sentiment_score` float DEFAULT NULL,"
    "  `metal_mentioned` json DEFAULT NULL,"
    "  PRIMARY KEY (`id`),"
    "  KEY `idx_platform_time` (`platform`,`post_time`)"
    ") ENGINE=InnoDB")

TABLES['topics'] = (
    "CREATE TABLE `topics` ("
    "  `id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `topic_name` varchar(200) NOT NULL,"
    "  `category` varchar(100) DEFAULT NULL,"
    "  `first_seen` datetime DEFAULT NULL,"
    "  `last_seen` datetime DEFAULT NULL,"
    "  `total_mentions` int(11) DEFAULT NULL,"
    "  `avg_sentiment` float DEFAULT NULL,"
    "  PRIMARY KEY (`id`)"
    ") ENGINE=InnoDB")

def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8mb4'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

def main():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
            exit(1)
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            # Database does not exist, but we can't connect to it to create it if we don't connect to server first
            # Usually we connect without DB to create DB
            pass
        else:
            print(err)
            exit(1)
    
    # Connect without DB to create DB
    try:
        cnx = mysql.connector.connect(user=DB_CONFIG['user'], password=DB_CONFIG['password'], host=DB_CONFIG['host'])
        cursor = cnx.cursor()
        try:
            cursor.execute("USE {}".format(DB_NAME))
        except mysql.connector.Error as err:
            print("Database {} does not exist.".format(DB_NAME))
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                create_database(cursor)
                print("Database {} created successfully.".format(DB_NAME))
                cnx.database = DB_NAME
            else:
                print(err)
                exit(1)
    except Exception as e:
        print(f"Error connecting: {e}")
        return

    for table_name in TABLES:
        table_description = TABLES[table_name]
        try:
            print("Creating table {}: ".format(table_name), end='')
            cursor.execute(table_description)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")

    cursor.close()
    cnx.close()

if __name__ == "__main__":
    main()
