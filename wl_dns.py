# !/usr/bin/env python3
"""
DNS management script. It takes predefined json as input to generate zone files
and apply changes to the Bind9 server
"""

import json
import shutil
import subprocess
import shlex
import re
import logging
import logging.handlers


LOGGER_FILE = '/opt/log/ssh_api.log'
LOGGER_LEVEL = logging.WARNING
# Nuber of rotated log files
LOGGER_COUNT = 12
# Create logger and set it's name
logger = logging.getLogger(name='dns_wl_log')
logger_format = logging.Formatter(fmt='%(asctime)s - \
    %(name)s.%(funcName)s - %(levelname)s - %(message)s')
logger_handler = logging.handlers.TimedRotatingFileHandler(
    filename=LOGGER_FILE,
    when='midnight',
    backupCount=LOGGER_COUNT)
logger_handler.setFormatter(logger_format)
logger.addHandler(logger_handler)
logger.setLevel(LOGGER_LEVEL)
logger.debug('Logger configuration finished.')


ZONES_DIR: str = '/var/lib/bind/zones/master'
WL_ZONE_FILE: str = "aa-wl.rpz.ituss.cz.zone"

class Bind9Manager:
    """ Wrapper class for handling DNS settings
    """

    def __init__(self, jsn: json) -> None:
        super().__init__() # useless here?
        try:
            self.jsn = jsn
            self.action = self.jsn["action"]
            self.data = self.jsn["data"]
            self.wl_domain: list = self.data["wl_domain"]
        except KeyError as e:
            logger.exception(f"Init of Bind9Manager failed due to key error: {e}")
            raise ValueError(f"14001;Can't read json data for key {e} or data are missing") from e

    def parse_wl_zone(self) -> None:
        wl_zone_file_bak = WL_ZONE_FILE + ".bak"
        try:
            shutil.copy2(ZONES_DIR + "/" + WL_ZONE_FILE, ZONES_DIR + "/" + wl_zone_file_bak, )
        except shutil.Error as e:
            raise shutil.Error(f"17103;Cannot backup whitelist zone: {e}") from e

        try:
            with open(ZONES_DIR + "/" + WL_ZONE_FILE, 'r+') as zone:
                lines = zone.readlines()
                try:
                    with open(ZONES_DIR + "/" + WL_ZONE_FILE, 'w+') as new_zone:
                        serial_is_set: bool = False
                        serial_pattern = 'Serial'
                        for record in lines:
                            # find serial number
                            if not serial_is_set:
                                if re.search(serial_pattern, record):
                                    splitted = record.split(';')
                                    if splitted[1].strip() == "Serial":
                                        serial_number = int(splitted[0].strip()) + 1
                                        record = f"\t\t\t{serial_number:010d}\t;Serial\n"
                                        serial_is_set = True
                            if re.search("\t",record):
                                delete = False
                                domain = record.split("\t")
                                if domain[0] != '':
                                    for wl_record in self.wl_domain:
                                        if wl_record == domain[0]:
                                            delete = True
                                if delete:
                                    if self.action == "dns_wl_del":
                                        continue
                                    # check if added domain allready exists and remove it from list
                                    elif self.action == "dns_wl_set":
                                        self.wl_domain.remove(domain[0])
                            new_zone.write(record)
                        # write new domains
                        if self.action == "dns_wl_set":
                            if len(self.wl_domain) != 0:
                                for domain in self.wl_domain:
                                    new_zone.write(f"{domain}\t\tCNAME\trpz-passthru.\n")
                except FileNotFoundError as e:
                    raise FileNotFoundError(f"17103;Cannot write to zone file: {e}") from e
        except FileNotFoundError as e:
            raise FileNotFoundError(f"17103;Cannot open zone file: {e}") from e

    def _reload(self) -> None:
        """ """

        # restart bind
        args = shlex.split(f'/usr/bin/sudo /usr/bin/systemctl reload named.service')
        retc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if retc.returncode != 0:
            logger.error(f"Restarting bind service failed. {retc}")
            raise RuntimeError(f"14002;Restarting bind service failed. {retc}")


def run(json):
    dns_mgmt = Bind9Manager(json)
    dns_mgmt.parse_wl_zone()
    dns_mgmt._reload()
    return "200"


if __name__ == '__main__':
    print('Module is intended to be loaded by manage_api.py.')

    # for testing
    # jsn = open('test/wl_dns_set.json')
    # jason = json.load(jsn)
    # run(jason)
